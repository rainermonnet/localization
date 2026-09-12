"""
bestand-und-bilder-pruefen.py — Bestandsaufnahme für Zwergenladen
==================================================================

Findet zwei Dinge im Shopify-Katalog:

  1. Aktive Produkte OHNE Bild
  2. HENRYS-Produkte mit Bestand 0

Nur Lesezugriff — das Skript ändert nichts.

AUSFÜHREN
---------
Muss im App-Ordner liegen, damit es shopify_http importieren kann:

    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 bestand-und-bilder-pruefen.py

Ergebnis: zwei CSV-Dateien im selben Ordner
    ohne-bild.csv
    henrys-bestand-null.csv

Der Zugang kommt aus shopify_http — Client-ID und Secret sind dort
bereits hinterlegt, es ist nichts einzutragen.
"""

import csv
import os
import sys
import time

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden.\n"
             "Das Skript muss im App-Ordner liegen:\n"
             '  cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"')

# ──────────────────────────────────────────
# Konfiguration
# ──────────────────────────────────────────
PRODUKTE_PRO_SEITE = 25          # GraphQL-Kosten niedrig halten
VARIANTEN_PRO_PRODUKT = 50
PAUSE = 0.4                      # Sekunden zwischen den Seiten
HENRYS_MUSTER = ("henry", "henrys")   # Treffer im Hersteller- oder Titelfeld

QUERY = """
query($cursor: String, $n: Int!, $v: Int!) {
  products(first: $n, after: $cursor, query: "status:active", sortKey: CREATED_AT, reverse: true) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        title
        vendor
        status
        createdAt
        handle
        featuredImage { url }
        variants(first: $v) {
          edges {
            node {
              id
              title
              sku
              barcode
              inventoryQuantity
              inventoryItem { tracked }
            }
          }
        }
      }
    }
  }
}
"""


def kurz_id(gid: str) -> str:
    """gid://shopify/Product/12345 -> 12345"""
    return gid.rsplit("/", 1)[-1] if gid else ""


def seite_holen(cursor):
    """Eine Seite Produkte holen, mit Wiederholung bei Drosselung."""
    for versuch in range(5):
        antwort = shopify_http.execute(QUERY, {
            "cursor": cursor,
            "n": PRODUKTE_PRO_SEITE,
            "v": VARIANTEN_PRO_PRODUKT,
        })
        fehler = antwort.get("_error", "")
        if not fehler:
            return antwort, ""
        if "THROTTLED" in fehler.upper() and versuch < 4:
            warte = 2 ** versuch
            print(f"    gedrosselt, warte {warte}s …")
            time.sleep(warte)
            continue
        return {}, fehler
    return {}, "dauerhaft gedrosselt"


def ist_henrys(produkt) -> bool:
    text = f"{produkt.get('vendor','')} {produkt.get('title','')}".lower()
    return any(m in text for m in HENRYS_MUSTER)


def main():
    print("Lese aktive Produkte aus Shopify …\n")

    ohne_bild = []
    henrys_null = []
    gesamt = 0
    henrys_gesamt = 0
    cursor = None
    seite = 0

    while True:
        seite += 1
        antwort, fehler = seite_holen(cursor)
        if fehler:
            print(f"\nAbbruch auf Seite {seite}:\n{fehler}")
            if not gesamt:
                return
            print("Bisherige Treffer werden trotzdem gespeichert.\n")
            break

        block = antwort.get("products", {})
        kanten = block.get("edges", [])
        if not kanten:
            break

        for kante in kanten:
            p = kante["node"]
            gesamt += 1

            varianten = [v["node"] for v in p.get("variants", {}).get("edges", [])]
            bestand = sum((v.get("inventoryQuantity") or 0) for v in varianten)
            # Nur Varianten zählen, deren Bestand überhaupt geführt wird
            gefuehrt = [v for v in varianten
                        if (v.get("inventoryItem") or {}).get("tracked")]

            # 1) Bild fehlt
            if not p.get("featuredImage"):
                ohne_bild.append({
                    "Produkt-ID": kurz_id(p["id"]),
                    "Titel": p.get("title", ""),
                    "Hersteller": p.get("vendor", ""),
                    "Angelegt": (p.get("createdAt") or "")[:10],
                    "Handle": p.get("handle", ""),
                    "Varianten": len(varianten),
                    "Bestand": bestand,
                    "Admin-Link": f"https://admin.shopify.com/store/zwergenladen-fr"
                                  f"/products/{kurz_id(p['id'])}",
                })

            # 2) HENRYS mit Bestand 0
            if ist_henrys(p):
                henrys_gesamt += 1
                if gefuehrt and bestand <= 0:
                    for v in gefuehrt:
                        if (v.get("inventoryQuantity") or 0) > 0:
                            continue
                        henrys_null.append({
                            "Produkt-ID": kurz_id(p["id"]),
                            "Varianten-ID": kurz_id(v["id"]),
                            "Titel": p.get("title", ""),
                            "Variante": v.get("title", ""),
                            "SKU": v.get("sku") or "",
                            "Barcode": v.get("barcode") or "",
                            "Bestand": v.get("inventoryQuantity") or 0,
                            "Neuer Bestand": "",
                            "Admin-Link": f"https://admin.shopify.com/store/"
                                          f"zwergenladen-fr/products/{kurz_id(p['id'])}",
                        })

        print(f"  Seite {seite}: {gesamt} Produkte gelesen, "
              f"{len(ohne_bild)} ohne Bild, {len(henrys_null)} HENRYS-Varianten leer")

        info = block.get("pageInfo", {})
        if not info.get("hasNextPage"):
            break
        cursor = info.get("endCursor")
        time.sleep(PAUSE)

    # ── Ausgabe ───────────────────────────
    def schreiben(name, zeilen):
        if not zeilen:
            return
        with open(name, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(zeilen[0].keys()), delimiter=";")
            w.writeheader()
            w.writerows(zeilen)

    schreiben("ohne-bild.csv", ohne_bild)
    schreiben("henrys-bestand-null.csv", henrys_null)

    print("\n" + "=" * 66)
    print(f"{gesamt} aktive Produkte geprüft, davon {henrys_gesamt} von HENRYS")
    print("=" * 66)

    print(f"\nOHNE BILD: {len(ohne_bild)}")
    for z in ohne_bild[:25]:
        print(f"  {z['Angelegt']}  {z['Hersteller'][:14]:<14} {z['Titel'][:44]}")
    if len(ohne_bild) > 25:
        print(f"  … und {len(ohne_bild)-25} weitere")

    print(f"\nHENRYS MIT BESTAND 0: {len(henrys_null)}")
    for z in henrys_null[:25]:
        var = f" / {z['Variante']}" if z['Variante'] not in ("", "Default Title") else ""
        print(f"  {z['SKU'][:12]:<12} {z['Titel'][:40]}{var}")
    if len(henrys_null) > 25:
        print(f"  … und {len(henrys_null)-25} weitere")

    print("\nGeschrieben:")
    for n in ("ohne-bild.csv", "henrys-bestand-null.csv"):
        if os.path.exists(n):
            print(f"  {n}")
    print("\nBeide Dateien im Chat hochladen — dann arbeite ich sie auf.")
    print("In henrys-bestand-null.csv ist die Spalte „Neuer Bestand“ leer;")
    print("dort die Stückzahlen aus dem HENRYS-Lieferschein eintragen.")


if __name__ == "__main__":
    main()

"""
aus-google-nehmen.py — Marken aus dem Google-Kanal entfernen
=============================================================

Nimmt alle Produkte bestimmter Marken aus dem Google-&-YouTube-Kanal.
Die Produkte bleiben im Katalog und im Laden verfügbar — sie werden nur
nicht mehr an Google übermittelt.

WARUM DIESE MARKEN
------------------
  Aurich         Lieferant insolvent, keine Nachbestellung möglich
  Urachhaus      Buchverlag, Sortiment wird nur stationär verkauft
  Geistesleben   Buchverlag, ebenso

Buchtitel im Google-Kanal ohne Verkauf im Onlineshop erzeugen nur
Ablehnungen. Ware eines insolventen Lieferanten kann nicht nachkommen.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 aus-google-nehmen.py          # Probelauf, ändert nichts
    python3 aus-google-nehmen.py --live   # entfernt aus dem Kanal

Umkehrbar: In Shopify lässt sich ein Produkt jederzeit wieder im
Google-Kanal veröffentlichen.
"""

import csv
import sys
import time
from collections import Counter

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

# Marken, die nicht mehr an Google gehen (kleingeschrieben vergleichen)
MARKEN_RAUS = {
    "aurich",
    "urachhaus",
    "geistesleben",
}

PRO_SEITE = 50
PAUSE = 0.3

KANAELE = "{ publications(first: 25) { edges { node { id name } } } }"

ABFRAGE = """
query($cursor: String, $n: Int!) {
  products(first: $n, after: $cursor, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        title
        vendor
        totalInventory
        resourcePublicationsV2(first: 10) {
          edges { node { isPublished publication { name } } }
        }
      }
    }
  }
}
"""

ZURUECKZIEHEN = """
mutation($id: ID!, $input: [PublicationInput!]!) {
  publishableUnpublish(id: $id, input: $input) {
    userErrors { field message }
  }
}
"""


def kurz_id(gid):
    return gid.rsplit("/", 1)[-1] if gid else ""


def google_kanal_id():
    antwort = shopify_http.execute(KANAELE)
    if antwort.get("_error"):
        sys.exit(f"Kanäle nicht lesbar: {antwort['_error']}")
    for kante in antwort.get("publications", {}).get("edges", []):
        n = kante["node"]
        if "google" in (n.get("name") or "").lower():
            return n["id"], n["name"]
    sys.exit("Google-Kanal nicht gefunden.")


def seite(cursor):
    for v in range(5):
        a = shopify_http.execute(ABFRAGE, {"cursor": cursor, "n": PRO_SEITE})
        f = a.get("_error", "")
        if not f:
            return a, ""
        if "THROTTLED" in f.upper() and v < 4:
            time.sleep(2 ** v)
            continue
        return {}, f
    return {}, "dauerhaft gedrosselt"


def main():
    live = "--live" in sys.argv
    if not live:
        print("PROBELAUF — es wird nichts geändert.")
        print("Zum Entfernen:  python3 aus-google-nehmen.py --live\n")

    kanal_id, kanal_name = google_kanal_id()
    print(f"Kanal: {kanal_name}")
    print(f"Marken: {', '.join(sorted(MARKEN_RAUS))}\n")

    betroffen = []
    gesamt = 0
    cursor = None

    print("Lese Katalog …")
    while True:
        antwort, fehler = seite(cursor)
        if fehler:
            print(f"Abbruch: {fehler}")
            if not gesamt:
                return
            break

        block = antwort.get("products", {})
        for kante in block.get("edges", []):
            p = kante["node"]
            gesamt += 1
            if (p.get("vendor") or "").strip().lower() not in MARKEN_RAUS:
                continue
            kanaele = [(k["node"]["publication"] or {}).get("name", "")
                       for k in p.get("resourcePublicationsV2", {}).get("edges", [])
                       if k["node"].get("isPublished")]
            if not any("google" in k.lower() for k in kanaele):
                continue          # steht dort ohnehin nicht
            betroffen.append({
                "Produkt-ID": kurz_id(p["id"]),
                "Marke": p.get("vendor", ""),
                "Titel": p.get("title", ""),
                "Bestand": p.get("totalInventory") or 0,
            })

        info = block.get("pageInfo", {})
        if not info.get("hasNextPage"):
            break
        cursor = info.get("endCursor")
        time.sleep(PAUSE)

    print(f"{gesamt} aktive Produkte geprüft\n")

    if not betroffen:
        print("Keine Produkte dieser Marken im Google-Kanal. Nichts zu tun.")
        return

    zaehler = Counter(z["Marke"] for z in betroffen)
    print(f"{len(betroffen)} Produkte werden aus dem Google-Kanal genommen:\n")
    for marke, n in zaehler.most_common():
        ohne_bestand = sum(1 for z in betroffen
                           if z["Marke"] == marke and (z["Bestand"] or 0) <= 0)
        print(f"  {n:>4}  {marke:<18} davon {ohne_bestand} ohne Bestand")

    print("\nBeispiele:")
    for z in betroffen[:10]:
        print(f"  {z['Marke'][:14]:<14} {z['Titel'][:50]}")
    if len(betroffen) > 10:
        print(f"  … und {len(betroffen)-10} weitere")

    with open("aus-google-genommen.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(betroffen[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(betroffen)
    print("\nListe geschrieben: aus-google-genommen.csv")

    if not live:
        print(f"\n{len(betroffen)} Änderungen bereit. Mit --live ausführen.")
        return

    antwort = input(f"\n{len(betroffen)} Produkte aus dem Google-Kanal nehmen? "
                    "(ja/NEIN): ").strip()
    if antwort.lower() != "ja":
        print("Abgebrochen.")
        return

    ok = fehler = 0
    for i, z in enumerate(betroffen, 1):
        e = shopify_http.execute(ZURUECKZIEHEN, {
            "id": f"gid://shopify/Product/{z['Produkt-ID']}",
            "input": [{"publicationId": kanal_id}]})
        meldungen = e.get("_error") or [
            u.get("message")
            for u in (e.get("publishableUnpublish", {}).get("userErrors") or [])]
        if meldungen:
            fehler += 1
            print(f"  ✗ {z['Titel'][:40]}: {meldungen}")
        else:
            ok += 1
        if i % 25 == 0:
            print(f"  … {i}/{len(betroffen)}")
        time.sleep(0.25)

    print(f"\nFertig: {ok} entfernt, {fehler} fehlgeschlagen")
    print("Die Produkte bleiben im Katalog und im Laden verfügbar.")
    print("Merchant Center übernimmt die Änderung innerhalb von 24 Stunden.")


if __name__ == "__main__":
    main()

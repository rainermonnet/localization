"""
kanal-uebersicht.py — Wie viel vom Katalog erreicht Shopping?
==============================================================

Beantwortet die Frage, warum eine Performance-Max-Kampagne ihr Budget
nicht ausgeben kann: Sie kann nur bewerben, was überhaupt im Google-Kanal
veröffentlicht und dort vollständig genug ist.

Zählt für alle aktiven Produkte:
  - in welchen Vertriebskanälen sie veröffentlicht sind
  - wie viele davon Bild, Barcode (GTIN) und Bestand haben
  - was im Google-Kanal steht, aber unvollständig ist

Nur Lesezugriff.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 kanal-uebersicht.py
"""

import csv
import sys
import time
from collections import Counter

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

PRO_SEITE = 25
PAUSE = 0.4

ABFRAGE = """
query($cursor: String, $n: Int!) {
  products(first: $n, after: $cursor, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        title
        vendor
        onlineStoreUrl
        totalInventory
        featuredImage { url }
        resourcePublicationsV2(first: 10) {
          edges { node { isPublished publication { name } } }
        }
        variants(first: 5) { edges { node { barcode } } }
      }
    }
  }
}
"""


def kurz_id(gid):
    return gid.rsplit("/", 1)[-1] if gid else ""


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
    kanal_zaehler = Counter()
    gesamt = 0
    im_google = 0
    google_ohne_bild = []
    google_ohne_gtin = []
    google_ohne_bestand = []
    google_ohne_shopseite = []
    google_vollstaendig = 0
    cursor = None

    print("Lese Katalog und Kanalzugehörigkeit …")
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

            kanaele = [(k["node"]["publication"] or {}).get("name", "")
                       for k in p.get("resourcePublicationsV2", {}).get("edges", [])
                       if k["node"].get("isPublished")]
            if not kanaele:
                kanal_zaehler["(kein Kanal)"] += 1
            for k in kanaele:
                kanal_zaehler[k] += 1

            if not any("google" in k.lower() for k in kanaele):
                continue

            im_google += 1
            titel = p.get("title", "")
            bild = bool(p.get("featuredImage"))
            gtin = any((v["node"].get("barcode") or "").strip()
                       for v in p.get("variants", {}).get("edges", []))
            bestand = (p.get("totalInventory") or 0) > 0
            im_shop = bool(p.get("onlineStoreUrl"))

            eintrag = {"Produkt-ID": kurz_id(p["id"]), "Titel": titel,
                       "Marke": p.get("vendor", ""),
                       "Bild": "ja" if bild else "NEIN",
                       "GTIN": "ja" if gtin else "NEIN",
                       "Bestand": p.get("totalInventory") or 0,
                       "Admin-Link": f"https://admin.shopify.com/store/"
                                     f"zwergenladen-fr/products/{kurz_id(p['id'])}"}
            if not bild:
                google_ohne_bild.append(eintrag)
            if not gtin:
                google_ohne_gtin.append(eintrag)
            if not bestand:
                google_ohne_bestand.append(eintrag)
            # Im Google-Kanal, aber ohne Seite im Onlineshop: Google hat keine
            # Zielseite und meldet "Seite nicht verfügbar".
            if not im_shop:
                google_ohne_shopseite.append(eintrag)
            if bild and gtin and bestand and im_shop:
                google_vollstaendig += 1

        if gesamt % 250 == 0:
            print(f"  {gesamt} gelesen …")

        info = block.get("pageInfo", {})
        if not info.get("hasNextPage"):
            break
        cursor = info.get("endCursor")
        time.sleep(PAUSE)

    print("\n" + "=" * 62)
    print(f"{gesamt} aktive Produkte")
    print("=" * 62)
    print("\nVERTEILUNG AUF DIE KANÄLE")
    for kanal, n in kanal_zaehler.most_common():
        anteil = 100 * n / gesamt if gesamt else 0
        print(f"  {n:>5}  ({anteil:>4.1f} %)  {kanal}")

    print(f"\nIM GOOGLE-KANAL: {im_google}")
    if im_google:
        print(f"  davon vollständig                          {google_vollstaendig:>5}")
        print(f"  ohne Bild                                  {len(google_ohne_bild):>5}")
        print(f"  ohne GTIN / Barcode                        {len(google_ohne_gtin):>5}")
        print(f"  ohne Bestand                               {len(google_ohne_bestand):>5}")
        print(f"  ohne Seite im Onlineshop                   {len(google_ohne_shopseite):>5}"
              "   ← 'Seite nicht verfügbar'")

    def schreiben(name, zeilen):
        if not zeilen:
            return
        with open(name, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(zeilen[0].keys()), delimiter=";")
            w.writeheader()
            w.writerows(zeilen)
        print(f"  {name}")

    print("\nGeschrieben:")
    schreiben("google-ohne-bild.csv", google_ohne_bild)
    schreiben("google-ohne-gtin.csv", google_ohne_gtin)
    schreiben("google-ohne-bestand.csv", google_ohne_bestand)
    schreiben("google-ohne-shopseite.csv", google_ohne_shopseite)

    if google_ohne_shopseite:
        print(f"\n{len(google_ohne_shopseite)} Produkte stehen im Google-Kanal, haben aber")
        print("keine Seite im Onlineshop. Google findet keine Zielseite und lehnt sie ab.")
        print("Zwei Wege: im Onlineshop veröffentlichen — oder aus dem Google-Kanal nehmen.")
        for z in google_ohne_shopseite[:15]:
            print(f"  {z['Marke'][:16]:<16} {z['Titel'][:48]}")
        if len(google_ohne_shopseite) > 15:
            print(f"  … und {len(google_ohne_shopseite)-15} weitere in der CSV")

    if im_google and gesamt:
        print(f"\nNur {100*im_google/gesamt:.0f} % deines Katalogs steht im Google-Kanal.")
        print("Was dort nicht steht, kann keine Anzeige auslösen — unabhängig vom Budget.")


if __name__ == "__main__":
    main()

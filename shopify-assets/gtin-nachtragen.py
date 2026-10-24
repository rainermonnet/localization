"""
gtin-nachtragen.py — Barcodes füllen, wo sie herleitbar sind
==============================================================

409 von 800 Varianten im Feed haben keine GTIN. Ein Teil davon lässt sich
ohne Recherche füllen, weil die Information bereits vorliegt.

DREI REGELN, NACH SICHERHEIT GEORDNET
--------------------------------------
1. Die SKU IST bereits eine gültige EAN-13. Kommt vor, wenn beim Anlegen
   der Barcode ins SKU-Feld geraten ist. Prüfziffer wird verifiziert,
   bevor etwas übernommen wird.

2. goki: EAN = 4013594 + Artikelnummer (5-stellig) + Prüfziffer.
   Diese Regel wurde gegen die Preisliste geprüft — 128 von 128 Artikeln
   exakt reproduziert.

3. HENRYS: Nachschlagen in henrys-ean.csv, der Stammdatei des Herstellers
   mit 1215 geprüften Artikelnummern.

Was keiner Regel folgt, bleibt unangetastet. Geraten wird nicht — eine
falsche GTIN ist deutlich schlimmer als keine, weil Google das Produkt
dann einem fremden Artikel zuordnet.

Vorhandene Barcodes werden nie überschrieben.

VORBEREITEN
-----------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    curl -fsSL -O "https://raw.githubusercontent.com/rainermonnet/localization/claude/shopify-opti-assets-miijc7/shopify-assets/henrys-ean.csv"

AUSFÜHREN
---------
    python3 gtin-nachtragen.py           # Probelauf
    python3 gtin-nachtragen.py --live    # schreibt
"""

import csv
import os
import re
import sys
import time
from collections import Counter, defaultdict

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

HENRYS_DATEI = "henrys-ean.csv"
GOKI_PRAEFIX = "4013594"
PRO_SEITE = 25
PAUSE = 0.3

PRODUKTE = """
query($cursor: String, $n: Int!) {
  products(first: $n, after: $cursor, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        title
        vendor
        variants(first: 50) {
          edges { node { id title sku barcode } }
        }
      }
    }
  }
}
"""

SCHREIBEN = """
mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants { id barcode }
    userErrors { field message }
  }
}
"""


def pruefziffer(body):
    summe = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(body))
    return (10 - (summe % 10)) % 10


def ean_gueltig(wert):
    w = (wert or "").strip()
    return bool(re.fullmatch(r"\d{13}", w)) and pruefziffer(w[:12]) == int(w[12])


def goki_ean(artikelnummer):
    nr = str(artikelnummer).strip()
    if not re.fullmatch(r"\d{1,5}", nr):
        return None
    body = GOKI_PRAEFIX + nr.zfill(5)
    return body + str(pruefziffer(body))


def henrys_laden():
    if not os.path.exists(HENRYS_DATEI):
        return {}
    tabelle = {}
    with open(HENRYS_DATEI, encoding="utf-8-sig") as f:
        for z in csv.DictReader(f, delimiter=";"):
            art = (z.get("Artikelnummer") or "").strip()
            ean = (z.get("EAN") or "").strip()
            if art and ean_gueltig(ean):
                tabelle[art.upper()] = ean
    return tabelle


def herleiten(sku, marke, henrys):
    """Gibt (ean, regel) zurück — oder (None, None), wenn nichts greift."""
    s = (sku or "").strip()
    m = (marke or "").strip().lower()
    if not s:
        return None, None

    # 1. Die SKU ist selbst schon eine EAN
    if ean_gueltig(s):
        return s, "SKU ist EAN"

    # 2. goki-Regel
    if "goki" in m:
        e = goki_ean(s)
        if e:
            return e, "goki berechnet"

    # 3. HENRYS-Stammdaten
    if "henry" in m and henrys:
        e = henrys.get(s.upper())
        if e:
            return e, "HENRYS nachgeschlagen"

    return None, None


def seite(cursor):
    for v in range(5):
        a = shopify_http.execute(PRODUKTE, {"cursor": cursor, "n": PRO_SEITE})
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
        print("Zum Schreiben:  python3 gtin-nachtragen.py --live\n")

    henrys = henrys_laden()
    if henrys:
        print(f"HENRYS-Stammdaten: {len(henrys)} Artikelnummern geladen")
    else:
        print(f"Hinweis: {HENRYS_DATEI} nicht gefunden — HENRYS-Regel inaktiv.")
    print()

    print("Lese Katalog …")
    aenderungen = defaultdict(list)   # Produkt-ID → [(Varianten-ID, EAN, Regel, Titel)]
    varianten_gesamt = ohne_barcode = 0
    cursor = None

    while True:
        antwort, fehler = seite(cursor)
        if fehler:
            print(f"Abbruch: {fehler}")
            if not varianten_gesamt:
                return
            break
        block = antwort.get("products", {})
        for kante in block.get("edges", []):
            p = kante["node"]
            marke = p.get("vendor", "")
            titel = p.get("title", "")
            for vk in p.get("variants", {}).get("edges", []):
                v = vk["node"]
                varianten_gesamt += 1
                if (v.get("barcode") or "").strip():
                    continue          # vorhandene nie überschreiben
                ohne_barcode += 1
                ean, regel = herleiten(v.get("sku"), marke, henrys)
                if ean:
                    aenderungen[p["id"]].append(
                        (v["id"], ean, regel, f"{titel} / {v.get('title','')}"))
        info = block.get("pageInfo", {})
        if not info.get("hasNextPage"):
            break
        cursor = info.get("endCursor")
        time.sleep(PAUSE)

    anzahl = sum(len(v) for v in aenderungen.values())
    print(f"\n{varianten_gesamt} Varianten · {ohne_barcode} ohne Barcode · "
          f"{anzahl} herleitbar\n")

    if not anzahl:
        print("Nichts herleitbar. Die übrigen brauchen Herstellerangaben.")
        return

    regeln = Counter(r for liste in aenderungen.values() for _, _, r, _ in liste)
    print("NACH REGEL")
    for regel, n in regeln.most_common():
        print(f"  {n:>4}  {regel}")

    print("\nBEISPIELE")
    gezeigt = 0
    for liste in aenderungen.values():
        for _, ean, regel, bez in liste:
            print(f"  {ean}  [{regel:<22}] {bez[:46]}")
            gezeigt += 1
            if gezeigt >= 12:
                break
        if gezeigt >= 12:
            break
    if anzahl > 12:
        print(f"  … und {anzahl-12} weitere")

    rest = ohne_barcode - anzahl
    print(f"\n{rest} Varianten bleiben ohne GTIN — dort fehlt die Grundlage.")
    print("Geraten wird nicht: Eine falsche GTIN ordnet dein Produkt bei")
    print("Google einem fremden Artikel zu. Das ist schlimmer als keine.")

    if not live:
        print(f"\n{anzahl} Barcodes bereit. Mit --live schreiben.")
        return

    antwort = input(f"\n{anzahl} Barcodes setzen? (ja/NEIN): ").strip()
    if antwort.lower() != "ja":
        print("Abgebrochen.")
        return

    ok = fehler = 0
    for i, (pid, liste) in enumerate(aenderungen.items(), 1):
        e = shopify_http.execute(SCHREIBEN, {
            "productId": pid,
            "variants": [{"id": vid, "barcode": ean} for vid, ean, _, _ in liste]})
        meldungen = e.get("_error") or [
            u.get("message")
            for u in (e.get("productVariantsBulkUpdate", {}).get("userErrors") or [])]
        if meldungen:
            fehler += len(liste)
            if fehler <= 20:
                print(f"  ✗ {liste[0][3][:40]}: {meldungen}")
        else:
            ok += len(liste)
        if i % 25 == 0:
            print(f"  … {i}/{len(aenderungen)} Produkte")
        time.sleep(0.25)

    print(f"\nFertig: {ok} Barcodes gesetzt, {fehler} fehlgeschlagen")


if __name__ == "__main__":
    main()

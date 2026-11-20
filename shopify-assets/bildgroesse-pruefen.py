"""
bildgroesse-pruefen.py — Produktbilder unter 500 x 500 Pixel finden
====================================================================

STAND 2026-11-08b (Antwortformat von execute() korrigiert)

Anlass: Google Merchant Center meldet "Bild zu klein für die bevorstehende
Maßnahme". Ab 31. Januar 2027 müssen Produktbilder mindestens 500 x 500
Pixel groß sein. Kleinere Bilder werden nicht mehr genehmigt und nicht mehr
auf Google gezeigt. Merchant Center bekommt die Bilder aus Shopify, also
muss in Shopify nachgebessert werden.

Das Skript prüft das Titelbild (das Bild, das Google als image_link nimmt)
aller aktiven, im Onlineshop veröffentlichten Produkte und schreibt eine
Liste der zu kleinen Bilder.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    curl -fsSL -o bildgroesse-pruefen.py "https://raw.githubusercontent.com/rainermonnet/localization/claude/shopify-opti-assets-miijc7/shopify-assets/bildgroesse-pruefen.py"
    python3 bildgroesse-pruefen.py

Optionen:
    --min 500        Mindestgröße in Pixel (Standard 500, beide Seiten)
    --alle-bilder    prüft auch die Zusatzbilder, nicht nur das Titelbild

Nur Lesezugriff — es wird nichts in Shopify geändert.
Ergebnis: bildgroesse-zu-klein.csv (öffnet in Excel/Numbers)
"""

import csv
import sys
import time
from collections import Counter

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden.\n"
             "Das Skript muss im App-Ordner liegen:\n"
             '  cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"')

ADMIN = "https://admin.shopify.com/store/zwergenladen-fr/products/"
SHOP = "https://zwergenladen.info/products/"
AUSGABE = "bildgroesse-zu-klein.csv"
SEITE = 25
PAUSE = 0.3

QUERY = """
query($cursor: String) {
  products(first: %d, after: $cursor,
           query: "status:active published_status:published", sortKey: ID) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      title
      handle
      vendor
      totalInventory
      featuredMedia { ... on MediaImage { image { width height } } }
      media(first: 10) { nodes { ... on MediaImage { image { width height } } } }
    }
  }
}
""" % SEITE


def lese_argumente(argv):
    optionen = {"--min": 500, "--alle-bilder": False}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--alle-bilder":
            optionen[a] = True
        elif a == "--min":
            try:
                optionen[a] = int(argv[i + 1])
            except (IndexError, ValueError):
                sys.exit("--min braucht eine Zahl, z. B. --min 500")
            i += 1
        else:
            sys.exit("Unbekannte Option: %s\nErlaubt: --min ZAHL, --alle-bilder" % a)
        i += 1
    return optionen


def groesse(bild):
    """(breite, hoehe) oder None."""
    if not bild or not bild.get("image"):
        return None
    b, h = bild["image"].get("width"), bild["image"].get("height")
    return (b, h) if b and h else None


def seite_holen(cursor):
    """Eine Seite lesen. execute() liefert direkt den data-Block oder
    {'_error': '...'}. Bei Drosselung wird mit Pause wiederholt."""
    for versuch in range(5):
        antwort = shopify_http.execute(QUERY, {"cursor": cursor})
        fehler = antwort.get("_error", "")
        if not fehler:
            return antwort["products"]
        if "THROTTLED" in fehler.upper() and versuch < 4:
            warte = 2 ** versuch
            print("\n    gedrosselt, warte %ds …" % warte)
            time.sleep(warte)
            continue
        sys.exit("\nShopify-Fehler:\n%s" % fehler)


def holen():
    cursor, alle = None, []
    while True:
        seite = seite_holen(cursor)
        alle.extend(seite["nodes"])
        print("  … %d Produkte gelesen" % len(alle), end="\r")
        if not seite["pageInfo"]["hasNextPage"]:
            break
        cursor = seite["pageInfo"]["endCursor"]
        time.sleep(PAUSE)
    print()
    return alle


def main():
    opt = lese_argumente(sys.argv)
    minimum = opt["--min"]
    print("Prüfe Produktbilder gegen %d x %d Pixel …" % (minimum, minimum))
    produkte = holen()

    zu_klein, ohne_bild = [], []
    for p in produkte:
        titelbild = groesse(p.get("featuredMedia"))
        if titelbild is None:
            ohne_bild.append(p)
            continue
        kleine_zusatz = 0
        if opt["--alle-bilder"]:
            for m in p["media"]["nodes"]:
                g = groesse(m)
                if g and min(g) < minimum:
                    kleine_zusatz += 1
        titel_klein = min(titelbild) < minimum
        if titel_klein or kleine_zusatz:
            zu_klein.append((p, titelbild, titel_klein, kleine_zusatz))

    def vorrat(p):
        return p.get("totalInventory") or 0

    # Zuerst, was auf Lager ist: Dort bringen bessere Bilder am meisten.
    zu_klein.sort(key=lambda t: (-(vorrat(t[0]) > 0), t[0]["vendor"] or "", t[0]["title"]))

    with open(AUSGABE, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Hersteller", "Produkt", "Titelbild Breite", "Titelbild Höhe",
                    "Titelbild zu klein", "Zusatzbilder zu klein", "Lagerbestand",
                    "Admin-Link", "Shop-Link"])
        for p, g, tk, zk in zu_klein:
            kurz = p["id"].rsplit("/", 1)[-1]
            w.writerow([p["vendor"], p["title"], g[0], g[1],
                        "ja" if tk else "nein", zk, vorrat(p),
                        ADMIN + kurz, SHOP + p["handle"]])

    n_titel = sum(1 for t in zu_klein if t[2])
    auf_lager = sum(1 for t in zu_klein if t[2] and vorrat(t[0]) > 0)
    print("\nGeprüft:                        %d Produkte" % len(produkte))
    print("Titelbild unter %d Pixel:      %d  (davon auf Lager: %d)" % (minimum, n_titel, auf_lager))
    if opt["--alle-bilder"]:
        print("Nur Zusatzbilder zu klein:      %d" % sum(1 for t in zu_klein if not t[2]))
    print("Ganz ohne Bild:                 %d  (eigene Liste: bildluecken-aufarbeiten.py)" % len(ohne_bild))
    print("\nNach Hersteller (Titelbild zu klein):")
    for v, n in Counter((t[0]["vendor"] or "—") for t in zu_klein if t[2]).most_common(15):
        print("  %-28s %d" % (v, n))
    print("\nListe gespeichert: %s" % AUSGABE)


if __name__ == "__main__":
    main()

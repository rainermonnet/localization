"""
barcode-umstellung-pruefen.py — Stand der Barcode-Umstellung
==============================================================

Sagt, wo der Shop und die Skripte gerade stehen:

  • welche API-Version `shopify_http.py` benutzt
  • ob diese Version das neue Feld `barcodes` kennt
  • ob die alte Schreibweise `barcode` beim Schreiben noch angenommen wird
  • welche Dateien im Ordner die alte Form verwenden

Ändert nichts. Reine Auskunft.

WORUM ES GEHT
-------------
Beim LESEN ist `barcode` veraltet — es funktioniert noch und warnt.
Beim SCHREIBEN ist es in neueren Versionen ersatzlos verschwunden:
`ProductVariantsBulkInput` kennt nur noch `barcodes`. Wer weiter
`barcode` sendet, bekommt einen Fehler, keine Warnung.

Das ist der Unterschied, der zählt: Ein Leseaufruf bleibt eine Weile
lesbar, ein Schreibaufruf bricht sofort.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 barcode-umstellung-pruefen.py
"""

import glob
import os
import re
import sys

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

try:
    import barcode_feld as bc
except ImportError:
    bc = None

LESEN_ALT = """
query { productVariants(first: 1) { nodes { id barcode } } }
"""
LESEN_NEU = """
query { productVariants(first: 1) { nodes { id barcodes(first: 1) { nodes { value type } } } } }
"""


def probe(name, abfrage):
    antwort = shopify_http.execute(abfrage)
    fehler = str(antwort.get("_error", ""))
    if not fehler:
        print(f"  ok     {name}")
        return True
    kurz = fehler.replace("\n", " ")[:150]
    print(f"  FEHLER {name}")
    print(f"         {kurz}")
    return False


def dateien_pruefen():
    """Sucht die alte Form in allen Python-Dateien daneben."""
    ordner = os.path.dirname(os.path.abspath(__file__))
    treffer = {}
    muster_lesen = re.compile(r"\bsku\s+barcode\b|\bnode\s*\{[^}]*\bbarcode\b")
    # Schreiben erkennt man nicht am Wort „barcode" allein — das steht auch
    # in Antworten und Testdaten. Es braucht beides: das Feld UND eine
    # Mutation, die Varianten schreibt.
    muster_schreiben = re.compile(r'"barcode"\s*:')
    muster_mutation = re.compile(r"productVariantsBulkUpdate|productVariantUpdate")
    for pfad in sorted(glob.glob(os.path.join(ordner, "*.py"))
                       + glob.glob(os.path.join(ordner, "pages", "*.py"))):
        name = os.path.relpath(pfad, ordner)
        # Die Transportschicht baut nie Produkteingaben — sie reicht nur durch.
        if name in ("barcode_feld.py", "shopify_http.py", "shopify_http_alt.py",
                    "shopify_api.py", os.path.basename(__file__)):
            continue
        try:
            text = open(pfad, encoding="utf-8").read()
        except OSError:
            continue
        if "barcode_feld" in text:
            treffer[name] = "umgestellt"
            continue
        liest = bool(muster_lesen.search(text))
        schreibt = bool(muster_schreiben.search(text)
                        and muster_mutation.search(text))
        if schreibt:
            treffer[name] = "SCHREIBT alte Form"
        elif liest:
            treffer[name] = "liest alte Form"
    return treffer


def main():
    print("BARCODE-UMSTELLUNG — STAND\n")
    print(f"API-Version laut shopify_http.py:  {shopify_http.API_VERSION}")
    print(f"Shop:                              {shopify_http.STORE}\n")

    print("Was der Shop auf dieser Version annimmt:")
    alt_geht = probe("Lesen mit  barcode   (alte Form)", LESEN_ALT)
    neu_geht = probe("Lesen mit  barcodes  (neue Form)", LESEN_NEU)

    print()
    if alt_geht and neu_geht:
        print("BEIDE FORMEN GEHEN — das ist das Zeitfenster für die Umstellung.")
        print("Jetzt umstellen kostet nichts und lässt sich jederzeit prüfen.")
    elif alt_geht and not neu_geht:
        print("Nur die alte Form. Diese API-Version kennt `barcodes` noch nicht.")
        print("Die Zwischenschicht erkennt das selbst — es ist nichts zu tun,")
        print("bis die Version angehoben wird.")
    elif neu_geht and not alt_geht:
        print("NUR DIE NEUE FORM. Alles, was noch `barcode` sendet, ist bereits")
        print("defekt — vor allem die schreibenden Skripte.")
    else:
        print("Keine der beiden Formen antwortet. Eher ein Zugriffsproblem")
        print("als eine Versionsfrage — pruefe_zugang() in shopify_http.py hilft.")

    if bc is not None:
        print(f"\nZwischenschicht erkennt: "
              f"{'neue' if bc.neue_api() else 'alte'} Form")
        print(f"  Lesefragment:  {bc.LESEN}")
        print(f"  Schreibform:   {bc.schreiben('4013594123458')}")
        print(f"  Buch (ISBN):   {bc.schreiben('9783522202503')}")
    else:
        print("\nbarcode_feld.py fehlt — ohne sie gibt es keine Umschaltung.")

    print("\nDATEIEN IM ORDNER")
    treffer = dateien_pruefen()
    if not treffer:
        print("  Keine Datei verwendet Barcodes.")
    else:
        for art in ("SCHREIBT alte Form", "liest alte Form", "umgestellt"):
            passend = [n for n, a in treffer.items() if a == art]
            if passend:
                print(f"\n  {art}  ({len(passend)})")
                for n in sorted(passend):
                    print(f"      {n}")
        if any(a == "SCHREIBT alte Form" for a in treffer.values()):
            print("\n  Die schreibenden zuerst umstellen — die brechen sofort,")
            print("  während die lesenden erst nur warnen.")


if __name__ == "__main__":
    main()

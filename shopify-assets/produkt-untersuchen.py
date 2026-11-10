"""
produkt-untersuchen.py — ein Produkt im Detail ansehen
=======================================================

Zeigt Optionen, Varianten, Metafelder und Kanalzugehörigkeit eines
Produkts. Gedacht, um vor einer Änderung zu verstehen, wie das Produkt
tatsächlich aufgebaut ist — statt zu raten, welches Feld Google liest.

Anlass: 22 Eurythmieschuhe-Varianten werden von Merchant Center mit
"Fehlende Größe" abgewiesen, obwohl die Größe im Variantentitel steht.
Google liest die Größe nicht aus dem Titel, sondern aus dem Attribut
`size` — das speist sich aus der Variantenoption, wenn sie passend
benannt ist, oder aus einem Metafeld.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 produkt-untersuchen.py 15405685506421

Nur Lesezugriff.
"""

import sys

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

ABFRAGE = """
query($id: ID!) {
  product(id: $id) {
    id
    title
    vendor
    productType
    status
    onlineStoreUrl
    category { id fullName }
    options { id name position optionValues { name } }
    resourcePublicationsV2(first: 10) {
      edges { node { isPublished publication { name } } }
    }
    metafields(first: 50) {
      edges { node { namespace key value type } }
    }
    variants(first: 30) {
      edges {
        node {
          id
          title
          sku
          barcode
          inventoryQuantity
          selectedOptions { name value }
          metafields(first: 20) {
            edges { node { namespace key value } }
          }
        }
      }
    }
  }
}
"""


def main():
    if len(sys.argv) < 2:
        sys.exit("Produkt-ID angeben:\n  python3 produkt-untersuchen.py 15405685506421")
    pid = sys.argv[1].strip()

    antwort = shopify_http.execute(ABFRAGE, {"id": f"gid://shopify/Product/{pid}"})
    if antwort.get("_error"):
        sys.exit(f"Fehler: {antwort['_error']}")
    p = antwort.get("product")
    if not p:
        sys.exit(f"Produkt {pid} nicht gefunden.")

    print(f"\n  {p.get('title','')}")
    print(f"  Hersteller   {p.get('vendor','')}")
    print(f"  Produktart   {p.get('productType') or '— leer —'}")
    print(f"  Status       {p.get('status','')}")
    print(f"  Im Shop      {'ja' if p.get('onlineStoreUrl') else 'nein'}")

    kat = p.get("category")
    print(f"  Kategorie    {kat.get('fullName') if kat else '— nicht gesetzt —'}")
    if not kat:
        print("               ↑ Ohne Kategorie kann Google Pflichtattribute")
        print("                 nicht zuordnen. Das ist oft die Wurzel.")

    kanaele = [(k["node"]["publication"] or {}).get("name", "")
               for k in p.get("resourcePublicationsV2", {}).get("edges", [])
               if k["node"].get("isPublished")]
    print(f"  Kanäle       {', '.join(kanaele) or 'keine'}")

    print("\n  OPTIONEN")
    for o in p.get("options", []):
        werte = [w["name"] for w in o.get("optionValues", [])]
        print(f"    {o['position']}. „{o['name']}“  "
              f"({len(werte)} Werte: {', '.join(werte[:6])}"
              f"{' …' if len(werte) > 6 else ''})")
        if o["name"].strip().lower() in ("title", "titel"):
            print("        ↑ Generischer Name. Google erkennt daraus weder")
            print("          Größe noch Farbe. Das ist der häufigste Grund")
            print("          für „Fehlende Größe“.")

    mf = [k["node"] for k in p.get("metafields", {}).get("edges", [])]
    print(f"\n  METAFELDER AM PRODUKT ({len(mf)})")
    if not mf:
        print("    — keine —")
    for m in mf:
        wert = (m.get("value") or "")[:40]
        print(f"    {m['namespace']}.{m['key']:<22} = {wert}")

    varianten = [v["node"] for v in p.get("variants", {}).get("edges", [])]
    print(f"\n  VARIANTEN ({len(varianten)}, erste 6)")
    for v in varianten[:6]:
        opts = ", ".join(f"{o['name']}={o['value']}"
                         for o in v.get("selectedOptions", []))
        print(f"    {v.get('title',''):<16} SKU {v.get('sku') or '—':<12} "
              f"Bestand {v.get('inventoryQuantity')}")
        print(f"      {opts}")
        vmf = [k["node"] for k in v.get("metafields", {}).get("edges", [])]
        for m in vmf:
            print(f"      Metafeld {m['namespace']}.{m['key']} = "
                  f"{(m.get('value') or '')[:30]}")

    # Einschätzung
    print("\n  " + "─" * 56)
    namen = [o["name"].strip().lower() for o in p.get("options", [])]
    groesse_ok = any(n in ("größe", "groesse", "size", "schuhgröße") for n in namen)
    farbe_ok = any(n in ("farbe", "color", "colour") for n in namen)
    google_mf = [m for m in mf if "google" in m["namespace"].lower()]

    print("  BEFUND")
    print(f"    Option für Größe erkennbar    {'ja' if groesse_ok else 'NEIN'}")
    print(f"    Option für Farbe erkennbar    {'ja' if farbe_ok else 'NEIN'}")
    print(f"    Kategorie gesetzt             {'ja' if kat else 'NEIN'}")
    print(f"    Google-Metafelder vorhanden   "
          f"{len(google_mf) if google_mf else 'NEIN'}")
    if google_mf:
        print(f"      Namensraum: {google_mf[0]['namespace']}")
        print("      ↑ Diesen Namensraum nutzt der Google-Kanal in deinem Shop.")


if __name__ == "__main__":
    main()

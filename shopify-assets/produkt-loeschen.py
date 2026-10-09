"""
produkt-loeschen.py — ein einzelnes Produkt endgültig entfernen
===============================================================

Zeigt das Produkt mit allen wesentlichen Angaben und löscht es nach
Bestätigung. Für Ware, die nicht mehr geführt wird — etwa von einem
insolventen Lieferanten.

LÖSCHEN IST ENDGÜLTIG. Shopify hat keinen Papierkorb für Produkte.
Wer ein Produkt nur vorübergehend aus dem Verkauf nehmen will, sollte es
stattdessen archivieren oder aus den Kanälen nehmen — das ist umkehrbar.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 produkt-loeschen.py 15259386872181
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
    status
    createdAt
    totalInventory
    onlineStoreUrl
    featuredImage { url }
    resourcePublicationsV2(first: 10) {
      edges { node { isPublished publication { name } } }
    }
    variants(first: 20) {
      edges { node { title sku barcode price inventoryQuantity } }
    }
  }
}
"""

LOESCHEN = """
mutation($input: ProductDeleteInput!) {
  productDelete(input: $input) {
    deletedProductId
    userErrors { field message }
  }
}
"""


def main():
    if len(sys.argv) < 2:
        sys.exit("Produkt-ID angeben:\n  python3 produkt-loeschen.py 15259386872181")
    pid = sys.argv[1].strip()

    antwort = shopify_http.execute(ABFRAGE, {"id": f"gid://shopify/Product/{pid}"})
    if antwort.get("_error"):
        sys.exit(f"Fehler: {antwort['_error']}")
    p = antwort.get("product")
    if not p:
        sys.exit(f"Produkt {pid} nicht gefunden — vielleicht schon gelöscht.")

    kanaele = [(k["node"]["publication"] or {}).get("name", "")
               for k in p.get("resourcePublicationsV2", {}).get("edges", [])
               if k["node"].get("isPublished")]
    varianten = [v["node"] for v in p.get("variants", {}).get("edges", [])]

    print()
    print(f"  Titel        {p.get('title','')}")
    print(f"  Hersteller   {p.get('vendor','')}")
    print(f"  Status       {p.get('status','')}")
    print(f"  Angelegt     {(p.get('createdAt') or '')[:10]}")
    print(f"  Bestand      {p.get('totalInventory')}")
    print(f"  Bild         {'ja' if p.get('featuredImage') else 'nein'}")
    print(f"  Im Shop      {'ja' if p.get('onlineStoreUrl') else 'nein'}")
    print(f"  Kanäle       {', '.join(kanaele) or 'keine'}")
    print(f"  Varianten    {len(varianten)}")
    for v in varianten[:5]:
        print(f"               {v.get('sku') or '—':<14} {v.get('barcode') or '—':<15} "
              f"{v.get('price') or '—':>8}  Bestand {v.get('inventoryQuantity')}")

    if (p.get("totalInventory") or 0) > 0:
        print(f"\n  ⚠ Das Produkt hat noch Bestand ({p.get('totalInventory')}).")
        print("    Nach dem Löschen ist er aus der Bestandsführung verschwunden.")

    print("\nLöschen ist endgültig — Shopify hat keinen Papierkorb.")
    print("Umkehrbare Alternative: archivieren oder aus den Kanälen nehmen.")
    if input(f"\nProdukt {pid} wirklich löschen? (ja/NEIN): ").strip().lower() != "ja":
        print("Abgebrochen, nichts geändert.")
        return

    e = shopify_http.execute(LOESCHEN, {"input": {"id": f"gid://shopify/Product/{pid}"}})
    if e.get("_error"):
        sys.exit(f"Fehler: {e['_error']}")
    block = e.get("productDelete", {})
    for f in block.get("userErrors") or []:
        print(f"Fehler: {f.get('message')}")
        return
    print(f"Gelöscht: {block.get('deletedProductId')}")


if __name__ == "__main__":
    main()

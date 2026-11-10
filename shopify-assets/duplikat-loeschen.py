"""
duplikat-loeschen.py — zwei Produkte vergleichen, eines löschen
================================================================

Für versehentlich doppelt angelegte Produkte. Zeigt beide nebeneinander,
empfiehlt eines zum Löschen und fragt vor dem Löschen nach.

Anlass: "Zwergenladen Mozart h Schlüsseletui" liegt zweimal im Katalog
(15985142530421 und 15985131159925, beide vom 14.09.2026).

LÖSCHEN IST ENDGÜLTIG. Shopify kennt keinen Papierkorb für Produkte.
Darum: erst vergleichen, dann entscheiden, dann bestätigen.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 duplikat-loeschen.py 15985142530421 15985131159925

Ohne Argumente werden die beiden Mozart-Etuis geprüft.
"""

import sys

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

VORGABE = ["15985142530421", "15985131159925"]

ABFRAGE = """
query($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    vendor
    status
    createdAt
    updatedAt
    onlineStoreUrl
    descriptionHtml
    totalInventory
    featuredImage { url }
    media(first: 1) { edges { node { id } } }
    resourcePublicationsV2(first: 10) {
      edges { node { isPublished publication { name } } }
    }
    variants(first: 50) {
      edges { node { id title sku barcode price inventoryQuantity } }
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


def laden(pid):
    antwort = shopify_http.execute(ABFRAGE, {"id": f"gid://shopify/Product/{pid}"})
    if antwort.get("_error"):
        return None, antwort["_error"]
    p = antwort.get("product")
    if not p:
        return None, f"Produkt {pid} nicht gefunden"
    return p, ""


def kanaele(p):
    return [(k["node"]["publication"] or {}).get("name", "")
            for k in p.get("resourcePublicationsV2", {}).get("edges", [])
            if k["node"].get("isPublished")]


def zusammenfassen(p):
    varianten = [v["node"] for v in p.get("variants", {}).get("edges", [])]
    return {
        "Titel": p.get("title", ""),
        "Handle": p.get("handle", ""),
        "Hersteller": p.get("vendor", ""),
        "Status": p.get("status", ""),
        "Angelegt": (p.get("createdAt") or "")[:16].replace("T", " "),
        "Geändert": (p.get("updatedAt") or "")[:16].replace("T", " "),
        "Im Onlineshop": "ja" if p.get("onlineStoreUrl") else "nein",
        "Kanäle": ", ".join(kanaele(p)) or "keine",
        "Bild": "ja" if p.get("featuredImage") else "nein",
        "Medien": len(p.get("media", {}).get("edges", [])),
        "Beschreibung": f"{len(p.get('descriptionHtml') or '')} Zeichen",
        "Varianten": len(varianten),
        "Bestand": p.get("totalInventory"),
        "SKU": ", ".join(v.get("sku") or "—" for v in varianten[:3]),
        "Barcode": ", ".join(v.get("barcode") or "—" for v in varianten[:3]),
        "Preis": ", ".join(str(v.get("price") or "—") for v in varianten[:3]),
    }


def punkte(z):
    """Je höher, desto erhaltenswerter."""
    p = 0
    p += 40 if z["Bild"] == "ja" else 0
    p += 30 if (z["Bestand"] or 0) > 0 else 0
    p += 20 if z["Im Onlineshop"] == "ja" else 0
    p += 10 if z["Kanäle"] != "keine" else 0
    p += min(int(z["Beschreibung"].split()[0]) // 100, 10)
    p += 5 if z["Barcode"] != "—" else 0
    return p


def main():
    ids = sys.argv[1:3] if len(sys.argv) >= 3 else VORGABE
    if len(ids) != 2:
        sys.exit("Zwei Produkt-IDs angeben.")

    daten = []
    for pid in ids:
        p, fehler = laden(pid)
        if fehler:
            sys.exit(f"Fehler bei {pid}: {fehler}")
        daten.append((pid, zusammenfassen(p)))

    felder = list(daten[0][1].keys())
    breite = max(len(f) for f in felder) + 2

    print()
    print(f"{'':<{breite}}{daten[0][0]:<26}{daten[1][0]}")
    print("─" * (breite + 52))
    for f in felder:
        a, b = str(daten[0][1][f]), str(daten[1][1][f])
        mark = "  " if a == b else "≠ "
        print(f"{mark}{f:<{breite-2}}{a[:24]:<26}{b[:24]}")

    pa, pb = punkte(daten[0][1]), punkte(daten[1][1])
    print("─" * (breite + 52))
    print(f"{'  Bewertung':<{breite}}{pa:<26}{pb}")

    if pa == pb:
        print("\nBeide gleichwertig. Vorschlag: das später angelegte löschen.")
        weg = 0 if daten[0][1]["Angelegt"] > daten[1][1]["Angelegt"] else 1
    else:
        weg = 0 if pa < pb else 1

    behalten = 1 - weg
    print(f"\n  BEHALTEN:  {daten[behalten][0]}  ({daten[behalten][1]['Titel']})")
    print(f"  LÖSCHEN:   {daten[weg][0]}")

    if (daten[weg][1]["Bestand"] or 0) > 0:
        print("\n  ⚠ Das zu löschende Produkt hat Bestand. Vorher umbuchen!")

    print("\nLöschen ist endgültig — Shopify hat keinen Papierkorb.")
    antwort = input(f"Produkt {daten[weg][0]} wirklich löschen? (ja/NEIN): ").strip()
    if antwort.lower() != "ja":
        print("Abgebrochen, nichts geändert.")
        return

    ergebnis = shopify_http.execute(LOESCHEN, {
        "input": {"id": f"gid://shopify/Product/{daten[weg][0]}"}})
    if ergebnis.get("_error"):
        print(f"Fehler: {ergebnis['_error']}")
        return
    block = ergebnis.get("productDelete", {})
    fehler = block.get("userErrors") or []
    if fehler:
        for f in fehler:
            print(f"Fehler: {f.get('message')}")
        return
    print(f"Gelöscht: {block.get('deletedProductId')}")


if __name__ == "__main__":
    main()

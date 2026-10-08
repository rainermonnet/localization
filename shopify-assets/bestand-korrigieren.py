"""
bestand-korrigieren.py — gezählte Bestände nach Shopify zurückschreiben
========================================================================

Liest die zurückgegebene Zählliste und setzt die Bestände in Shopify auf
die gezählten Werte.

WELCHE ZAHL GILT
----------------
Vorrang hat die Spalte „Ist-Bestand gezählt". Ist sie leer, zählt der
Wert in „Bestand lt. Shopify" — denn der wurde beim Zählen überschrieben.

Verglichen wird NICHT gegen die Ursprungsdatei, sondern gegen den
Bestand, den Shopify im Moment des Laufs meldet. Zwischen Zählen und
Korrigieren können Verkäufe liegen; die Datei weiß davon nichts. Nur wo
Blatt und Shopify auseinanderliegen, wird etwas geändert.

WAS ÜBERSPRUNGEN WIRD
---------------------
• Produkte mit mehreren Varianten. Das Blatt führt eine Zahl je Produkt,
  Shopify je Variante — eine Gesamtzahl lässt sich nicht aufteilen, ohne
  zu raten. Diese Zeilen werden genannt, nicht verteilt.
• Produkte mit Bestand an mehreren Lagerorten, solange nicht mit
  --lager ein Ort genannt ist.
• Zeilen ohne Handle oder ohne Zahl.

BRAUCHT
-------
Zugriffsbereich write_inventory. Fehlt der, bricht das Skript mit
klarer Meldung ab, ohne etwas zu ändern.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 bestand-korrigieren.py Ladenhueter_ab_50_Euro_oder_3_Stueck.xlsx
    python3 bestand-korrigieren.py <datei.xlsx> --live

Der Probelauf zeigt jede Änderung einzeln mit Vorher und Nachher.
Geschrieben wird erst mit --live und nach ausdrücklicher Bestätigung.

Jede Korrektur wird in Shopify als Bestandskorrektur mit Grund
protokolliert und ist im Bestandsverlauf nachvollziehbar.
"""

import os
import sys
import time

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl fehlt.  Abhilfe:  pip3 install openpyxl")

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

BLATT = "Zählliste"
GRUND = "correction"

LAGER = """
query { locations(first: 20) { edges { node { id name isActive } } } }
"""

PRODUKT = """
query($handle: String!) {
  productByHandle(handle: $handle) {
    id
    title
    totalInventory
    variants(first: 20) {
      edges {
        node {
          id
          title
          sku
          inventoryItem {
            id
            tracked
            inventoryLevels(first: 10) {
              edges {
                node {
                  location { id name }
                  quantities(names: ["on_hand", "available"]) { name quantity }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

SETZEN = """
mutation($input: InventorySetQuantitiesInput!) {
  inventorySetQuantities(input: $input) {
    inventoryAdjustmentGroup { createdAt reason }
    userErrors { field message }
  }
}
"""


def zahl(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return int(float(str(v).replace(",", ".")))
    except ValueError:
        return None


def blatt_lesen(pfad):
    wb = openpyxl.load_workbook(pfad, data_only=True)
    if BLATT not in wb.sheetnames:
        sys.exit(f"Blatt „{BLATT}“ nicht gefunden in {os.path.basename(pfad)}.")
    ws = wb[BLATT]
    kopf = [c.value for c in next(ws.iter_rows(max_row=1))]
    i = {n: j for j, n in enumerate(kopf) if n}
    for pflicht in ("Shopify-Handle", "Bestand lt. Shopify", "Produkt"):
        if pflicht not in i:
            sys.exit(f"Spalte „{pflicht}“ fehlt — ist das die Zählliste?")

    zeilen = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        handle = str(r[i["Shopify-Handle"]] or "").strip()
        if not handle:
            continue
        gezaehlt = zahl(r[i["Ist-Bestand gezählt"]]) if "Ist-Bestand gezählt" in i else None
        quelle = "Ist-Bestand gezählt"
        if gezaehlt is None:
            gezaehlt = zahl(r[i["Bestand lt. Shopify"]])
            quelle = "Bestand lt. Shopify"
        if gezaehlt is None:
            continue
        zeilen.append({"handle": handle, "titel": str(r[i["Produkt"]] or ""),
                       "soll": gezaehlt, "quelle": quelle})
    return zeilen


def lagerorte():
    a = shopify_http.execute(LAGER)
    if a.get("_error"):
        sys.exit(f"Lagerorte nicht lesbar: {a['_error']}")
    return [k["node"] for k in a.get("locations", {}).get("edges", [])
            if k["node"].get("isActive")]


def produkt_holen(handle):
    for versuch in range(5):
        a = shopify_http.execute(PRODUKT, {"handle": handle})
        f = str(a.get("_error", ""))
        if not f:
            return a.get("productByHandle"), ""
        if "THROTTLED" in f.upper() and versuch < 4:
            time.sleep(2 ** versuch)
            continue
        return None, f
    return None, "dauerhaft gedrosselt"


def menge(knoten, name):
    for q in knoten.get("quantities") or []:
        if q.get("name") == name:
            return q.get("quantity")
    return None


def main():
    dateien = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not dateien:
        sys.exit("Zählliste angeben:\n"
                 "  python3 bestand-korrigieren.py <datei.xlsx>")
    pfad = dateien[0]
    if not os.path.exists(pfad):
        sys.exit(f"{pfad} nicht gefunden.")
    live = "--live" in sys.argv
    lager_wunsch = ""
    if "--lager" in sys.argv:
        k = sys.argv.index("--lager")
        if k + 1 < len(sys.argv):
            lager_wunsch = sys.argv[k + 1].strip().lower()

    if not live:
        print("PROBELAUF — es wird nichts geändert.")
        print("Zum Schreiben:  python3 bestand-korrigieren.py <datei.xlsx> --live\n")

    zeilen = blatt_lesen(pfad)
    print(f"{len(zeilen)} Zeilen mit Handle und Zahl gelesen")

    orte = lagerorte()
    print(f"{len(orte)} aktive Lagerorte: {', '.join(o['name'] for o in orte)}\n")

    aendern, gleich = [], 0
    uebersprungen = []

    print("Vergleiche mit dem aktuellen Shopify-Bestand …")
    for n, z in enumerate(zeilen, 1):
        p, fehler = produkt_holen(z["handle"])
        if fehler:
            uebersprungen.append((z, f"nicht lesbar: {fehler}"))
            continue
        if not p:
            uebersprungen.append((z, "Produkt nicht gefunden"))
            continue

        varianten = [k["node"] for k in p.get("variants", {}).get("edges", [])]
        if len(varianten) != 1:
            uebersprungen.append(
                (z, f"{len(varianten)} Varianten — Gesamtzahl nicht aufteilbar"))
            continue
        v = varianten[0]
        lager_art = v.get("inventoryItem") or {}
        if not lager_art.get("tracked"):
            uebersprungen.append((z, "Bestand wird nicht verfolgt"))
            continue

        ebenen = [k["node"] for k in
                  (lager_art.get("inventoryLevels") or {}).get("edges", [])]
        if lager_wunsch:
            ebenen = [e for e in ebenen
                      if lager_wunsch in (e["location"]["name"] or "").lower()]
        if len(ebenen) != 1:
            uebersprungen.append(
                (z, f"{len(ebenen)} Lagerorte — mit --lager <Name> eingrenzen"))
            continue
        ebene = ebenen[0]

        ist = menge(ebene, "on_hand")
        if ist is None:
            ist = menge(ebene, "available")
        if ist is None:
            uebersprungen.append((z, "Bestand nicht lesbar"))
            continue

        if int(ist) == int(z["soll"]):
            gleich += 1
            continue

        aendern.append({**z, "ist": int(ist), "titel_shop": p.get("title", ""),
                        "lager_art": lager_art["id"],
                        "ort": ebene["location"]["id"],
                        "ort_name": ebene["location"]["name"]})
        if n % 25 == 0:
            print(f"  … {n}/{len(zeilen)}")
        time.sleep(0.2)

    print(f"\n{gleich} Zeilen stimmen bereits überein")
    if uebersprungen:
        print(f"{len(uebersprungen)} übersprungen:")
        for z, grund in uebersprungen[:20]:
            print(f"    {z['titel'][:44]:<44} {grund}")
        if len(uebersprungen) > 20:
            print(f"    … und {len(uebersprungen)-20} weitere")

    if not aendern:
        print("\nNichts zu ändern.")
        return

    print(f"\n{'='*72}\n{len(aendern)} ÄNDERUNGEN\n{'='*72}")
    for a in aendern:
        pfeil = "↓" if a["soll"] < a["ist"] else "↑"
        print(f"  {a['ist']:>4} {pfeil} {a['soll']:<4}  {a['titel'][:44]:<44}"
              f"  [{a['quelle']}]")
    hoch = [a for a in aendern if a["soll"] > a["ist"]]
    if hoch:
        print(f"\n{len(hoch)} davon ERHÖHEN den Bestand. Beim Aufarbeiten von")
        print("Ladenhütern ist das ungewöhnlich — bitte noch einmal ansehen:")
        for a in hoch:
            print(f"    {a['ist']} → {a['soll']}  {a['titel'][:50]}")

    if not live:
        print(f"\n{len(aendern)} Änderungen bereit. Mit --live schreiben.")
        return

    antwort = input(f"\n{len(aendern)} Bestände setzen? (ja/NEIN): ").strip()
    if antwort.lower() != "ja":
        print("Abgebrochen.")
        return

    ok = fehler = 0
    for a in aendern:
        e = shopify_http.execute(SETZEN, {"input": {
            "name": "on_hand",
            "reason": GRUND,
            "ignoreCompareQuantity": True,
            "quantities": [{"inventoryItemId": a["lager_art"],
                            "locationId": a["ort"],
                            "quantity": a["soll"]}]}})
        meldungen = e.get("_error") or [
            u.get("message")
            for u in (e.get("inventorySetQuantities", {}).get("userErrors") or [])]
        if meldungen:
            fehler += 1
            txt = str(meldungen).lower()
            if "scope" in txt or "access denied" in txt:
                print("\nDer App fehlt der Zugriffsbereich write_inventory.")
                print("Nachtragen im Dev Dashboard, dann Installation bestätigen.")
                return
            print(f"  ✗ {a['titel'][:40]}: {meldungen}")
        else:
            ok += 1
        time.sleep(0.25)

    print(f"\nFertig: {ok} Bestände gesetzt, {fehler} fehlgeschlagen")
    print("Nachvollziehbar in Shopify unter Produkt → Bestand → Verlauf.")


if __name__ == "__main__":
    main()

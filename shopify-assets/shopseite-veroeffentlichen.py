"""
shopseite-veroeffentlichen.py — fehlende Zielseiten nachtragen
===============================================================

Produkte, die im Google-Kanal stehen, aber keine Seite im Onlineshop
haben, kann Google nicht bewerben: Es gibt keine Zielseite, auf die eine
Anzeige führen könnte. Merchant Center meldet dafür
"Seite nicht verfügbar".

Dieses Skript veröffentlicht sie im Onlineshop — oder nimmt sie wahlweise
aus dem Google-Kanal, wenn sie dort nichts verloren haben.

VORGEHEN
--------
1. kanal-uebersicht.py laufen lassen, es schreibt google-ohne-shopseite.csv
2. Diese CSV öffnen und die Spalte "Aktion" füllen:

       shop      Produkt im Onlineshop veröffentlichen
       google    aus dem Google-Kanal entfernen
       (leer)    nichts tun

   Zeilen, die du gar nicht anfassen willst, kannst du auch löschen.

3. Dieses Skript ausführen:

       cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
       python3 shopseite-veroeffentlichen.py          # Probelauf
       python3 shopseite-veroeffentlichen.py --live   # schreibt

Ohne ausgefüllte Aktion-Spalte schlägt das Skript "shop" für alle vor —
der Probelauf zeigt dann, was es täte.
"""

import csv
import os
import sys
import time

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

QUELLE = "google-ohne-shopseite.csv"

KANAELE = """
{ publications(first: 25) { edges { node { id name } } } }
"""

VEROEFFENTLICHEN = """
mutation($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    userErrors { field message }
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


def kanal_ids():
    """Publication-IDs für Online Store und Google & YouTube."""
    antwort = shopify_http.execute(KANAELE)
    if antwort.get("_error"):
        sys.exit(f"Kanäle nicht lesbar: {antwort['_error']}")
    gefunden = {}
    for kante in antwort.get("publications", {}).get("edges", []):
        n = kante["node"]
        name = (n.get("name") or "").lower()
        if "online store" in name:
            gefunden["shop"] = n["id"]
        elif "google" in name:
            gefunden["google"] = n["id"]
    fehlend = {"shop", "google"} - set(gefunden)
    if fehlend:
        sys.exit(f"Kanal nicht gefunden: {', '.join(fehlend)}")
    return gefunden


def zeilen_lesen():
    if not os.path.exists(QUELLE):
        sys.exit(f"{QUELLE} nicht gefunden.\n"
                 "Erst kanal-uebersicht.py laufen lassen.")
    with open(QUELLE, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def main():
    live = "--live" in sys.argv
    if not live:
        print("PROBELAUF — es wird nichts geändert.")
        print("Zum Schreiben:  python3 shopseite-veroeffentlichen.py --live\n")

    zeilen = zeilen_lesen()
    kanal = kanal_ids()

    aufgaben = []
    for z in zeilen:
        pid = (z.get("Produkt-ID") or "").strip()
        if not pid:
            continue
        aktion = (z.get("Aktion") or "").strip().lower()
        if aktion and aktion not in ("shop", "google"):
            print(f"  unbekannte Aktion '{aktion}' bei {z.get('Titel','')} — übersprungen")
            continue
        aufgaben.append({
            "id": pid,
            "titel": z.get("Titel", ""),
            "marke": z.get("Marke", ""),
            "bild": z.get("Bild", ""),
            "bestand": z.get("Bestand", ""),
            "aktion": aktion or "shop",     # Vorgabe
            "vorgabe": not aktion,
        })

    if not aufgaben:
        print("Keine Zeilen mit Produkt-ID gefunden.")
        return

    vorgabe = sum(1 for a in aufgaben if a["vorgabe"])
    if vorgabe:
        print(f"Hinweis: bei {vorgabe} Zeilen ist die Spalte 'Aktion' leer —")
        print("         sie werden als 'shop' behandelt (im Onlineshop veröffentlichen).\n")

    print(f"{'Aktion':<8} {'Bild':<5} {'Best.':>5}  {'Marke':<14} Titel")
    print("─" * 78)
    for a in aufgaben:
        print(f"{a['aktion']:<8} {a['bild']:<5} {a['bestand']:>5}  "
              f"{a['marke'][:14]:<14} {a['titel'][:38]}")

    ohne_bild = [a for a in aufgaben if a["aktion"] == "shop" and a["bild"] == "NEIN"]
    if ohne_bild:
        print(f"\n  ⚠ {len(ohne_bild)} davon haben kein Bild. Im Onlineshop wären sie")
        print("    ohne Abbildung sichtbar — vorher Bild ergänzen oder auf 'google' setzen.")

    ohne_bestand = [a for a in aufgaben
                    if a["aktion"] == "shop" and str(a["bestand"]).strip() in ("0", "")]
    if ohne_bestand:
        print(f"\n  ⚠ {len(ohne_bestand)} davon haben keinen Bestand. Sie erscheinen im Shop")
        print("    als ausverkauft und lösen in Google weiterhin keine Anzeige aus.")

    if not live:
        print(f"\n{len(aufgaben)} Änderungen bereit. Mit --live ausführen.")
        return

    antwort = input(f"\n{len(aufgaben)} Produkte ändern? (ja/NEIN): ").strip()
    if antwort.lower() != "ja":
        print("Abgebrochen.")
        return

    ok = fehler = 0
    for i, a in enumerate(aufgaben, 1):
        gid = f"gid://shopify/Product/{a['id']}"
        if a["aktion"] == "shop":
            e = shopify_http.execute(VEROEFFENTLICHEN, {
                "id": gid, "input": [{"publicationId": kanal["shop"]}]})
            block = e.get("publishablePublish", {})
        else:
            e = shopify_http.execute(ZURUECKZIEHEN, {
                "id": gid, "input": [{"publicationId": kanal["google"]}]})
            block = e.get("publishableUnpublish", {})

        meldungen = e.get("_error") or [u.get("message")
                                        for u in (block.get("userErrors") or [])]
        if meldungen:
            fehler += 1
            print(f"  ✗ {a['titel'][:40]}: {meldungen}")
        else:
            ok += 1
        if i % 10 == 0:
            print(f"  … {i}/{len(aufgaben)}")
        time.sleep(0.25)

    print(f"\nFertig: {ok} geändert, {fehler} fehlgeschlagen")
    if ok:
        print("Merchant Center holt den Feed innerhalb von 24 Stunden neu.")


if __name__ == "__main__":
    main()

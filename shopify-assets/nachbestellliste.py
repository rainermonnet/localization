"""
nachbestellliste.py — belegte Nachfrage trifft leeres Lager
=============================================================

Liest den Produktexport aus dem Merchant Center und findet Artikel, die
Klicks bekommen haben und nicht lieferbar sind. Das ist Nachfrage, die
nachweislich da war und ins Leere lief.

WARUM NICHT EINFACH ALLE AUSVERKAUFTEN
---------------------------------------
„Null Klicks" ist bei ausverkaufter Ware kein Beleg für fehlende
Nachfrage: Google liefert ausverkaufte Artikel nicht aus, also können sie
gar keine Klicks sammeln. Der Schluss wäre zirkulär.

Umgekehrt ist „Klicks trotz Ausverkauf" ein harter Beleg: Diese Artikel
wurden gefunden und angeklickt, bevor oder obwohl das Lager leer war.

Ausverkaufte Artikel im Feed zu lassen kostet übrigens nichts — Google
liefert sie nicht aus und behält ihre Historie. Entfernen bringt keinen
Gewinn, Nachbestellen schon.

EXPORT BESORGEN
---------------
Merchant Center → Produkte → Alle Produkte → Herunterladen
Die entpackte .tsv-Datei neben dieses Skript legen.

AUSFÜHREN
---------
    python3 nachbestellliste.py produkte_2026-10-05_16-09-56.tsv

Braucht keinen Shopify-Zugang — es liest nur die Exportdatei.
"""

import csv
import sys
from collections import defaultdict


def klicks(zeile):
    try:
        return int((zeile.get("Alle Klicks") or "0").strip() or 0)
    except ValueError:
        return 0


def ausverkauft(zeile):
    return "nicht" in (zeile.get("Verfügbarkeit") or "").lower()


def preis(zeile):
    roh = (zeile.get("Preis") or "").strip()
    for teil in roh.replace(",", ".").split():
        try:
            return float(teil)
        except ValueError:
            continue
    return 0.0


def shopify_id(zeile):
    """shopify_DE_<produkt>_<variante> → (produkt, variante)"""
    teile = (zeile.get("ID") or "").split("_")
    return (teile[2], teile[3]) if len(teile) >= 4 else ("", "")


def main():
    if len(sys.argv) < 2:
        sys.exit("Exportdatei angeben:\n"
                 "  python3 nachbestellliste.py produkte_….tsv")
    pfad = sys.argv[1]

    try:
        with open(pfad, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f, delimiter="\t"))
    except FileNotFoundError:
        sys.exit(f"{pfad} nicht gefunden.")
    except Exception as e:
        sys.exit(f"Datei nicht lesbar: {e}")

    if not rows or "Verfügbarkeit" not in rows[0]:
        sys.exit("Das sieht nicht nach einem Merchant-Center-Produktexport aus.")

    leer = [z for z in rows if ausverkauft(z)]
    gefragt = sorted([z for z in leer if klicks(z) > 0], key=klicks, reverse=True)

    print(f"{len(rows)} Varianten im Feed")
    print(f"{len(leer)} nicht lieferbar")
    print(f"{len(gefragt)} davon mit belegten Klicks\n")

    if not gefragt:
        print("Keine ausverkaufte Ware mit Klickhistorie. Nichts nachzubestellen,")
        print("was sich aus diesen Daten begründen ließe.")
        return

    nach_marke = defaultdict(list)
    for z in gefragt:
        nach_marke[(z.get("Marke") or "—").strip()].append(z)

    print("=" * 72)
    print("NACHBESTELLEN — nach Lieferant")
    print("=" * 72)
    for marke, artikel in sorted(nach_marke.items(),
                                 key=lambda t: -sum(klicks(z) for z in t[1])):
        summe = sum(klicks(z) for z in artikel)
        print(f"\n{marke}  ({len(artikel)} Artikel, {summe} Klicks)")
        for z in sorted(artikel, key=klicks, reverse=True):
            p, v = shopify_id(z)
            sku = (z.get("sku") or "").strip()
            print(f"  {klicks(z):>3} Klicks  {preis(z):>7.2f} €  "
                  f"{(z.get('Titel') or '')[:46]}")
            print(f"              SKU {sku or '—':<14} Produkt {p}")

    gesamt_klicks = sum(klicks(z) for z in gefragt)
    gesamt_wert = sum(preis(z) for z in gefragt)
    print("\n" + "=" * 72)
    print(f"{len(gefragt)} Artikel · {gesamt_klicks} Klicks ins Leere · "
          f"Warenwert {gesamt_wert:.2f} €")
    print("=" * 72)
    print("\nDie Klicks sind bereits passiert — die Nachfrage ist belegt,")
    print("nicht geschätzt. Bei diesen Artikeln lohnt die Nachbestellung")
    print("eher als bei allem anderen im Lager.")

    # Datei zum Mitnehmen
    with open("nachbestellen.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Marke", "Artikel", "SKU", "Klicks", "Preis",
                    "Shopify Produkt-ID", "Shopify Varianten-ID"])
        for z in gefragt:
            p, v = shopify_id(z)
            w.writerow([(z.get("Marke") or "").strip(), (z.get("Titel") or "").strip(),
                        (z.get("sku") or "").strip(), klicks(z),
                        f"{preis(z):.2f}", p, v])
    print("\nGeschrieben: nachbestellen.csv")


if __name__ == "__main__":
    main()

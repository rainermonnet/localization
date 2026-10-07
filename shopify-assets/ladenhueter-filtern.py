"""
ladenhueter-filtern.py — aus 1156 Artikeln eine zählbare Liste machen
=======================================================================

Die Ladenhüter-Auswertung listet 1156 Artikel zum Nachzählen. Das ist
mehr Arbeit, als die Ware wert ist: 836 davon haben zusammen 18.788 €
Lagerwert, im Schnitt 22 € je Artikel.

WARUM „12 STATT 10 MONATE" NICHTS BRINGT
-----------------------------------------
Alle 1091 Ladenhüter haben als letzten Verkauf „nie" — kein einziger
hat ein Datum. Sie haben nicht vor zehn Monaten zuletzt verkauft,
sondern seit Beginn der Shopify-Daten (24.11.2025) überhaupt nicht.
Ein längeres Fenster kann nichts ausschließen, weil nichts darin liegt.
Vor dem 24.11.2025 fehlen die HelloCash-Daten vollständig.

WAS STATTDESSEN HILFT
---------------------
1. ALTER IM SORTIMENT. Das ist die sinnvolle Fassung der Jahres-Idee:
   Ein Artikel, der erst seit drei Monaten im Katalog steht, kann nicht
   zehn Monate lang nichts verkauft haben. Mit --mit-shopify wird das
   Anlagedatum je Produkt geholt; wer kürzer als --monate im Sortiment
   ist, fliegt raus. Das trifft die goki-Neuheiten und die KISME-Welle.

2. WERT UND MENGE. Gezählt wird, was sich lohnt: ab --ab-wert Euro
   Lagerwert oder ab --ab-stueck Stück. Ein Einzelstück für 8 € ist
   kein Fall für eine Inventur.

3. BÜCHER RAUS. 231 Titel mit Preisbindung. Herabsetzen ist nicht
   erlaubt, Rabattaktion also sinnlos — das ist ein Fall für
   Remission oder Mängelexemplar, nicht für diese Liste.

4. FREITEXT-VERDACHT. Rund 500 Stück wurden an der Kasse als Freitext
   gebucht und sind keinem Produkt zugeordnet. Die Ware ist weg, der
   Bestand steht noch — solche Artikel erscheinen fälschlich als
   Ladenhüter. Taucht ein Freitext-Begriff im Produkttitel auf, wird
   die Zeile markiert: erst recherchieren, nicht zählen.

AUSFÜHREN
---------
    python3 ladenhueter-filtern.py Ladenhueter_Zwergenladen_2026-09.xlsx

    # mit Anlagedatum aus Shopify (braucht shopify_http.py daneben)
    python3 ladenhueter-filtern.py <datei.xlsx> --mit-shopify

    # Schwellen anpassen
    python3 ladenhueter-filtern.py <datei.xlsx> --ab-wert 100 --ab-stueck 5

    # nur nach Wert, Mengenregel aus
    python3 ladenhueter-filtern.py <datei.xlsx> --ab-wert 100 --ab-stueck 0

Die beiden Schwellen wirken als ODER: Ein Artikel bleibt drin, wenn er
teuer genug ODER zahlreich genug ist. „--ab-wert 100" allein lässt also
weiterhin alles mit 3 und mehr Stück stehen.

Schreibt `ladenhueter-kurz.xlsx`. Die Ursprungsdatei bleibt unberührt —
es wird nichts überschrieben und nichts an Shopify gesendet.
"""

import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

try:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
except ImportError:
    sys.exit("openpyxl fehlt.  Abhilfe:  pip3 install openpyxl")

AB_WERT = 50.0        # Lagerwert VK, ab dem gezählt wird
AB_STUECK = 3         # oder: so viele Stück auf Lager
MONATE = 12           # Mindestalter im Sortiment
AUSGABE = "ladenhueter-kurz.xlsx"
MAX_TREFFER = 3       # ein Freitext-Begriff, der auf mehr Artikel passt,
                      # ist ein Marken- oder Gattungsname und belegt nichts

# Warengruppen, die nicht in die Zählliste gehören (Preisbindung)
RAUS_GRUPPE = re.compile(r"b(ü|ue)cher|postkarte", re.I)

# Freitext-Begriffe, die zu allgemein sind, um etwas zu belegen
ZU_ALLGEMEIN = {
    "benutzerdefinierter verkauf", "verkauf", "ws", "wb", "sonstiges",
    "diverses", "div", "artikel", "ware", "rest", "kleinteil",
}

PRODUKTE = """
query($cursor: String) {
  products(first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    edges { node { handle createdAt } }
  }
}
"""


def zahl(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def blatt_lesen(wb, name):
    if name not in wb.sheetnames:
        return [], {}
    ws = wb[name]
    kopf = [c.value for c in next(ws.iter_rows(max_row=1))]
    spalte = {n: k for k, n in enumerate(kopf) if n}
    return list(ws.iter_rows(min_row=2, values_only=True)), spalte


def freitext_begriffe(wb):
    """Begriffe aus dem Blatt „Freitext-Verkäufe", die als Beleg taugen."""
    zeilen, spalte = blatt_lesen(wb, "Freitext-Verkäufe")
    name_sp = next((k for n, k in spalte.items() if "eingetippt" in (n or "").lower()), 0)
    begriffe = set()
    for r in zeilen:
        if name_sp >= len(r):
            continue
        b = str(r[name_sp] or "").strip().lower()
        # Zu kurze oder zu allgemeine Begriffe treffen alles und belegen nichts
        if len(b) >= 4 and b not in ZU_ALLGEMEIN:
            begriffe.add(b)
    return begriffe


def anlagedaten():
    """handle → Anlagedatum. Leer, wenn Shopify nicht erreichbar ist."""
    try:
        import shopify_http
    except ImportError:
        print("  shopify_http.py nicht gefunden — Alter wird übersprungen.")
        return {}

    daten, cursor, seiten = {}, None, 0
    while True:
        antwort = shopify_http.execute(PRODUKTE, {"cursor": cursor})
        fehler = antwort.get("_error", "")
        if fehler:
            if "THROTTLED" in str(fehler).upper() and seiten < 20:
                time.sleep(2)
                continue
            print(f"  Shopify nicht lesbar: {fehler}")
            return daten
        block = antwort.get("products", {})
        for k in block.get("edges", []):
            n = k["node"]
            if n.get("handle") and n.get("createdAt"):
                daten[n["handle"]] = n["createdAt"][:10]
        seiten += 1
        if not block.get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = block["pageInfo"]["endCursor"]
        time.sleep(0.25)
    print(f"  {len(daten)} Anlagedaten geladen")
    return daten


def main():
    argumente = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not argumente:
        sys.exit(__doc__.split("AUSFÜHREN")[1].strip())
    pfad = argumente[0]
    if not os.path.exists(pfad):
        sys.exit(f"{pfad} nicht gefunden.")

    def schalter(name, standard):
        if name in sys.argv:
            k = sys.argv.index(name)
            if k + 1 < len(sys.argv):
                return type(standard)(sys.argv[k + 1])
        return standard

    ab_wert = schalter("--ab-wert", AB_WERT)
    ab_stueck = schalter("--ab-stueck", AB_STUECK)
    monate = schalter("--monate", MONATE)

    wb = openpyxl.load_workbook(pfad, data_only=True)
    zeilen, sp = blatt_lesen(wb, "Aktionsliste")
    if not sp:
        sys.exit("Blatt „Aktionsliste“ nicht gefunden — ist das die richtige Datei?")
    kopf = [None] * len(sp)
    for n, k in sp.items():
        kopf[k] = n

    begriffe = freitext_begriffe(wb)
    print(f"{len(zeilen)} Zeilen gelesen · {len(begriffe)} Freitext-Begriffe\n")

    daten = {}
    if "--mit-shopify" in sys.argv:
        print("Hole Anlagedaten aus Shopify …")
        daten = anlagedaten()
    grenze = (datetime.now(timezone.utc) - timedelta(days=int(monate * 30.44))
              ).strftime("%Y-%m-%d")

    behalten, weg = [], {"Buch": 0, "zu klein": 0, "zu neu": 0}
    wert_weg = 0.0
    for r in zeilen:
        if not r[sp["Produkt"]]:
            continue
        wert = zahl(r[sp["Lagerwert VK €"]])
        stueck = zahl(r[sp["Bestand lt. Shopify"]])
        gruppe = str(r[sp["Warengruppe"]] or "")
        handle = str(r[sp["Shopify-Handle"]] or "") if "Shopify-Handle" in sp else ""
        titel = str(r[sp["Produkt"]]).lower()

        if RAUS_GRUPPE.search(gruppe):
            weg["Buch"] += 1
            wert_weg += wert
            continue
        angelegt = daten.get(handle, "")
        if angelegt and angelegt > grenze:
            weg["zu neu"] += 1
            wert_weg += wert
            continue
        # --ab-stueck 0 schaltet die Mengenregel ab: dann zählt nur der Wert
        gross_genug = wert >= ab_wert or (ab_stueck > 0 and stueck >= ab_stueck)
        if not gross_genug:
            weg["zu klein"] += 1
            wert_weg += wert
            continue

        behalten.append([list(r), angelegt, titel])

    # Freitext-Zuordnung erst jetzt, weil sie den ganzen Bestand braucht:
    # Ein Begriff, der auf viele Artikel passt, belegt bei keinem etwas.
    # „ostheimer" traf 33 Produkte, „taschen" ein Taschenmesser — das ist
    # ein Marken- oder Gattungsname, kein Beleg für einen Verkauf.
    marken = {str(z[0][sp["Marke"]] or "").strip().lower() for z in behalten}
    for eintrag in behalten:
        titel = eintrag[2]
        passend = [b for b in begriffe
                   if b not in marken
                   and re.search(r"(?<!\w)" + re.escape(b) + r"(?!\w)", titel)]
        eintrag[2] = passend
    haeufigkeit = Counter(b for z in behalten for b in z[2])
    for eintrag in behalten:
        eindeutig = [b for b in eintrag[2] if haeufigkeit[b] <= MAX_TREFFER]
        eintrag[2] = max(eindeutig, key=len) if eindeutig else ""
    behalten = [tuple(z) for z in behalten]

    behalten.sort(key=lambda t: -zahl(t[0][sp["Lagerwert VK €"]]))

    wert_bleibt = sum(zahl(z[0][sp["Lagerwert VK €"]]) for z in behalten)
    verdacht = sum(1 for z in behalten if z[2])

    print(f"BLEIBT ZU ZÄHLEN: {len(behalten)} Artikel · {wert_bleibt:,.0f} € Lagerwert VK"
          .replace(",", "."))
    print(f"ENTFÄLLT:         {sum(weg.values())} Artikel · {wert_weg:,.0f} €"
          .replace(",", "."))
    for grund, n in weg.items():
        if n:
            print(f"    {n:>5}  {grund}")
    if verdacht:
        print(f"\n{verdacht} Zeilen mit Freitext-Verdacht — dort wurde unter"
              "\nähnlichem Namen an der Kasse gebucht. Erst prüfen, nicht zählen.")
    if not daten and "--mit-shopify" in sys.argv:
        print("\nOhne Anlagedaten: Artikel, die erst kürzlich ins Sortiment kamen,"
              "\nstehen weiterhin in der Liste.")

    # ── Ausgabe ──
    neu = openpyxl.Workbook()
    ws = neu.active
    ws.title = "Zählliste"
    kopfzeile = kopf + ["Im Sortiment seit", "Freitext-Verdacht"]
    ws.append(kopfzeile)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    gelb = PatternFill("solid", fgColor="FFF2CC")
    for r, angelegt, treffer in behalten:
        ws.append(list(r) + [angelegt, treffer])
        if treffer:
            for c in ws[ws.max_row]:
                c.fill = gelb
    ws.freeze_panes = "A2"
    for k, n in enumerate(kopfzeile, 1):
        ws.column_dimensions[ws.cell(row=1, column=k).column_letter].width = \
            min(38, max(11, len(str(n)) + 2))

    info = neu.create_sheet("Definition")
    for z in [
        ["Zählliste Ladenhüter — gekürzt"],
        [f"Erzeugt am {datetime.now():%d.%m.%Y} aus {os.path.basename(pfad)}"],
        [],
        ["Aufgenommen wird ein Artikel, wenn alles davon zutrifft:"],
        [f"  • Lagerwert VK ab {ab_wert:.0f} €"
         + (f" ODER Bestand ab {ab_stueck} Stück" if ab_stueck > 0
            else "  (Mengenregel abgeschaltet)")],
        ["  • keine Bücher, keine Postkarten (Preisbindung — Remission statt Rabatt)"],
        [f"  • seit mindestens {monate} Monaten im Sortiment"
         + ("" if daten else "  (nicht geprüft: ohne --mit-shopify gelaufen)")],
        [],
        ["Warum nicht einfach das Zeitfenster verlängern:"],
        ["Alle Ladenhüter haben als letzten Verkauf „nie“, keiner ein Datum."],
        ["Sie haben seit Beginn der Shopify-Daten (24.11.2025) nie verkauft."],
        ["Ein längeres Fenster schließt deshalb keinen einzigen Artikel aus."],
        ["Vor dem 24.11.2025 fehlen die HelloCash-Daten vollständig."],
        [],
        ["Gelbe Zeilen: Freitext-Verdacht."],
        ["Unter ähnlichem Namen wurde an der Kasse als Freitext gebucht."],
        ["Die Ware ist vermutlich verkauft, nur der Bestand steht noch."],
        [],
        [f"Aufgenommen: {len(behalten)} Artikel · {wert_bleibt:.0f} € Lagerwert VK"],
        [f"Entfallen:   {sum(weg.values())} Artikel · {wert_weg:.0f} €"],
    ]:
        info.append(z)
    info.column_dimensions["A"].width = 78

    neu.save(AUSGABE)
    print(f"\nGeschrieben: {AUSGABE}")
    print("Sortiert nach Lagerwert — von oben abarbeiten, jederzeit aufhören.")


if __name__ == "__main__":
    main()

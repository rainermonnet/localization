"""
goki.py — EAN-Berechnung für goki / Gollnest & Kiesel
======================================================

REGEL
-----
goki vergibt seine EANs nach einem festen Schema:

    EAN-13 = 4013594 + Artikelnummer (5-stellig, links mit Nullen) + Prüfziffer

Beispiele:
    Art-Nr   824  ->  4013594 + 00824 + 2  =  4013594008242
    Art-Nr 13278  ->  4013594 + 13278 + 7  =  4013594132787
    Art-Nr 80620  ->  4013594 + 80620 + 6  =  4013594806206

`4013594` ist das GS1-Basisnummernpräfix von Gollnest & Kiesel:
401 = Deutschland, der Rest die Unternehmensnummer.

GEPRÜFT
-------
Gegen die Preisliste „Neuheitenkatalog 2025" (128 Artikel mit EAN):
128 von 128 EANs exakt reproduziert, keine Abweichung.

Damit brauchst du für einen goki-Artikel nie wieder eine EAN nachzuschlagen —
die Artikelnummer genügt.

NUTZUNG
-------
    from goki import ean_von_artikelnummer
    ean_von_artikelnummer("57305")     -> "4013594573054"
    ean_von_artikelnummer(80620)       -> "4013594806206"
"""

import re

GS1_PRAEFIX = "4013594"
ARTIKEL_STELLEN = 5


def pruefziffer(body: str) -> int:
    """
    GS1-Prüfziffer für die ersten 12 Stellen einer EAN-13.
    Gewichte ab links: 1,3,1,3,…
    """
    summe = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(body))
    return (10 - (summe % 10)) % 10


def ean_von_artikelnummer(artikelnummer) -> str:
    """
    Rechnet eine goki-Artikelnummer in die zugehörige EAN-13 um.

    Wirft ValueError, wenn die Nummer nicht aus 1–5 Ziffern besteht —
    lieber ein klarer Fehler als eine falsche EAN auf dem Etikett.
    """
    nr = str(artikelnummer).strip()
    if not re.fullmatch(r"\d{1,5}", nr):
        raise ValueError(
            f"'{artikelnummer}' ist keine goki-Artikelnummer "
            f"(erwartet 1–5 Ziffern)"
        )
    body = GS1_PRAEFIX + nr.zfill(ARTIKEL_STELLEN)
    return body + str(pruefziffer(body))


def ist_goki_ean(ean: str) -> bool:
    """Prüft, ob eine EAN aus dem goki-Nummernkreis stammt."""
    e = str(ean).strip()
    return bool(re.fullmatch(r"\d{13}", e)) and e.startswith(GS1_PRAEFIX)


def artikelnummer_von_ean(ean: str):
    """
    Umkehrung: zieht die Artikelnummer aus einer goki-EAN.
    Rückgabe None, wenn die EAN nicht zu goki gehört oder die
    Prüfziffer nicht stimmt.
    """
    e = str(ean).strip()
    if not ist_goki_ean(e):
        return None
    if pruefziffer(e[:12]) != int(e[12]):
        return None
    return e[7:12].lstrip("0") or "0"


def umrechnen(zeilen):
    """
    Wandelt eine Liste von Artikelnummern (optional mit '| Beschriftung')
    in Barcode-Zeilen für die Werkbank.

    Rückgabe: (zeilen, fehler)
    """
    fertig, fehler = [], []
    for roh in zeilen:
        roh = roh.strip()
        if not roh or roh.startswith("#"):
            continue
        if "|" in roh:
            nr, name = roh.split("|", 1)
            nr, name = nr.strip(), name.strip()
        else:
            nr, name = roh, ""
        try:
            ean = ean_von_artikelnummer(nr)
        except ValueError as exc:
            fehler.append((roh, str(exc)))
            continue
        fertig.append(f"{ean} | {name}".strip(" |"))
    return fertig, fehler

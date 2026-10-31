"""
barcode_feld.py — Barcodes lesen und schreiben, egal welche API-Version
=========================================================================

Shopify hat `ProductVariant.barcode` abgelöst. Ab API-Version 2026-10:

    LESEN    barcode: String        →  barcodes(first: n) { nodes { value type } }
    SCHREIBEN  barcode: "4013594…"  →  barcodes: [{ value: "4013594…", type: EAN }]

Beim Schreiben ist `barcode` in `ProductVariantsBulkInput` nicht
veraltet, sondern **ersatzlos verschwunden**. Wer es weiter sendet,
bekommt einen Fehler, keine Warnung.

`shopify_http.py` ist auf 2025-01 festgelegt, dort läuft noch alles.
Shopify nimmt Versionen aber nach etwa einem Jahr aus dem Betrieb, und
dann hören mehrere Skripte am selben Tag auf zu arbeiten.

WAS DIESES MODUL TUT
--------------------
Es kapselt den Unterschied an einer Stelle. Die Skripte fragen nicht
mehr „welche Version läuft", sondern benutzen:

    import barcode_feld as bc

    ABFRAGE = f"variants(first: 10) {{ edges {{ node {{ id sku {bc.LESEN} }} }} }}"
    wert = bc.lies(variantenknoten)
    eingabe = {"id": vid, **bc.schreiben("4013594123458")}

Die Erkennung läuft einmal je Programmlauf über eine winzige Abfrage
gegen den Shop — nicht über einen Versionsvergleich. Wann Shopify das
neue Feld eingeführt hat, muss so niemand wissen, und ein Irrtum über
die Einführungsversion kann keine falschen Barcodes erzeugen.

BARCODE-TYPEN
-------------
Neu ist, dass jeder Barcode einen Typ trägt: ASIN, EAN, GTIN, ISBN,
NS_PID, UPC. Für den Zwergenladen zählen EAN (goki, HENRYS, Spielzeug)
und ISBN (Bücher). `typ_fuer()` leitet ihn aus dem Wert ab — 978/979
am Anfang heißt ISBN, sonst EAN beziehungsweise UPC bei zwölf Stellen.

Das ist mehr als Kosmetik: Bei den Büchern steht damit erkennbar eine
ISBN im Feld und keine beliebige Zahl.

PRÜFEN
------
    python3 barcode-umstellung-pruefen.py
"""

import re

try:
    import shopify_http
except ImportError:                      # Modul auch ohne Zugang importierbar
    shopify_http = None

# Wie viele Barcodes je Variante gelesen werden. Shopify erlaubt bis zu 20;
# der erste ist der, den die alten Skripte meinen.
ANZAHL = 5

_PROBE = """
query { productVariants(first: 1) { nodes { barcodes(first: 1) { nodes { value } } } } }
"""

_neu = None          # None = noch nicht erkannt


def neue_api(erneut: bool = False) -> bool:
    """True, wenn der Shop das Feld `barcodes` kennt.

    Einmal je Programmlauf ermittelt. Kein Versionsvergleich: Ob
    2026-07 oder 2026-10 die erste Version mit dem neuen Feld war,
    muss so niemand wissen.
    """
    global _neu
    if _neu is not None and not erneut:
        return _neu
    if shopify_http is None:
        _neu = False
        return _neu
    antwort = shopify_http.execute(_PROBE)
    fehler = str(antwort.get("_error", ""))
    # Kennt die Version das Feld nicht, meldet Shopify genau das.
    _neu = not ("barcodes" in fehler.lower()
                and ("doesn't exist" in fehler.lower()
                     or "cannot query field" in fehler.lower()))
    if fehler and _neu:
        # Anderer Fehler (Zugriffsrechte, Drosselung) — nichts gelernt,
        # also nicht festschreiben.
        _neu = None
        return False
    return _neu


def _lesefeld() -> str:
    return (f"barcodes(first: {ANZAHL}) {{ nodes {{ value type }} }}"
            if neue_api() else "barcode")


class _Feld:
    """Setzt sich erst beim Einsetzen in die Abfrage zum passenden Text um."""

    def __str__(self):
        return _lesefeld()

    def __repr__(self):
        return _lesefeld()


LESEN = _Feld()


def lies(knoten) -> str:
    """Erster Barcode einer Variante — aus alter wie neuer Antwortform."""
    if not isinstance(knoten, dict):
        return ""
    alt = knoten.get("barcode")
    if isinstance(alt, str):
        return alt.strip()
    block = knoten.get("barcodes")
    if isinstance(block, dict):
        eintraege = block.get("nodes")
        if eintraege is None:
            eintraege = [k.get("node", {}) for k in (block.get("edges") or [])]
        for e in eintraege or []:
            wert = str((e or {}).get("value") or "").strip()
            if wert:
                return wert
    return ""


def alle(knoten):
    """Alle Barcodes als [(wert, typ)] — neu können es bis zu 20 sein."""
    if not isinstance(knoten, dict):
        return []
    alt = knoten.get("barcode")
    if isinstance(alt, str):
        return [(alt.strip(), None)] if alt.strip() else []
    block = knoten.get("barcodes") or {}
    eintraege = block.get("nodes")
    if eintraege is None:
        eintraege = [k.get("node", {}) for k in (block.get("edges") or [])]
    ergebnis = []
    for e in eintraege or []:
        wert = str((e or {}).get("value") or "").strip()
        if wert:
            ergebnis.append((wert, (e or {}).get("type")))
    return ergebnis


def typ_fuer(wert: str):
    """Leitet den Barcode-Typ aus dem Wert ab. None, wenn unklar.

    978/979 am Anfang einer 13-stelligen Zahl ist eine ISBN — das ist
    bei den Buchverlagen der Unterschied zwischen „irgendeine Nummer"
    und „nachweislich eine ISBN".
    """
    z = re.sub(r"[^0-9Xx]", "", str(wert or "")).upper()
    if len(z) == 13 and z.isdigit():
        return "ISBN" if z[:3] in ("978", "979") else "EAN"
    if len(z) == 12 and z.isdigit():
        return "UPC"
    if len(z) == 8 and z.isdigit():
        return "EAN"
    if len(z) == 10 and re.fullmatch(r"\d{9}[\dX]", z):
        return "ISBN"
    return None


def schreiben(wert: str, typ: str = "") -> dict:
    """Eingabefeld für ProductVariantsBulkInput, passend zur Version.

    Alt:  {"barcode": "4013594123458"}
    Neu:  {"barcodes": [{"value": "4013594123458", "type": "EAN"}]}

    Leerer Wert heißt löschen: alt ein leerer String, neu eine leere
    Liste. Beides entfernt den Barcode, aber auf verschiedene Weise —
    genau dafür gibt es diese Funktion.
    """
    wert = str(wert or "").strip()
    if not neue_api():
        return {"barcode": wert}
    if not wert:
        return {"barcodes": []}
    eintrag = {"value": wert}
    gewaehlt = typ or typ_fuer(wert)
    if gewaehlt:
        eintrag["type"] = gewaehlt
    return {"barcodes": [eintrag]}


def rueckgabefeld() -> str:
    """Für `productVariants { … }` in der Antwort einer Mutation."""
    return _lesefeld()

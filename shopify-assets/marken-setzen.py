"""
marken-setzen.py — Herstellerfeld in Shopify vereinheitlichen
==============================================================

Schreibt die bestätigten Markenkorrekturen in den Katalog. Anders als
bildluecken-aufarbeiten.py betrifft das ALLE aktiven Produkte, nicht nur
die ohne Bild — Markenfehler stecken auch in Produkten mit Bild.

BESTÄTIGTE REGELN
-----------------
  K:S ME, kisme            -> KISME
  zwergenladen-fr          -> Zwergenladen
  Stockmar / Lyra          -> Lyra (Ferby-Stifte) bzw. Stockmar
  Zwergenladen + Etui-Ware -> Sonnenleder
  Zwergenladen + "Kraul" im Titel -> Kraul
  Zwergenladen + "goki" im Titel  -> Goki

Warum das zählt: `brand` ist im Merchant Center ein Pflichtattribut.
Uneinheitliche oder falsche Marken kosten Sichtbarkeit in Shopping —
Sonnenleder-Lederwaren unter der Marke "Zwergenladen" findet niemand.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 marken-setzen.py            # zeigt nur an, ändert nichts
    python3 marken-setzen.py --live     # schreibt

Der Probelauf ist die Vorgabe. Erst prüfen, dann --live.
"""

import re
import sys
import time

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

# ──────────────────────────────────────────
# Regeln — identisch mit bildluecken-aufarbeiten.py
# ──────────────────────────────────────────
MARKEN_NORM = {
    "k:s me": "KISME",
    "kisme": "KISME",
    "zwergenladen-fr": "Zwergenladen",
}

LYRA_MUSTER = re.compile(r"\blyra\b|\bferby\b", re.I)

EIGENMARKE = {"zwergenladen", "zwergenladen-fr"}
SONNENLEDER_MUSTER = re.compile(
    r"\b(storm|simmel|handke|b[oö]ll?|bert|wienfluss+|mozart)\b"
    r"|schreibetui|stecketui|stiftemäppchen|geldbörse|schlüsseletui", re.I)
IM_TITEL = ("kraul", "goki", "ostheimer", "grimms", "nanchen")

# Lieferant steht weder im Hersteller- noch im Titelfeld — namentlich zuordnen.
# Holzkiste-Sortiment, ausgelaufen (Stand 09/2026).
NACH_TITEL = {
    "bogen mit loch": "Holzkiste",
    "pfeile 3er set": "Holzkiste",
    "köcher": "Holzkiste",
    "steinschleuder": "Holzkiste",
}


def marke_normalisiert(vendor, titel):
    v = (vendor or "").strip()
    s = v.lower()
    t = (titel or "").strip()

    if s == "stockmar / lyra":
        return "Lyra" if LYRA_MUSTER.search(t) else "Stockmar"

    if s in EIGENMARKE:
        if SONNENLEDER_MUSTER.search(t):
            return "Sonnenleder"
        nach_titel = NACH_TITEL.get(t.lower())
        if nach_titel:
            return nach_titel
        for h in IM_TITEL:
            if re.search(rf"\b{h}\b", t, re.I):
                return "Goki" if h == "goki" else h.capitalize()
        return "Zwergenladen"

    return MARKEN_NORM.get(s, v)


PRODUKTE_PRO_SEITE = 50
PAUSE = 0.3

ABFRAGE = """
query($cursor: String, $n: Int!) {
  products(first: $n, after: $cursor, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    edges { node { id title vendor } }
  }
}
"""

SCHREIBEN = """
mutation($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id vendor }
    userErrors { field message }
  }
}
"""


def seite_holen(cursor):
    for versuch in range(5):
        a = shopify_http.execute(ABFRAGE, {"cursor": cursor, "n": PRODUKTE_PRO_SEITE})
        f = a.get("_error", "")
        if not f:
            return a, ""
        if "THROTTLED" in f.upper() and versuch < 4:
            time.sleep(2 ** versuch)
            continue
        return {}, f
    return {}, "dauerhaft gedrosselt"


def main():
    live = "--live" in sys.argv
    if not live:
        print("PROBELAUF — es wird nichts geändert.")
        print("Zum Schreiben:  python3 marken-setzen.py --live\n")

    aenderungen = []
    gesamt = 0
    cursor = None

    print("Lese Katalog …")
    while True:
        antwort, fehler = seite_holen(cursor)
        if fehler:
            print(f"Abbruch: {fehler}")
            if not gesamt:
                return
            break
        block = antwort.get("products", {})
        for kante in block.get("edges", []):
            p = kante["node"]
            gesamt += 1
            alt = (p.get("vendor") or "").strip()
            neu = marke_normalisiert(alt, p.get("title"))
            if neu != alt:
                aenderungen.append((p["id"], p.get("title", ""), alt, neu))
        info = block.get("pageInfo", {})
        if not info.get("hasNextPage"):
            break
        cursor = info.get("endCursor")
        time.sleep(PAUSE)

    print(f"{gesamt} Produkte geprüft, {len(aenderungen)} zu ändern\n")
    if not aenderungen:
        print("Nichts zu tun.")
        return

    # Übersicht nach Zielmarke
    from collections import Counter
    zaehler = Counter((alt, neu) for _, _, alt, neu in aenderungen)
    print(f"{'bisher':<24} {'neu':<18} Anzahl")
    print("─" * 52)
    for (alt, neu), n in zaehler.most_common():
        print(f"{alt[:24]:<24} {neu[:18]:<18} {n:>5}")

    print(f"\nBeispiele:")
    for _, titel, alt, neu in aenderungen[:12]:
        print(f"  {titel[:44]:<44} {alt[:16]:<16} → {neu}")
    if len(aenderungen) > 12:
        print(f"  … und {len(aenderungen)-12} weitere")

    if not live:
        print(f"\n{len(aenderungen)} Änderungen bereit. Mit --live ausführen.")
        return

    antwort = input(f"\n{len(aenderungen)} Produkte ändern? (ja/NEIN): ").strip()
    if antwort.lower() != "ja":
        print("Abgebrochen.")
        return

    ok = fehlgeschlagen = 0
    for i, (pid, titel, alt, neu) in enumerate(aenderungen, 1):
        e = shopify_http.execute(SCHREIBEN, {"input": {"id": pid, "vendor": neu}})
        fehler = e.get("_error") or [
            u.get("message") for u in (e.get("productUpdate", {}).get("userErrors") or [])]
        if fehler and fehler != []:
            fehlgeschlagen += 1
            print(f"  ✗ {titel[:40]}: {fehler}")
        else:
            ok += 1
        if i % 25 == 0:
            print(f"  … {i}/{len(aenderungen)}")
        time.sleep(0.25)

    print(f"\nFertig: {ok} geändert, {fehlgeschlagen} fehlgeschlagen")


if __name__ == "__main__":
    main()

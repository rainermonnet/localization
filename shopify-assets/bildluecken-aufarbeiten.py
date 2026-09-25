"""
bildluecken-aufarbeiten.py — Bildlücken nach Relevanz sortieren
================================================================

Erweiterung von bestand-und-bilder-pruefen.py. Zählt nicht mehr alles,
was „aktiv" heißt, sondern nur das, was online tatsächlich verkauft wird —
und gruppiert den Rest nach Lieferant.

WAS SICH GEGENÜBER DER ERSTEN FASSUNG ÄNDERT
--------------------------------------------
Die erste Fassung prüfte `status:active`. Das umfasst auch Produkte, die
im Shopify-Katalog stehen, aber in keinem Vertriebskanal veröffentlicht
sind — etwa das Buchsortiment, das nur im Laden verkauft wird. Für diese
Produkte ist ein fehlendes Bild kein Mangel.

Diese Fassung prüft zusätzlich die Veröffentlichung:
  - onlineStoreUrl gesetzt  -> im Onlineshop sichtbar
  - Publikation "Google"    -> im Shopping-Feed

Nur wer im Onlineshop steht, braucht ein Bild. Nur wer zusätzlich im
Google-Kanal steht, kostet ohne Bild Werbereichweite.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    curl -fsSL -o bildluecken-aufarbeiten.py "https://raw.githubusercontent.com/rainermonnet/localization/claude/shopify-opti-assets-miijc7/shopify-assets/bildluecken-aufarbeiten.py"
    python3 bildluecken-aufarbeiten.py

Nur Lesezugriff — es wird nichts geändert.
"""

import csv
import os
import re
import sys
import time
from collections import defaultdict

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden.\n"
             "Das Skript muss im App-Ordner liegen:\n"
             '  cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"')

# ──────────────────────────────────────────
# Was nicht gezählt wird
# ──────────────────────────────────────────
# Buchverlage: Sortiment wird stationär verkauft, braucht keine Bilder.
# Aurich: Lieferant insolvent, Nachbeschaffung zwecklos.
AUSGESCHLOSSEN = {
    "thienemann", "geistesleben", "urachhaus", "oettinger", "raffael verlag",
    "aurich",
}

# Lieferanten, deren Bildmaterial bereits vorliegt
MEDIEN_VORHANDEN = {"goki", "kraul"}

# ──────────────────────────────────────────
# Markennamen vereinheitlichen
# ──────────────────────────────────────────
# Nur Vorschlag — das Skript schreibt nichts in Shopify zurück.
MARKEN_NORM = {
    "k:s me": "KISME",
    "kisme": "KISME",
    "zwergenladen-fr": "Zwergenladen",
    "stockmar": "Stockmar",
}

# "Stockmar / Lyra" ist ein Sammelfeld für zwei Marken. Aufteilen nach
# Titel: Ferby-Stifte sind Lyra, alles andere Stockmar.
LYRA_MUSTER = re.compile(r"\blyra\b|\bferby\b", re.I)

# Unter "Zwergenladen" steht Fremdware, die falsch zugeordnet wurde.
# Sonnenleder benennt seine Lederwaren nach Schriftstellern — dieses
# Muster erkennt sie zuverlässig, weil es nur innerhalb der eigenen
# Marke angewandt wird.
EIGENMARKE = {"zwergenladen", "zwergenladen-fr"}
SONNENLEDER_MUSTER = re.compile(
    r"\b(storm|simmel|handke|b[oö]ll?|bert|wienfluss+|mozart)\b"
    r"|schreibetui|stecketui|stiftemäppchen|geldbörse|schlüsseletui", re.I)
# Hersteller, die im Titel statt im Herstellerfeld stehen
IM_TITEL = ("kraul", "goki", "ostheimer", "grimms", "nanchen")

PRODUKTE_PRO_SEITE = 25
VARIANTEN_PRO_PRODUKT = 30
PAUSE = 0.4

QUERY = """
query($cursor: String, $n: Int!, $v: Int!) {
  products(first: $n, after: $cursor, query: "status:active", sortKey: CREATED_AT, reverse: true) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        title
        vendor
        handle
        createdAt
        onlineStoreUrl
        featuredImage { url }
        resourcePublicationsV2(first: 10) {
          edges { node { isPublished publication { name } } }
        }
        variants(first: $v) {
          edges { node { id sku barcode inventoryQuantity } }
        }
      }
    }
  }
}
"""


def kurz_id(gid):
    return gid.rsplit("/", 1)[-1] if gid else ""


def marke_normalisiert(vendor, titel):
    """Vereinheitlichter Markenname — reiner Vorschlag."""
    v = (vendor or "").strip()
    schluessel = v.lower()
    t = titel or ""

    if schluessel == "stockmar / lyra":
        return "Lyra" if LYRA_MUSTER.search(t) else "Stockmar"

    # Innerhalb der Eigenmarke steckt Fremdware
    if schluessel in EIGENMARKE:
        if SONNENLEDER_MUSTER.search(t):
            return "Sonnenleder"
        for hersteller in IM_TITEL:
            if re.search(rf"\b{hersteller}\b", t, re.I):
                return hersteller.capitalize() if hersteller != "goki" else "Goki"
        return "Zwergenladen"

    return MARKEN_NORM.get(schluessel, v)


def kanaele(knoten):
    """Namen der Kanäle, in denen das Produkt veröffentlicht ist."""
    raus = []
    for k in knoten.get("resourcePublicationsV2", {}).get("edges", []):
        n = k.get("node") or {}
        if n.get("isPublished"):
            name = (n.get("publication") or {}).get("name") or ""
            if name:
                raus.append(name)
    return raus


def seite_holen(cursor):
    for versuch in range(5):
        antwort = shopify_http.execute(QUERY, {
            "cursor": cursor, "n": PRODUKTE_PRO_SEITE, "v": VARIANTEN_PRO_PRODUKT})
        fehler = antwort.get("_error", "")
        if not fehler:
            return antwort, ""
        if "THROTTLED" in fehler.upper() and versuch < 4:
            warte = 2 ** versuch
            print(f"    gedrosselt, warte {warte}s …")
            time.sleep(warte)
            continue
        return {}, fehler
    return {}, "dauerhaft gedrosselt"


def dateiname(marke):
    sauber = re.sub(r"[^\wäöüÄÖÜß-]+", "-", marke).strip("-").lower()
    return f"anfrage-{sauber or 'ohne-marke'}.csv"


def main():
    print("Lese aktive Produkte und ihre Veröffentlichung …\n")

    relevant = []          # ohne Bild, im Onlineshop
    nur_intern = 0         # ohne Bild, nirgends veröffentlicht
    ausgeschlossen = 0     # Verlage, Aurich
    mit_bild = 0
    gesamt = 0
    marken_roh = defaultdict(int)     # Originalschreibweise -> Anzahl
    cursor, seite = None, 0

    while True:
        seite += 1
        antwort, fehler = seite_holen(cursor)
        if fehler:
            print(f"\nAbbruch auf Seite {seite}:\n{fehler}")
            if not gesamt:
                return
            break

        block = antwort.get("products", {})
        kanten = block.get("edges", [])
        if not kanten:
            break

        for kante in kanten:
            p = kante["node"]
            gesamt += 1

            if p.get("featuredImage"):
                mit_bild += 1
                continue

            vendor = (p.get("vendor") or "").strip()
            titel = p.get("title") or ""

            if vendor.lower() in AUSGESCHLOSSEN:
                ausgeschlossen += 1
                continue

            im_shop = bool(p.get("onlineStoreUrl"))
            kanal_namen = kanaele(p)
            im_google = any("google" in k.lower() for k in kanal_namen)

            if not im_shop:
                nur_intern += 1
                continue

            marken_roh[vendor] += 1
            marke = marke_normalisiert(vendor, titel)

            varianten = [v["node"] for v in p.get("variants", {}).get("edges", [])]
            bestand = sum((v.get("inventoryQuantity") or 0) for v in varianten)
            erste = varianten[0] if varianten else {}

            relevant.append({
                "Marke": marke,
                "Marke laut Shopify": vendor,
                "Produkt-ID": kurz_id(p["id"]),
                "Titel": titel,
                "SKU": erste.get("sku") or "",
                "Barcode": erste.get("barcode") or "",
                "Bestand": bestand,
                "Angelegt": (p.get("createdAt") or "")[:10],
                "Im Google-Kanal": "ja" if im_google else "nein",
                "Medien vorhanden": "ja" if marke.lower() in MEDIEN_VORHANDEN else "",
                "Admin-Link": f"https://admin.shopify.com/store/zwergenladen-fr"
                              f"/products/{kurz_id(p['id'])}",
            })

        print(f"  Seite {seite}: {gesamt} gelesen · "
              f"{len(relevant)} relevant · {nur_intern} nicht online · "
              f"{ausgeschlossen} ausgeschlossen")

        info = block.get("pageInfo", {})
        if not info.get("hasNextPage"):
            break
        cursor = info.get("endCursor")
        time.sleep(PAUSE)

    # ── Gesamtliste ───────────────────────
    relevant.sort(key=lambda z: (z["Marke"].lower(), z["Titel"]))
    if relevant:
        with open("bildluecken.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(relevant[0].keys()), delimiter=";")
            w.writeheader()
            w.writerows(relevant)

    # ── Anfrageliste je Marke ─────────────
    nach_marke = defaultdict(list)
    for z in relevant:
        nach_marke[z["Marke"]].append(z)

    erzeugt = []
    for marke, zeilen in nach_marke.items():
        if marke.lower() in MEDIEN_VORHANDEN or len(zeilen) < 3:
            continue
        name = dateiname(marke)
        with open(name, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Artikelnummer (SKU)", "EAN", "Produktbezeichnung", "Bestand"])
            for z in zeilen:
                w.writerow([z["SKU"], z["Barcode"], z["Titel"], z["Bestand"]])
        erzeugt.append((marke, len(zeilen), name))
    erzeugt.sort(key=lambda t: -t[1])

    # ── Markenbereinigung ─────────────────
    # Je Produkt auswerten, nicht je Lieferant: "Stockmar / Lyra" teilt sich
    # auf zwei Zielmarken auf, ein Vorschlag pro Lieferant wäre falsch.
    paare = defaultdict(int)
    for z in relevant:
        if z["Marke"] != z["Marke laut Shopify"]:
            paare[(z["Marke laut Shopify"], z["Marke"])] += 1

    korrekturen = [{"Bisher": alt, "Vorschlag": neu, "Produkte": n}
                   for (alt, neu), n in sorted(paare.items(), key=lambda t: -t[1])]
    if korrekturen:
        with open("marken-bereinigung.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["Bisher", "Vorschlag", "Produkte"],
                               delimiter=";")
            w.writeheader()
            w.writerows(korrekturen)

    # ── Bericht ───────────────────────────
    print("\n" + "=" * 68)
    print(f"{gesamt} aktive Produkte · {mit_bild} mit Bild")
    print("=" * 68)
    print(f"  ohne Bild, im Onlineshop      {len(relevant):>5}   ← zu beschaffen")
    print(f"  ohne Bild, nicht online       {nur_intern:>5}   (kein Mangel)")
    print(f"  ausgeschlossen (Verlage/Aurich){ausgeschlossen:>4}")

    im_google = sum(1 for z in relevant if z["Im Google-Kanal"] == "ja")
    print(f"\n  davon im Google-Kanal          {im_google:>5}   ← kostet Werbereichweite")

    print(f"\nANFRAGELISTEN ({len(erzeugt)} Lieferanten)")
    for marke, n, name in erzeugt:
        print(f"  {n:>4}  {marke:<22} {name}")

    rest = sum(len(v) for k, v in nach_marke.items()
               if k.lower() in MEDIEN_VORHANDEN or len(v) < 3)
    if rest:
        print(f"  {rest:>4}  übrige (Medien vorhanden oder unter 3 Stück)")

    if korrekturen:
        print("\nMARKENNAMEN VEREINHEITLICHEN (Vorschlag, nichts geändert)")
        for k in korrekturen:
            print(f"  {k['Produkte']:>4}  {k['Bisher']:<24} → {k['Vorschlag']}")

    print("\nGeschrieben:")
    for n in ["bildluecken.csv", "marken-bereinigung.csv"] + [e[2] for e in erzeugt]:
        if os.path.exists(n):
            print(f"  {n}")


if __name__ == "__main__":
    main()

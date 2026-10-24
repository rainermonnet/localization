"""
bilder-suchen.py — fehlende Produktbilder auffinden und holen
===============================================================

Schritt 1 von zwei. Dieses Skript findet die Lücken und besorgt, was
sich sicher besorgen lässt. Das Hochladen macht danach
`bilder-hochladen.py`.

WAS DIESES SKRIPT NICHT TUT
----------------------------
Es durchsucht nicht selbständig Herstellerseiten. Jeder Hersteller baut
seine Seite anders, und ein Bild, das zum falschen Artikel gehört, fällt
niemandem auf und wandert in den Google-Feed. Geraten wird deshalb
nicht.

Stattdessen zwei Wege:

  A) ARBEITSLISTE. Für jedes Produkt ohne Bild entsteht eine Zeile mit
     Artikelnummer, EAN und fertigen Suchlinks — Herstellerseite,
     EAN-Suche, Bildersuche. Du öffnest, lädst herunter, legst die
     Datei unter dem vorgegebenen Namen ab. Das ist Handarbeit, aber
     belastbar.

  B) DIREKTER ABRUF, wenn ein Hersteller seine Bilder nach einem festen
     Muster ablegt. Dafür unten MUSTER füllen. goki etwa benennt vieles
     nach der Artikelnummer. Jeder Treffer wird geprüft: echter
     Bildtyp, Mindestgröße, und keine Platzhaltergrafik — wenn
     mehrere Produkte dieselbe Datei liefern, ist es ein „Kein Bild
     vorhanden"-Bild und wird verworfen.

ZU DEN NUTZUNGSRECHTEN
-----------------------
Herstellerbilder sind urheberrechtlich geschützt. Als autorisierter
Händler hast du meist ein Nutzungsrecht — aber „meist" ist keine
Lizenz. Der saubere Weg führt über das Händlerportal oder eine kurze
Anfrage; Vorlagen dafür liegen in `lieferanten-emails.md`.

Ein Bild von der öffentlichen Herstellerseite zu ziehen ist etwas
anderes, als es vom Hersteller bekommen zu haben. Bei den Marken, mit
denen du seit Jahren arbeitest, ist das Risiko gering und die Antwort
auf eine Anfrage fast immer ja. Diese Abwägung triffst du, nicht ich.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"

    python3 bilder-suchen.py                    # Arbeitsliste erstellen
    python3 bilder-suchen.py --marke goki       # nur eine Marke
    python3 bilder-suchen.py --holen            # Muster-Abruf, Probelauf
    python3 bilder-suchen.py --holen --live     # lädt herunter

Die Dateien landen in `bilder-neu/<Marke>/<handle>.jpg`. Der Handle im
Dateinamen sorgt dafür, dass `bilder-hochladen.py` sie eindeutig
zuordnet — kein Raten über Titelwörter.

DANACH
------
    python3 bilder-hochladen.py bilder-neu --live
"""

import csv
import hashlib
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

ZIEL = "bilder-neu"
LISTE = "bilder-fehlen.csv"
MIN_BYTES = 4000          # darunter ist es kein brauchbares Produktbild
ZEIT = 25

# Direktabruf je Marke. {artikel} = SKU, {ean} = Barcode.
# Leer gelassen heißt: diese Marke läuft über die Arbeitsliste.
# Muster erst eintragen, wenn du eine Beispiel-URL im Browser geprüft hast.
MUSTER = {
    # "goki": ["https://www.example.com/media/{artikel}.jpg"],
}

# Wo man bei dieser Marke von Hand sucht
HERSTELLER = {
    "goki":        "https://www.goki.eu/suche?q=",
    "kraul":       "https://www.kraul.de/?s=",
    "ostheimer":   "https://www.ostheimer.de/?s=",
    "henrys":      "https://www.henrys-online.de/search?q=",
    "grapat":      "https://grapat.es/?s=",
    "nanchen":     "https://www.nanchen.com/?s=",
    "stockmar":    "https://www.stockmar.de/?s=",
    "käthe kruse": "https://www.kaethe-kruse.de/?s=",
    "grimms":      "https://www.grimms.eu/suche?q=",
    "sonett":      "https://www.sonett.eu/?s=",
}

PRODUKTE = """
query($cursor: String, $suche: String!) {
  products(first: 50, after: $cursor, query: $suche) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id handle title vendor totalInventory
        media(first: 1) { edges { node { id } } }
        resourcePublicationsV2(first: 8) {
          edges { node { isPublished publication { name } } }
        }
        variants(first: 10) { edges { node { sku barcode } } }
      }
    }
  }
}
"""


def kurz(gid):
    return gid.rsplit("/", 1)[-1] if gid else ""


def sauber(text):
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", str(text or "")).strip("-")[:80]


def produkte_ohne_bild(marke):
    suche = "status:active"
    if marke:
        suche += f' AND vendor:"{marke}"'
    liste, cursor = [], None
    while True:
        for versuch in range(5):
            a = shopify_http.execute(PRODUKTE, {"cursor": cursor, "suche": suche})
            f = str(a.get("_error", ""))
            if not f:
                break
            if "THROTTLED" in f.upper() and versuch < 4:
                time.sleep(2 ** versuch)
                continue
            sys.exit(f"Produkte nicht lesbar: {f}")
        block = a.get("products", {})
        for k in block.get("edges", []):
            n = k["node"]
            if (n.get("media") or {}).get("edges"):
                continue
            kanaele = [(e["node"]["publication"] or {}).get("name", "")
                       for e in n.get("resourcePublicationsV2", {}).get("edges", [])
                       if e["node"].get("isPublished")]
            varianten = [v["node"] for v in n.get("variants", {}).get("edges", [])]
            liste.append({
                "id": kurz(n["id"]), "handle": n["handle"], "titel": n["title"],
                "marke": (n.get("vendor") or "").strip(),
                "bestand": n.get("totalInventory") or 0,
                "sku": next((str(v.get("sku") or "").strip() for v in varianten
                             if v.get("sku")), ""),
                "ean": next((str(v.get("barcode") or "").strip() for v in varianten
                             if v.get("barcode")), ""),
                "shop": any("online" in k.lower() for k in kanaele),
                "google": any("google" in k.lower() for k in kanaele),
            })
        if not block.get("pageInfo", {}).get("hasNextPage"):
            return liste
        cursor = block["pageInfo"]["endCursor"]
        time.sleep(0.2)


def suchlinks(p):
    begriff = p["sku"] or p["titel"]
    basis = HERSTELLER.get(p["marke"].lower(), "")
    hersteller = basis + urllib.parse.quote(begriff) if basis else ""
    bilder = ("https://www.google.com/search?tbm=isch&q="
              + urllib.parse.quote(f'{p["marke"]} {begriff}'))
    ean = ("https://www.google.com/search?q=" + urllib.parse.quote(p["ean"])
           if p["ean"] else "")
    return hersteller, bilder, ean


def ist_bild(daten):
    return (daten[:3] == b"\xff\xd8\xff"                      # JPEG
            or daten[:8] == b"\x89PNG\r\n\x1a\n"              # PNG
            or daten[:6] in (b"GIF87a", b"GIF89a")
            or (daten[:4] == b"RIFF" and daten[8:12] == b"WEBP"))


def laden(url):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh) Zwergenladen-Bildabruf",
            "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"})
        with urllib.request.urlopen(req, timeout=ZEIT) as r:
            typ = (r.headers.get("Content-Type") or "").lower()
            daten = r.read(12 * 1024 * 1024)
    except (urllib.error.URLError, OSError) as e:
        return None, str(e)
    if "image" not in typ and not ist_bild(daten):
        return None, f"kein Bild ({typ or 'ohne Typ'})"
    if not ist_bild(daten):
        return None, "Dateikopf ist kein Bildformat"
    if len(daten) < MIN_BYTES:
        return None, f"zu klein ({len(daten)} Bytes)"
    return daten, ""


def endung(daten):
    if daten[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if daten[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if daten[:4] == b"RIFF":
        return ".webp"
    return ".gif"


def main():
    live = "--live" in sys.argv
    holen = "--holen" in sys.argv
    marke = ""
    if "--marke" in sys.argv:
        k = sys.argv.index("--marke")
        if k + 1 < len(sys.argv):
            marke = sys.argv[k + 1]

    print("Lese Katalog …")
    fehlend = produkte_ohne_bild(marke)
    if not fehlend:
        print("Kein aktives Produkt ohne Bild. Nichts zu tun.")
        return

    im_shop = [p for p in fehlend if p["shop"]]
    mit_bestand = [p for p in fehlend if (p["bestand"] or 0) > 0]
    print(f"\n{len(fehlend)} aktive Produkte ohne Bild")
    print(f"  {len(im_shop)} davon im Onlineshop sichtbar")
    print(f"  {len(mit_bestand)} davon mit Bestand\n")

    nach_marke = Counter(p["marke"] or "—" for p in fehlend)
    print("NACH MARKE")
    for m, n in nach_marke.most_common(15):
        sichtbar = sum(1 for p in fehlend if (p["marke"] or "—") == m and p["shop"])
        muster = "Muster hinterlegt" if m.lower() in MUSTER else ""
        print(f"  {n:>4}  {m[:24]:<24} davon {sichtbar:>3} im Shop   {muster}")
    if len(nach_marke) > 15:
        print(f"  … und {len(nach_marke)-15} weitere Marken")

    ohne_sku = [p for p in fehlend if not p["sku"] and not p["ean"]]
    if ohne_sku:
        print(f"\n{len(ohne_sku)} haben weder Artikelnummer noch EAN — bei denen")
        print("bleibt nur die Suche über den Titel, entsprechend unsicher.")

    with open(LISTE, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Marke", "Titel", "SKU", "EAN", "Bestand", "Im Shop",
                    "Dateiname ablegen als", "Hersteller-Suche",
                    "Bildersuche", "EAN-Suche", "Produkt-ID", "Handle"])
        for p in sorted(fehlend, key=lambda x: (x["marke"], x["titel"])):
            h, b, e = suchlinks(p)
            w.writerow([p["marke"], p["titel"], p["sku"], p["ean"], p["bestand"],
                        "ja" if p["shop"] else "nein",
                        f"{ZIEL}/{sauber(p['marke']) or 'ohne-marke'}/{p['handle']}.jpg",
                        h, b, e, p["id"], p["handle"]])
    print(f"\nGeschrieben: {LISTE}")
    print("Spalte „Dateiname ablegen als“ beachten — der Handle im Namen")
    print("sorgt für die eindeutige Zuordnung beim Hochladen.")

    if not holen:
        print("\nDirektabruf für Marken mit festem Bildmuster:")
        print("  python3 bilder-suchen.py --holen")
        if not MUSTER:
            print("  (noch kein Muster eingetragen — siehe MUSTER im Skript)")
        return

    if not MUSTER:
        print("\nKein Muster in MUSTER eingetragen. Nichts abzurufen.")
        print("Trag erst eine geprüfte Beispiel-URL ein, dann erneut starten.")
        return

    kandidaten = [p for p in fehlend if p["marke"].lower() in MUSTER
                  and (p["sku"] or p["ean"])]
    print(f"\n{len(kandidaten)} Produkte mit hinterlegtem Muster")
    if not live:
        print("PROBELAUF — es wird nichts heruntergeladen.")
        for p in kandidaten[:10]:
            for m in MUSTER[p["marke"].lower()]:
                print("   " + m.format(artikel=p["sku"], ean=p["ean"]))
        print(f"\nMit --live herunterladen.")
        return

    nach_hash = defaultdict(list)
    ok = fehler = 0
    for i, p in enumerate(kandidaten, 1):
        daten, grund = None, "kein Muster griff"
        for m in MUSTER[p["marke"].lower()]:
            daten, grund = laden(m.format(artikel=p["sku"], ean=p["ean"]))
            if daten:
                break
        if not daten:
            fehler += 1
            if fehler <= 15:
                print(f"  ✗ {p['titel'][:40]}: {grund}")
            continue
        ordner = os.path.join(ZIEL, sauber(p["marke"]) or "ohne-marke")
        os.makedirs(ordner, exist_ok=True)
        pfad = os.path.join(ordner, p["handle"] + endung(daten))
        with open(pfad, "wb") as f:
            f.write(daten)
        nach_hash[hashlib.sha256(daten).hexdigest()].append(pfad)
        ok += 1
        if i % 25 == 0:
            print(f"  … {i}/{len(kandidaten)}")
        time.sleep(0.5)

    print(f"\n{ok} geladen, {fehler} ohne Treffer")

    # Platzhalter erkennen: dieselbe Datei für mehrere Produkte
    doppelt = {h: v for h, v in nach_hash.items() if len(v) > 1}
    entfernt = 0
    for h, pfade in doppelt.items():
        print(f"\n{len(pfade)} Produkte haben dieselbe Bilddatei bekommen —")
        print("das ist eine Platzhaltergrafik, keine Produktaufnahme:")
        for p in pfade[:5]:
            print(f"    {p}")
        for p in pfade:
            try:
                os.remove(p)
                entfernt += 1
            except OSError:
                pass
    if entfernt:
        print(f"\n{entfernt} Platzhalter wieder gelöscht.")

    print(f"\nEchte Bilder in {ZIEL}/ — vor dem Hochladen ansehen.")
    print("Dann:  python3 bilder-hochladen.py bilder-neu")


if __name__ == "__main__":
    main()

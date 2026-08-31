#!/usr/bin/env python3
"""Erzeugt die Druck-PDFs aus den HTML-Vorlagen in diesem Ordner.

    pip install pillow playwright
    python3 druck/bauen.py

Jede Vorlage traegt ihr Endformat plus 2 mm Beschnitt ringsum im @page-Format.
Chromium setzt den Text als Vektor, die Zwerge liegen als eingebettetes Bild
darin. Farbraum ist RGB — die meisten Onlinedruckereien wandeln selbst nach
CMYK; wer ein CMYK-PDF verlangt, bekommt es aus diesen Dateien ueber einen
Konverter.
"""

import base64
import io
import json
import pathlib
import re

from PIL import Image

HIER = pathlib.Path(__file__).resolve().parent
ZWERGE = HIER.parent / "zwerge"
SCHRIFTEN = HIER.parent / "quelle" / "schriften.json"

VORLAGEN = ["postkarte-vorderseite", "postkarte-rueckseite", "visitenkarte",
             "gutschein", "flagge"]


def bild_uri(pfad, hoehe, qualitaet=90):
    bild = Image.open(pfad).convert("RGBA")
    bild = bild.crop(bild.getbbox())
    breite, alt = bild.size
    bild = bild.resize((max(1, round(breite * hoehe / alt)), hoehe), Image.LANCZOS)
    puffer = io.BytesIO()
    bild.save(puffer, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(puffer.getvalue()).decode()


def gemaelde_uri():
    bild = Image.open(ZWERGE / "gemaelde-2012-vorderseite.jpg").convert("RGB")
    puffer = io.BytesIO()
    bild.save(puffer, "JPEG", quality=94, subsampling=0, dpi=(600, 600))
    return "data:image/jpeg;base64," + base64.b64encode(puffer.getvalue()).decode()


def marken():
    import code128

    schriften = json.loads(SCHRIFTEN.read_text())
    werte = {
        "__MULISH__": schriften["Mulish"],
        # Fuer den Druck reichen 900 px Hoehe: bei 30 mm Bildhoehe sind das 760 dpi.
        "__Z2__": bild_uri(ZWERGE / "zwerg-2-blick-nach-oben.png", 900),
        "__Z3__": bild_uri(ZWERGE / "zwerg-3-profil.png", 900),
        "__Z4__": bild_uri(ZWERGE / "zwerg-4-frontal.png", 900),
        # 60 mm Barcodebreite ergibt 0,37 mm Modulbreite — deutlich ueber der
        # Grenze von 0,25 mm, ab der Handscanner unzuverlaessig werden.
        # Das Gemaelde liegt mit 626 dpi vor; bei 138 mm Breite bleiben 690 dpi.
        "__GEMAELDE__": gemaelde_uri(),
        "__QR__": bild_uri(ZWERGE / "qr-zwergenladen.png", 888),
        "__BARCODE__": "data:image/svg+xml;base64,"
        + base64.b64encode(code128.svg("ZWERG5AB30", 60, 16).encode()).decode(),
    }
    return werte


def main():
    werte = marken()
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        seite = browser.new_page()
        for name in VORLAGEN:
            quelle = HIER / f"{name}.html"
            inhalt = quelle.read_text()
            for marke, wert in werte.items():
                inhalt = inhalt.replace(marke, wert)
            offen = set(re.findall(r"__[A-Z][A-Z0-9_]*__", inhalt))
            if offen:
                raise SystemExit(f"{name}: nicht ersetzte Platzhalter {offen}")

            fertig = HIER / f".{name}.fertig.html"
            fertig.write_text(inhalt)
            seite.goto(fertig.as_uri())
            seite.wait_for_timeout(700)
            ziel = HIER / f"{name}.pdf"
            seite.pdf(path=str(ziel), print_background=True, prefer_css_page_size=True)
            fertig.unlink()
            print(f"{ziel.name} — {ziel.stat().st_size / 1024:.0f} KB")
        browser.close()


if __name__ == "__main__":
    main()

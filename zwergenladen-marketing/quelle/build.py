#!/usr/bin/env python3
"""Baut konzept.html aus vorlage.html, den Zwergenbildern und den Schriften.

    pip install pillow
    python3 quelle/build.py

Erzeugt zwergenladen-marketing/konzept.html — eine eigenständige Datei ohne
externe Abhängigkeiten. Schriften und Bilder liegen als data:-URI darin, die
Seite läuft offline und lässt sich im Browser als PDF drucken.

Braucht kein Netz: die Schriften liegen als quelle/schriften.json bei.
"""

import base64
import io
import json
import pathlib
import re

from PIL import Image

HIER = pathlib.Path(__file__).resolve().parent
ZIEL = HIER.parent
ZWERGE = ZIEL / "zwerge"


def als_uri(bild, fmt="WEBP", **opt):
    puffer = io.BytesIO()
    bild.save(puffer, fmt, **opt)
    typ = "webp" if fmt == "WEBP" else fmt.lower()
    return f"data:image/{typ};base64," + base64.b64encode(puffer.getvalue()).decode()


def auf_hoehe(bild, hoehe):
    breite, alt = bild.size
    return bild.resize((max(1, round(breite * hoehe / alt)), hoehe), Image.LANCZOS)


def bilder():
    """Skaliert die Originale auf Bildschirmgröße und kodiert sie."""
    out = {}

    for schluessel, datei in [
        ("z1", "zwerg-1-ruecken.png"),
        ("z2", "zwerg-2-blick-nach-oben.png"),
        ("z3", "zwerg-3-profil.png"),
        ("z4", "zwerg-4-frontal.png"),
    ]:
        bild = Image.open(ZWERGE / datei).convert("RGBA")
        bild = bild.crop(bild.getbbox())  # Transparenzrand weg
        out[schluessel] = als_uri(auf_hoehe(bild, 760), quality=82, method=6)

    postkarte = Image.open(ZWERGE / "postkarte-2023-vorderseite.png").convert("RGB")
    out["pk_front"] = als_uri(auf_hoehe(postkarte, 760), quality=76, method=6)

    advent = Image.open(ZWERGE / "postkarte-advent-2024.png").convert("RGB")
    out["advent"] = als_uri(auf_hoehe(advent, 620), quality=74, method=6)

    stempel = Image.open(ZWERGE / "stempel-strichfassung-2231px.png").convert("RGB")
    out["stempel"] = als_uri(auf_hoehe(stempel, 700), quality=80, method=6)

    # Wand und Boden als echte Pinselstruktur aus der Postkarte schneiden
    breite, hoehe = postkarte.size
    wand = postkarte.crop((0, int(hoehe * .02), breite, int(hoehe * .30)))
    boden = postkarte.crop((0, int(hoehe * .80), breite, int(hoehe * .99)))
    out["tex_wall"] = als_uri(wand.resize((1400, 240), Image.LANCZOS), quality=70, method=6)
    out["tex_floor"] = als_uri(boden.resize((1400, 150), Image.LANCZOS), quality=70, method=6)

    return out


def main():
    seite = (HIER / "vorlage.html").read_text()
    schriften = json.loads((HIER / "schriften.json").read_text())
    bild = bilder()

    seite = seite.replace("__MULISH__", schriften["Mulish"])
    seite = seite.replace("__LITERATA__", schriften["Literata"])
    seite = seite.replace("__CAVEAT_FACE__", (HIER / "caveat.css").read_text())

    # Texturen als Custom Properties, direkt vor die Schriftvariablen
    seite = seite.replace(
        "  --sans:",
        f"  --tw:url('{bild['tex_wall']}');\n  --tf:url('{bild['tex_floor']}');\n  --sans:",
        1,
    )

    for schluessel, marke in [
        ("z1", "__Z1__"), ("z2", "__Z2__"), ("z3", "__Z3__"), ("z4", "__Z4__"),
        ("pk_front", "__PK__"), ("advent", "__ADVENT__"), ("stempel", "__STEMPEL__"),
    ]:
        seite = seite.replace(marke, bild[schluessel])

    # Bewusst nur Marken mit Großbuchstaben: die Unterstrichreihen in den
    # Gutscheintexten sind gewollte Ausfülllinien, keine Platzhalter.
    offen = set(re.findall(r"__[A-Z][A-Z_]*__", seite))
    if offen:
        raise SystemExit(f"Nicht ersetzte Platzhalter: {offen}")

    ausgabe = ZIEL / "konzept.html"
    ausgabe.write_text(seite)
    print(f"{ausgabe.relative_to(ZIEL.parent)} — {len(seite.encode()) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()

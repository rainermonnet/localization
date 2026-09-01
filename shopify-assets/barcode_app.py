"""
barcode_app.py — Barcode-Werkbank für Zwergenladen
===================================================
Erzeugt maßstabstreue EAN-13/EAN-8/UPC-A/Code-128-Symbole als Vektor-SVG.

Start:
    pip install streamlit python-barcode
    streamlit run barcode_app.py

WARUM DIE ALTEN BARCODES NICHT GESCANNT WURDEN
-----------------------------------------------
Ein Scanner misst nicht die Form der Striche, sondern die BREITENVERHÄLTNISSE
zwischen hellen und dunklen Modulen.

Ein EAN-13 besteht aus 95 Modulen Nutzdaten plus Ruhezonen (11 Module links,
7 rechts) = 113 Module zu je 0,330 mm = 37,29 mm Gesamtbreite bei 100 %.

Wird das Symbol als PNG gerendert, muss jede Modulbreite auf ganze Pixel
gerundet werden. Bei 96 dpi ist ein Modul nur 1,25 px breit — die Rundung
verschiebt die Verhältnisse, und die Dekodierung schlägt fehl. Beim
Hochskalieren zum Druck kommt Kantenunschärfe dazu.

Diese Fassung gibt SVG aus: Die Geometrie bleibt bis zur Druckerauflösung
exakt, und alle Maße sind in Millimetern gesetzt statt in Pixeln.

DRUCK
-----
Der Download liefert eine HTML-Datei. In Chrome öffnen → Drucken →
Skalierung 100 %, "An Seite anpassen" AUS. Dieser Weg hat sich bereits
als funktionierend erwiesen.
"""

import re
from io import BytesIO

import streamlit as st
import streamlit.components.v1 as components

try:
    import barcode
    from barcode.writer import SVGWriter
except ImportError:
    st.error("Bibliothek fehlt. Bitte ausführen:  pip install python-barcode")
    st.stop()


# ──────────────────────────────────────────────────────────
# Konstanten
# ──────────────────────────────────────────────────────────
MODULE_MM = 0.33          # Nennmodulbreite bei 100 % Vergrößerung

# Ruhezone in Modulen je Symbolik (python-barcode setzt sie beidseitig,
# darum jeweils der größere der beiden Normwerte)
QUIET_MODULES = {
    "ean13":   11,
    "ean8":     7,
    "upca":     9,
    "code128": 10,
}

# python-barcode-Klassenname → Anzeigename
FORMAT_LABEL = {
    "ean13":   "EAN-13",
    "ean8":    "EAN-8",
    "upca":    "UPC-A",
    "code128": "Code 128",
}


# ──────────────────────────────────────────────────────────
# Prüfziffern
# ──────────────────────────────────────────────────────────
def check_digit(body: str, start_weight: int) -> int:
    """
    GS1-Prüfziffer.
    EAN-13:  Gewichte ab links 1,3,1,3,…  → start_weight=1
    EAN-8 / UPC-A: Gewichte ab links 3,1,3,1,… → start_weight=3
    """
    total = 0
    for i, ch in enumerate(body):
        weight = start_weight if i % 2 == 0 else (3 if start_weight == 1 else 1)
        total += int(ch) * weight
    return (10 - (total % 10)) % 10


def detect_format(raw: str) -> str:
    """Symbolik anhand der Länge raten."""
    if re.fullmatch(r"\d{12,13}", raw):
        return "ean13"
    if re.fullmatch(r"\d{7,8}", raw):
        return "ean8"
    return "code128"


def normalise(raw: str, forced: str):
    """
    Prüft und vervollständigt einen Code.
    Rückgabe: (wert, symbolik, hinweis) oder (None, None, fehlermeldung)
    """
    fmt = detect_format(raw) if forced == "auto" else forced

    specs = {
        "ean13": (12, 13, 1, "EAN-13 braucht 12 oder 13 Ziffern"),
        "ean8":  (7,  8,  3, "EAN-8 braucht 7 oder 8 Ziffern"),
        "upca":  (11, 12, 3, "UPC-A braucht 11 oder 12 Ziffern"),
    }

    if fmt in specs:
        body_len, full_len, weight, msg = specs[fmt]

        if not re.fullmatch(rf"\d{{{body_len},{full_len}}}", raw):
            return None, None, msg

        if len(raw) == body_len:
            d = check_digit(raw, weight)
            return raw + str(d), fmt, f"Prüfziffer {d} ergänzt"

        expected = check_digit(raw[:body_len], weight)
        if expected != int(raw[body_len]):
            return None, None, f"Prüfziffer falsch — erwartet {expected}"
        return raw, fmt, None

    # Code 128
    if not raw:
        return None, None, "leer"
    return raw, "code128", None


# ──────────────────────────────────────────────────────────
# SVG-Erzeugung
# ──────────────────────────────────────────────────────────
def make_svg(value: str, fmt: str, module_mm: float,
             bar_height_mm: float, show_text: bool) -> str:
    """
    Erzeugt ein einzelnes Barcode-SVG mit exakten Millimetermaßen.
    Wirft nichts — Fehler werden vom Aufrufer über die Exception gefangen.
    """
    quiet_mm = QUIET_MODULES.get(fmt, 10) * module_mm

    cls = barcode.get_barcode_class(fmt)
    obj = cls(value, writer=SVGWriter())

    buf = BytesIO()
    obj.write(buf, options={
        "module_width":  module_mm,
        "module_height": bar_height_mm,
        "quiet_zone":    quiet_mm,
        "font_size":     9,
        "text_distance": 1.2,
        "background":    "white",
        "foreground":    "black",
        "write_text":    show_text,
    })

    svg = buf.getvalue().decode("utf-8")

    # XML-Deklaration und DOCTYPE entfernen, damit das SVG in HTML einbettbar ist
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    svg = re.sub(r"<!DOCTYPE[^>]*>", "", svg, flags=re.IGNORECASE)
    return svg.strip()


def parse_lines(text: str):
    """'Code | Beschriftung' je Zeile → Liste von (code, beschriftung)."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            code, caption = line.split("|", 1)
            rows.append((code.strip(), caption.strip()))
        else:
            rows.append((line, ""))
    return rows


def build_sheet_html(cells, columns: int, gap_mm: float) -> str:
    """Setzt die SVGs zu einem druckfertigen Bogen zusammen."""
    figures = []
    for svg, caption in cells:
        cap = f'<figcaption>{caption}</figcaption>' if caption else ""
        figures.append(f'<figure class="cell">{svg}{cap}</figure>')

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Barcode-Bogen — Zwergenladen</title>
<style>
  @page {{ size: A4; margin: 8mm; }}
  body {{
    margin: 0;
    background: #fff;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
  }}
  .sheet {{
    display: grid;
    grid-template-columns: repeat({columns}, 1fr);
    gap: {gap_mm + 2}mm {gap_mm}mm;
    padding: 4mm;
  }}
  .cell {{
    margin: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.4mm;
    break-inside: avoid;
    page-break-inside: avoid;
  }}
  .cell svg {{ display: block; shape-rendering: crispEdges; }}
  figcaption {{
    font-size: 8pt;
    line-height: 1.25;
    text-align: center;
    color: #000;
    overflow-wrap: anywhere;
  }}
  @media screen {{
    body {{ background: #eef1f3; padding: 16px; }}
    .sheet {{
      background: #fff;
      max-width: 210mm;
      margin: 0 auto;
      box-shadow: 0 2px 12px rgba(0,0,0,.12);
      padding: 9mm 7mm;
    }}
  }}
</style>
</head>
<body>
<div class="sheet">
{chr(10).join(figures)}
</div>
</body>
</html>"""


# ──────────────────────────────────────────────────────────
# Oberfläche
# ──────────────────────────────────────────────────────────
st.set_page_config(page_title="Barcode-Werkbank", page_icon="🏷️", layout="wide")

st.title("Barcode-Werkbank")
st.caption(
    "Vektorbasierte Symbole in maßstabstreuer Millimetergröße — "
    "SVG statt PNG, damit die Breitenverhältnisse exakt bleiben."
)

SEED = """4012345000009 | Grimms Regenbogen gross
400827100000  | Ostheimer Dalmatiner 10511
4260000000004 | Grapat Ring natur
ZL-KIS-0042   | KISME Stimmungskette"""

with st.sidebar:
    st.subheader("Codes")
    text = st.text_area(
        "Ein Code pro Zeile — optional `Code | Beschriftung`",
        value=SEED,
        height=200,
    )
    st.caption("Bei 12 Ziffern wird die EAN-13-Prüfziffer automatisch ergänzt.")

    st.subheader("Symbolik")
    forced = st.selectbox(
        "Format",
        options=["auto", "ean13", "ean8", "upca", "code128"],
        format_func=lambda k: "Automatisch nach Länge" if k == "auto" else FORMAT_LABEL[k],
    )

    st.subheader("Maßstab")
    mag = st.slider("Vergrößerungsfaktor %", 80, 200, 100, 5)
    bar_height = st.slider("Strichhöhe mm", 8.0, 30.0, 22.9, 0.5)
    st.caption("GS1 lässt 80–200 % zu. Unter 100 % steigt das Leserisiko spürbar.")

    st.subheader("Bogen")
    columns = st.number_input("Spalten", 1, 8, 4)
    gap_mm = st.number_input("Abstand mm", 0.0, 20.0, 5.0, 1.0)
    show_text = st.checkbox("Klarschriftzeile anzeigen", value=True)
    show_caption = st.checkbox("Produktbeschriftung anzeigen", value=True)

module_mm = MODULE_MM * (mag / 100.0)

# ── Erzeugen ──────────────────────────────────────────────
cells = []
problems = []
notes = []
widest_mm = 0.0

for raw, caption in parse_lines(text):
    value, fmt, msg = normalise(raw, forced)

    if value is None:
        problems.append((raw or "(leer)", msg))
        continue
    if msg:
        notes.append((value, msg))

    try:
        svg = make_svg(
            value, fmt, module_mm, bar_height,
            show_text,
        )
    except Exception as exc:                      # nie abstürzen — melden
        problems.append((raw, f"nicht kodierbar ({type(exc).__name__})"))
        continue

    cells.append((svg, caption if show_caption else ""))

    # Breite = (Nutzmodule + 2 × Ruhezone) × Modulbreite
    if fmt in ("ean13", "upca"):
        total_modules = 95 + 2 * QUIET_MODULES[fmt]
    elif fmt == "ean8":
        total_modules = 67 + 2 * QUIET_MODULES[fmt]
    else:
        total_modules = 0                          # Code 128 variabel
    if total_modules:
        widest_mm = max(widest_mm, total_modules * module_mm)

# ── Kennzahlen ────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Modulbreite", f"{module_mm:.3f} mm".replace(".", ","))
c2.metric("Breite inkl. Ruhezonen",
          f"{widest_mm:.2f} mm".replace(".", ",") if widest_mm else "—")
c3.metric("Symbole", len(cells))
c4.metric("Abgewiesen", len(problems))
st.caption(
    "Die Ruhezone wird beidseitig gleich breit gesetzt, darum liegt EAN-13 bei "
    "100 % auf 38,61 mm statt der Nennbreite 37,29 mm (11 Module links / "
    "7 rechts). Eine breitere Ruhezone verbessert die Lesbarkeit, sie schadet nie."
)

# ── Prüfziffern-Protokoll ─────────────────────────────────
for value, msg in notes:
    st.info(f"`{value}` — {msg}")
for raw, msg in problems:
    st.error(f"`{raw}` — {msg}")
if not notes and not problems and cells:
    st.success("Alle Prüfziffern stimmen.")

# ── Bogen ─────────────────────────────────────────────────
if cells:
    sheet = build_sheet_html(cells, int(columns), float(gap_mm))

    st.download_button(
        "Druckbogen herunterladen (HTML)",
        data=sheet,
        file_name="barcode-bogen.html",
        mime="text/html",
        type="primary",
    )
    st.caption(
        "Datei in Chrome öffnen → Drucken → **Skalierung 100 %**, "
        "„An Seite anpassen“ **aus**. Sonst stimmen die Millimeter nicht mehr."
    )

    st.subheader("Vorschau")
    components.html(sheet, height=760, scrolling=True)
else:
    st.warning("Keine gültigen Codes — bitte links eingeben.")

with st.expander("Warum diese Codes gelesen werden"):
    st.markdown(
        """
Ein Scanner misst keine Formen, sondern die **Breitenverhältnisse** zwischen
hellen und dunklen Modulen. Ein EAN-13 besteht aus 95 Modulen Nutzdaten plus
11 Modulen Ruhezone links und 7 rechts — zusammen 113 Module zu je 0,330 mm,
also 37,29 mm.

Wird das Symbol als **Pixelbild** erzeugt, muss jede Modulbreite auf ganze
Pixel gerundet werden. Bei 96 dpi ist ein Modul nur 1,25 px breit; die Rundung
verschiebt die Verhältnisse, und die Dekodierung schlägt fehl. Beim
Hochskalieren zum Druck kommt Kantenunschärfe hinzu.

Diese Fassung gibt **SVG** aus. Die Geometrie bleibt bis zur Druckerauflösung
exakt, die Breite ist in Millimetern gesetzt statt in Pixeln, die Ruhezonen
sind je Symbolik korrekt bemessen, und die Balken sind reines `#000000` auf
weißem Grund.

**Prüfen ohne Scanner:** Bogen drucken, mit der Kamera-App des iPhones
draufhalten. Zeigt iOS die Ziffernfolge, stimmt die Geometrie.

**Falls der Scanner liest, aber kein Produkt findet:** Dann liegt es nicht am
Barcode, sondern am Abgleich. Der Wert muss in Shopify unter
*Produkt → Variante → Barcode (ISBN, UPC, GTIN)* exakt so eingetragen sein.
        """
    )

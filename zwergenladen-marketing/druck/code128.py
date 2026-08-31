"""Code-128-B-Barcode als SVG-Pfad. Ohne Fremdbibliothek, damit die
Druckdateien auch offline reproduzierbar bleiben."""

PATTERNS = (
    "212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 "
    "221312 231212 112232 122132 122231 113222 123122 123221 223211 221132 "
    "221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 "
    "212123 212321 232121 111323 131123 131321 112313 132113 132311 211313 "
    "231113 231311 112133 112331 132131 113123 113321 133121 313121 211331 "
    "231131 213113 213311 213131 311123 311321 331121 312113 312311 332111 "
    "314111 221411 431111 111224 111422 121124 121421 141122 141221 112214 "
    "112412 122114 122411 142112 142211 241211 221114 413111 241112 134111 "
    "111242 121142 121241 114212 124112 124211 411212 421112 421211 212141 "
    "214121 412121 111143 111341 131141 114113 114311 411113 411311 113141 "
    "114131 311141 411131 211412 211214 211232 2331112"
).split()

START_B, STOP = 104, 106


def widths(text):
    """Balkenbreiten in Modulen für Code 128 B."""
    codes = [START_B] + [ord(c) - 32 for c in text]
    checksum = (START_B + sum((i + 1) * v for i, v in enumerate(codes[1:]))) % 103
    codes += [checksum, STOP]
    out = []
    for c in codes:
        out.extend(int(w) for w in PATTERNS[c])
    return out


def svg(text, width_mm, height_mm, quiet_mm=3.0, farbe="#23211D"):
    """Barcode als eigenständiges SVG. Ruhezone links und rechts inklusive."""
    bars = widths(text)
    module = (width_mm - 2 * quiet_mm) / sum(bars)
    rects, x, dunkel = [], quiet_mm, True
    for b in bars:
        w = b * module
        if dunkel:
            rects.append(f'<rect x="{x:.4f}" y="0" width="{w:.4f}" height="{height_mm}"/>')
        x += w
        dunkel = not dunkel
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm}mm" height="{height_mm}mm" '
        f'viewBox="0 0 {width_mm} {height_mm}" shape-rendering="crispEdges">'
        f'<g fill="{farbe}">{"".join(rects)}</g></svg>'
    )


def modulbreite_mm(text, width_mm, quiet_mm=3.0):
    return (width_mm - 2 * quiet_mm) / sum(widths(text))

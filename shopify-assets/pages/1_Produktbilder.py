"""
Produktbilder — fehlende Bilder sehen, prüfen, hochladen
=========================================================

Zweite Seite der Zwergenladen-Werkbank. Streamlit findet alles in
`pages/` von allein; `barcode_app.py` bleibt unverändert.

Ablage:
    zwergenladen-import-app/
        barcode_app.py
        shopify_http.py
        pages/
            1_Produktbilder.py      ← diese Datei

Starten wie bisher:  streamlit run barcode_app.py
Links in der Seitenleiste erscheint „Produktbilder“.

WARUM EINE SEITE UND KEIN SKRIPT
---------------------------------
Beim Bilderbesorgen ist der riskante Schritt nicht das Hochladen,
sondern die Zuordnung. Ein Bild am falschen Produkt fällt niemandem
auf und wandert in den Google-Feed.

Hier siehst du das Bild neben Titel, Artikelnummer und EAN, bevor
irgendetwas gesendet wird. Damit ist die Fehlerquelle geschlossen,
die jedes automatische Zuordnen offen lässt.

ZU DEN NUTZUNGSRECHTEN
-----------------------
Herstellerbilder sind urheberrechtlich geschützt. Als autorisierter
Händler hast du meist ein Nutzungsrecht — „meist“ ist aber keine
Lizenz. Der saubere Weg führt übers Händlerportal oder eine kurze
Anfrage; Vorlagen in `lieferanten-emails.md`.
"""

import json
import mimetypes
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter

import streamlit as st

try:
    import shopify_http
except ImportError:
    shopify_http = None

# Eigene, bereits vorhandene Bildbeschaffung. Sie kennt die
# Hersteller-Muster (goki über gokitoys.com/media/shop/shop_2020/,
# HENRYS über die Shopware-Suche, Buchverlage über die ISBN) und wird
# hier NICHT nachgebaut — sie bleibt die eine Stelle, an der neue
# Lieferanten dazukommen.
try:
    import bild_quellen
except ImportError:
    bild_quellen = None

st.set_page_config(page_title="Produktbilder", page_icon="🖼️", layout="wide")
st.title("Produktbilder")
st.caption("Fehlende Bilder finden, ansehen und einsetzen — ohne Umweg über Dateien.")

if shopify_http is None:
    st.error("`shopify_http.py` liegt nicht neben der App. Ohne sie kein Zugriff.")
    st.stop()

MIN_BYTES = 4000
ZEIT = 25

HERSTELLER = {
    "goki": "https://www.goki.eu/suche?q=",
    "kraul": "https://www.kraul.de/?s=",
    "ostheimer": "https://www.ostheimer.de/?s=",
    "henrys": "https://www.henrys-online.de/search?q=",
    "grapat": "https://grapat.es/?s=",
    "nanchen": "https://www.nanchen.com/?s=",
    "stockmar": "https://www.stockmar.de/?s=",
    "käthe kruse": "https://www.kaethe-kruse.de/?s=",
    "grimms": "https://www.grimms.eu/suche?q=",
    "sonett": "https://www.sonett.eu/?s=",
}

# Verlage: Cover findet man über Titel und ISBN, nicht über Artikelnummern.
VERLAGE = {"thienemann", "thienemann-esslinger", "urachhaus", "geistesleben",
           "freies geistesleben", "verlag freies geistesleben", "grätz",
           "graetz", "ode desjardin", "mellinger"}

PRODUKTE = """
query($cursor: String) {
  products(first: 50, after: $cursor, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id handle title vendor totalInventory
        media(first: 1) { edges { node { id } } }
        resourcePublicationsV2(first: 8) {
          edges { node { isPublished publication { name } } }
        }
        variants(first: 10) { edges { node { id sku barcode } } }
      }
    }
  }
}
"""

STAGED = """
mutation($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets { url resourceUrl parameters { name value } }
    userErrors { field message }
  }
}
"""

BARCODE = """
mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    userErrors { field message }
  }
}
"""

ANHAENGEN = """
mutation($productId: ID!, $media: [CreateMediaInput!]!) {
  productCreateMedia(productId: $productId, media: $media) {
    media { ... on MediaImage { id status } }
    mediaUserErrors { field message }
  }
}
"""


def ist_bild(daten: bytes) -> bool:
    return (daten[:3] == b"\xff\xd8\xff"
            or daten[:8] == b"\x89PNG\r\n\x1a\n"
            or daten[:6] in (b"GIF87a", b"GIF89a")
            or (daten[:4] == b"RIFF" and daten[8:12] == b"WEBP"))


def endung(daten: bytes) -> str:
    if daten[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if daten[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if daten[:4] == b"RIFF":
        return ".webp"
    return ".gif"


def isbn_sauber(roh: str) -> str:
    return re.sub(r"[^0-9Xx]", "", str(roh or "")).upper()


def isbn_gueltig(isbn: str) -> bool:
    """Prüfziffer von ISBN-10 und ISBN-13.

    Ohne diese Prüfung landet jeder Zahlendreher als Fehlgriff im
    Katalog — und ein falsches Cover fällt niemandem auf.
    """
    if len(isbn) == 13 and isbn.isdigit():
        summe = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(isbn[:12]))
        return (10 - summe % 10) % 10 == int(isbn[12])
    if len(isbn) == 10:
        if not re.fullmatch(r"\d{9}[\dX]", isbn):
            return False
        summe = sum((10 - i) * (10 if c == "X" else int(c))
                    for i, c in enumerate(isbn))
        return summe % 11 == 0
    return False


def isbn13(isbn: str) -> str:
    """ISBN-10 nach ISBN-13 umrechnen; ISBN-13 bleibt unverändert."""
    if len(isbn) == 13:
        return isbn
    rumpf = "978" + isbn[:9]
    summe = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(rumpf))
    return rumpf + str((10 - summe % 10) % 10)


def cover_zu_isbn(isbn: str):
    """Sucht ein Cover. Google Books zuerst, dann Open Library.

    Beide liefern zu deutschen Kinderbüchern nicht immer etwas — dann
    bleibt die Handsuche. Geraten wird nicht.
    """
    voll = isbn13(isbn)
    try:
        req = urllib.request.Request(
            "https://www.googleapis.com/books/v1/volumes?q=isbn:" + voll,
            headers={"User-Agent": "Zwergenladen"})
        with urllib.request.urlopen(req, timeout=ZEIT) as r:
            antwort = json.loads(r.read().decode("utf-8", "replace"))
        for eintrag in (antwort.get("items") or [])[:3]:
            info = eintrag.get("volumeInfo") or {}
            bilder = info.get("imageLinks") or {}
            url = (bilder.get("extraLarge") or bilder.get("large")
                   or bilder.get("medium") or bilder.get("thumbnail"))
            if url:
                url = url.replace("http://", "https://").replace("&edge=curl", "")
                url = re.sub(r"zoom=\d", "zoom=2", url)
                daten, meldung = von_url(url)
                if daten:
                    titel = info.get("title", "")
                    return daten, f"Google Books · {titel[:40]}", ""
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        pass

    daten, meldung = von_url(
        f"https://covers.openlibrary.org/b/isbn/{voll}-L.jpg?default=false")
    if daten:
        return daten, "Open Library", ""
    return None, "", "Zu dieser ISBN ist kein Cover hinterlegt."


def von_url(url: str):
    """Holt ein Bild und prüft, dass es wirklich eins ist."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh) Zwergenladen",
            "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"})
        with urllib.request.urlopen(req, timeout=ZEIT) as r:
            daten = r.read(15 * 1024 * 1024)
    except (urllib.error.URLError, OSError, ValueError) as e:
        return None, f"Nicht erreichbar: {e}"
    if not ist_bild(daten):
        return None, "Die Adresse liefert kein Bild — oft ist es eine HTML-Seite."
    if len(daten) < MIN_BYTES:
        return None, f"Nur {len(daten)} Bytes — das ist ein Platzhalter oder Icon."
    return daten, ""


@st.cache_data(show_spinner=False, ttl=3600)
def vorschlag(marke, sku, ean, titel):
    """Fragt bild_quellen nach einer Bild-URL und holt das Bild.

    Gibt (daten, quelle, meldung) zurück. Fehler der Fremdfunktion
    werden abgefangen: Ein Hersteller, der heute anders antwortet,
    darf die Seite nicht lahmlegen.
    """
    if bild_quellen is None:
        return None, "", "bild_quellen.py liegt nicht neben der App"
    try:
        ergebnis = bild_quellen.finde_bild(marke, sku, ean, titel)
    except Exception as e:                      # fremder Code, fremde Fehler
        return None, "", f"Suche fehlgeschlagen: {e}"
    if not ergebnis:
        return None, "", "kein Treffer"
    url, quelle = (list(ergebnis) + ["", ""])[:2]
    if not url:
        return None, "", "kein Treffer"
    daten, meldung = von_url(url)
    return daten, (quelle or url), meldung


@st.cache_data(show_spinner="Lese Katalog …", ttl=600)
def katalog():
    liste, cursor = [], None
    while True:
        antwort = shopify_http.execute(PRODUKTE, {"cursor": cursor})
        fehler = str(antwort.get("_error", ""))
        if fehler:
            if "THROTTLED" in fehler.upper():
                time.sleep(2)
                continue
            raise RuntimeError(fehler)
        block = antwort.get("products", {})
        for k in block.get("edges", []):
            n = k["node"]
            if (n.get("media") or {}).get("edges"):
                continue
            kanaele = [(e["node"]["publication"] or {}).get("name", "")
                       for e in n.get("resourcePublicationsV2", {}).get("edges", [])
                       if e["node"].get("isPublished")]
            v = [x["node"] for x in n.get("variants", {}).get("edges", [])]
            liste.append({
                "id": n["id"], "handle": n["handle"], "titel": n["title"],
                "marke": (n.get("vendor") or "").strip(),
                "bestand": n.get("totalInventory") or 0,
                "sku": next((str(x.get("sku") or "").strip() for x in v if x.get("sku")), ""),
                "ean": next((str(x.get("barcode") or "").strip() for x in v if x.get("barcode")), ""),
                "variante": v[0]["id"] if v else "",
                "varianten": len(v),
                "shop": any("online" in k.lower() for k in kanaele),
            })
        if not block.get("pageInfo", {}).get("hasNextPage"):
            return liste
        cursor = block["pageInfo"]["endCursor"]


def hochladen(produkt, daten, dateiname):
    typ = mimetypes.guess_type(dateiname)[0] or "image/jpeg"
    a = shopify_http.execute(STAGED, {"input": [{
        "resource": "IMAGE", "filename": dateiname, "mimeType": typ,
        "httpMethod": "POST", "fileSize": str(len(daten))}]})
    fehler = a.get("_error") or [u.get("message") for u in
                                 (a.get("stagedUploadsCreate", {}).get("userErrors") or [])]
    if fehler:
        return f"Zwischenspeicher: {fehler}"
    ziele = (a.get("stagedUploadsCreate") or {}).get("stagedTargets") or []
    if not ziele:
        return "Shopify hat kein Upload-Ziel geliefert."
    ziel = ziele[0]

    grenze = "----zwergenladen" + uuid.uuid4().hex
    teile = []
    for par in ziel.get("parameters", []):
        teile.append(f'--{grenze}\r\nContent-Disposition: form-data; '
                     f'name="{par["name"]}"\r\n\r\n{par["value"]}\r\n'.encode())
    teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="file"; '
                 f'filename="{dateiname}"\r\nContent-Type: {typ}\r\n\r\n'.encode())
    teile.append(daten)
    teile.append(f"\r\n--{grenze}--\r\n".encode())
    koerper = b"".join(teile)
    req = urllib.request.Request(
        ziel["url"], data=koerper, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={grenze}",
                 "Content-Length": str(len(koerper))})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            if r.status not in (200, 201, 204):
                return f"Upload-Antwort {r.status}"
    except (urllib.error.URLError, OSError) as e:
        return f"Upload fehlgeschlagen: {e}"

    b = shopify_http.execute(ANHAENGEN, {
        "productId": produkt["id"],
        "media": [{"originalSource": ziel["resourceUrl"],
                   "alt": produkt["titel"][:500],
                   "mediaContentType": "IMAGE"}]})
    fehler = b.get("_error") or [u.get("message") for u in
                                 (b.get("productCreateMedia", {}).get("mediaUserErrors") or [])]
    return str(fehler) if fehler else ""


# ──────────────────────────────────────────────────────────────
try:
    offen = katalog()
except RuntimeError as e:
    st.error(f"Shopify antwortet nicht: {e}")
    st.stop()

if "erledigt" not in st.session_state:
    st.session_state.erledigt = set()
offen = [p for p in offen if p["id"] not in st.session_state.erledigt]

# ──────────────────────────────────────────────────────────────
# Reihenfolge der Arbeit. Nicht jede Lücke ist gleich viel wert, und
# „irgendwo anfangen“ führt dazu, dass die teuren Fälle liegen bleiben.
#
#   1  im Onlineshop UND lieferbar  — der Kunde sieht es und kann kaufen
#   2  nur Kasse/Shop-App, lieferbar — hilft beim Kassieren am iPad
#   3  im Onlineshop, nicht lieferbar — lohnt nur bei Nachbestellung
#   4  weder sichtbar noch lieferbar — aufheben, nicht aufarbeiten
# ──────────────────────────────────────────────────────────────
WELLEN = {
    1: "① Im Shop und lieferbar",
    2: "② Kasse und lieferbar",
    3: "③ Im Shop, nicht lieferbar",
    4: "④ Rest",
}


def welle(p):
    hat = (p["bestand"] or 0) > 0
    if p["shop"] and hat:
        return 1
    if hat:
        return 2
    if p["shop"]:
        return 3
    return 4


for p in offen:
    p["welle"] = welle(p)

with st.sidebar:
    st.subheader("Reihenfolge")
    gewaehlt = st.radio(
        "Welle", list(WELLEN),
        format_func=lambda w: f"{WELLEN[w]}  ({sum(1 for p in offen if p['welle'] == w)})",
        index=0)
    st.caption("Von oben nach unten abarbeiten. Welle ④ ist nichts wert — "
               "die Produkte sind weder sichtbar noch lieferbar.")

    st.subheader("Eingrenzen")
    in_welle = [p for p in offen if p["welle"] == gewaehlt]
    marken = sorted({p["marke"] or "—" for p in in_welle})
    marke = st.selectbox(
        "Marke", ["alle"] + marken,
        format_func=lambda m: (m if m == "alle" else
                               f"{m}  ({sum(1 for p in in_welle if (p['marke'] or '—') == m)})"))
    st.caption("Markenweise arbeiten: eine Quelle, ein Handgriff, "
               "und man gewöhnt sich an die Benennung des Herstellers.")

    if st.button("Katalog neu laden"):
        katalog.clear()
        st.session_state.erledigt = set()
        st.session_state.pop("stapel", None)
        st.rerun()

gefiltert = [p for p in in_welle
             if marke == "alle" or (p["marke"] or "—") == marke]

a, b, c, d = st.columns(4)
a.metric("ohne Bild gesamt", len(offen))
b.metric(WELLEN[gewaehlt].split(" ", 1)[1][:22], len(in_welle))
c.metric("in dieser Auswahl", len(gefiltert))
d.metric("heute gesetzt", len(st.session_state.erledigt))

if not gefiltert:
    st.success("In dieser Auswahl fehlt kein Bild mehr. "
               "Nächste Marke oder nächste Welle wählen.")
    with st.expander("Verteilung nach Marke"):
        for m, n in Counter(p["marke"] or "—" for p in offen).most_common():
            st.write(f"{n:>4}  {m}")
    st.stop()

if bild_quellen is None:
    st.warning("`bild_quellen.py` liegt nicht neben der App — es gibt dann "
               "keine automatischen Vorschläge, nur Einfügen von Hand.")

einzeln, stapel = st.tabs(["Einzeln prüfen", "Stapel"])

# ──────────────────────────────────────────────────────────────
with einzeln:
    produkt = gefiltert[0]
    links, rechts = st.columns([1, 1])

    with links:
        st.subheader(produkt["titel"])
        st.write(f"**Marke** {produkt['marke'] or '—'}  ·  "
                 f"**Bestand** {produkt['bestand']}")
        st.write(f"**Artikelnummer** {produkt['sku'] or '—'}  ·  "
                 f"**EAN** {produkt['ean'] or '—'}")
        st.caption(f"Handle: {produkt['handle']}")

        begriff = produkt["sku"] or produkt["titel"]
        ist_buch = produkt["marke"].lower() in VERLAGE
        basis = HERSTELLER.get(produkt["marke"].lower(), "")
        st.markdown("**Selbst suchen bei**")
        if ist_buch:
            such = urllib.parse.quote(f'{produkt["titel"]} {produkt["marke"]}')
            st.markdown(f"- [Buchsuche](https://www.google.com/search?tbm=bks&q={such})")
            st.markdown(f"- [ISBN finden](https://www.google.com/search?q={such}+ISBN)")
        elif basis:
            st.markdown(f"- [{produkt['marke']} – Herstellerseite]"
                        f"({basis}{urllib.parse.quote(begriff)})")
        st.markdown("- [Bildersuche](https://www.google.com/search?tbm=isch&q="
                    + urllib.parse.quote(f"{produkt['marke']} {begriff}") + ")")
        if produkt["ean"]:
            st.markdown("- [EAN-Suche](https://www.google.com/search?q="
                        + urllib.parse.quote(produkt["ean"]) + ")")

        if st.button("Überspringen", width="stretch"):
            st.session_state.erledigt.add(produkt["id"])
            st.rerun()

    with rechts:
        daten, dateiname, meldung, quelle = None, "", "", ""

        with st.spinner("Suche beim Hersteller …"):
            v_daten, v_quelle, v_meldung = vorschlag(
                produkt["marke"], produkt["sku"], produkt["ean"], produkt["titel"])

        if v_daten:
            st.success(f"Vorschlag gefunden · Quelle: {v_quelle}")
            daten, quelle = v_daten, v_quelle
            dateiname = produkt["handle"] + endung(v_daten)
        else:
            st.info(f"Kein Vorschlag ({v_meldung}). Von Hand einsetzen:")

        with st.expander("Anderes Bild verwenden", expanded=not v_daten):
            wege = ["ISBN", "Datei", "Adresse"] if ist_buch else ["Datei", "Adresse"]
            weg = st.radio("Herkunft", wege, horizontal=True, key="weg_einzeln")
            if weg == "ISBN":
                roh_isbn = st.text_input(
                    "ISBN des Buchs", key="isbn_einzeln",
                    placeholder="978-3-522-20250-3")
                st.caption("Steht hinten auf dem Buch über dem Strichcode. "
                           "Bindestriche egal.")
                isbn = isbn_sauber(roh_isbn)
                if isbn and not isbn_gueltig(isbn):
                    meldung = ("Diese ISBN stimmt nicht — die Prüfziffer passt "
                               "nicht. Vermutlich ein Zahlendreher.")
                elif isbn:
                    with st.spinner("Suche Cover …"):
                        roh, quelle_isbn, meldung = cover_zu_isbn(isbn)
                    if roh:
                        daten = roh
                        dateiname = produkt["handle"] + endung(roh)
                        quelle = quelle_isbn
                        st.session_state["isbn_fertig"] = isbn13(isbn)
            if weg == "Datei":
                hoch = st.file_uploader("Bilddatei",
                                        type=["jpg", "jpeg", "png", "webp", "gif"],
                                        key="datei_einzeln")
                if hoch is not None:
                    roh = hoch.getvalue()
                    if ist_bild(roh):
                        daten, dateiname, quelle = roh, hoch.name, "von Hand"
                    else:
                        meldung = "Das ist kein gültiges Bildformat."
            else:
                url = st.text_input("Bildadresse", placeholder="https://… .jpg",
                                    key="url_einzeln")
                st.caption("Im Browser Rechtsklick aufs Bild → "
                           "„Bildadresse kopieren“.")
                if url:
                    roh, meldung = von_url(url.strip())
                    if roh:
                        daten = roh
                        dateiname = produkt["handle"] + endung(roh)
                        quelle = "von Hand"

        if meldung:
            st.warning(meldung)

        if daten:
            st.image(daten, width="stretch")
            st.caption(f"{len(daten)/1024:.0f} KB · {quelle}")
            st.info(f"Gehört dieses Bild zu **{produkt['titel']}**?")

            fertige_isbn = st.session_state.get("isbn_fertig", "")
            isbn_setzen = False
            if fertige_isbn and produkt["varianten"] == 1 and produkt["variante"]:
                isbn_setzen = st.checkbox(
                    f"ISBN {fertige_isbn} auch als Barcode eintragen "
                    f"(steht jetzt: {produkt['ean'] or 'leer'})", value=True)
                st.caption("Die achtstelligen Altnummern sind keine ISBN. "
                           "Mit der echten ISBN im Barcodefeld lässt sich das "
                           "Buch künftig direkt am Regal scannen.")

            if st.button("Bild zu diesem Produkt setzen", type="primary",
                         width="stretch"):
                with st.spinner("Lade zu Shopify …"):
                    fehler = hochladen(produkt, daten, dateiname or "bild.jpg")
                if not fehler and isbn_setzen:
                    antwort = shopify_http.execute(BARCODE, {
                        "productId": produkt["id"],
                        "variants": [{"id": produkt["variante"],
                                      "barcode": fertige_isbn}]})
                    nebenfehler = antwort.get("_error") or [
                        u.get("message") for u in
                        (antwort.get("productVariantsBulkUpdate", {})
                         .get("userErrors") or [])]
                    if nebenfehler:
                        st.warning(f"Bild gesetzt, ISBN nicht: {nebenfehler}")
                    else:
                        st.caption(f"ISBN {fertige_isbn} als Barcode eingetragen.")
                if fehler:
                    st.error(fehler)
                    if "scope" in fehler.lower() or "access denied" in fehler.lower():
                        st.caption("Der App fehlt der Zugriffsbereich write_products.")
                else:
                    st.success("Gesetzt.")
                    st.session_state.pop("isbn_fertig", None)
                    st.session_state.erledigt.add(produkt["id"])
                    time.sleep(1)
                    st.rerun()

# ──────────────────────────────────────────────────────────────
with stapel:
    st.caption("Sucht für mehrere Produkte auf einmal und zeigt alle Treffer "
               "nebeneinander. Du hakst ab, was falsch ist — gesetzt wird nur "
               "das Angehakte.")
    menge = st.slider("Wie viele Produkte auf einmal", 5, 60, 20, step=5)
    if st.button("Vorschläge suchen", type="primary"):
        st.session_state.stapel = []
        st.session_state.ohne_fund = []
        fortschritt = st.progress(0.0, "Suche …")
        ziel = gefiltert[:menge]
        for i, p in enumerate(ziel, 1):
            d, q, m = vorschlag(p["marke"], p["sku"], p["ean"], p["titel"])
            if d:
                st.session_state.stapel.append({"p": p, "daten": d, "quelle": q})
            else:
                st.session_state.ohne_fund.append({"p": p, "grund": m})
            fortschritt.progress(i / len(ziel), f"{i}/{len(ziel)} · {p['titel'][:40]}")
        fortschritt.empty()
        st.rerun()

    treffer = st.session_state.get("stapel", [])
    if treffer:
        st.write(f"**{len(treffer)} Vorschläge** — prüf jedes Bild gegen den "
                 "Titel darunter.")
        auswahl = {}
        spalten = st.columns(4)
        for i, eintrag in enumerate(treffer):
            with spalten[i % 4]:
                st.image(eintrag["daten"], width="stretch")
                st.caption(eintrag["p"]["titel"][:60])
                st.caption(f"{eintrag['p']['marke']} · {eintrag['p']['sku'] or '—'}")
                auswahl[eintrag["p"]["id"]] = st.checkbox(
                    "passt", value=True, key="ok_" + eintrag["p"]["id"])

        gewaehlt = [e for e in treffer if auswahl.get(e["p"]["id"])]
        st.divider()
        st.write(f"{len(gewaehlt)} von {len(treffer)} ausgewählt")
        if gewaehlt and st.button(f"{len(gewaehlt)} Bilder setzen",
                                  type="primary", width="stretch"):
            balken = st.progress(0.0, "Lade hoch …")
            ok = fehlgeschlagen = 0
            for i, e in enumerate(gewaehlt, 1):
                name = e["p"]["handle"] + endung(e["daten"])
                fehler = hochladen(e["p"], e["daten"], name)
                if fehler:
                    fehlgeschlagen += 1
                    st.error(f"{e['p']['titel'][:40]}: {fehler}")
                else:
                    ok += 1
                    st.session_state.erledigt.add(e["p"]["id"])
                balken.progress(i / len(gewaehlt), f"{i}/{len(gewaehlt)}")
            balken.empty()
            st.success(f"{ok} gesetzt, {fehlgeschlagen} fehlgeschlagen")
            st.session_state.stapel = []
            time.sleep(1.5)
            st.rerun()

    ohne = st.session_state.get("ohne_fund", [])
    if ohne:
        st.divider()
        st.subheader(f"{len(ohne)} ohne Vorschlag — das ist die Handarbeit")
        st.caption("Diese Produkte findet die automatische Suche nicht. "
                   "Im Reiter „Einzeln prüfen“ kommen sie der Reihe nach, "
                   "mit Suchlinks daneben.")
        gruende = Counter(e["grund"] or "kein Treffer" for e in ohne)
        for grund, n in gruende.most_common():
            st.write(f"· {n}× {grund}")
        with st.expander("Welche Produkte das sind"):
            for e in ohne:
                p_ = e["p"]
                st.write(f"{p_['titel'][:60]}  ·  {p_['marke']}  ·  "
                         f"{p_['sku'] or p_['ean'] or 'keine Nummer'}")
        if all(not (e["p"]["sku"] or e["p"]["ean"]) for e in ohne):
            st.info("Bei allen fehlt Artikelnummer und EAN. Ohne eine Nummer "
                    "kann keine Quelle etwas finden — hier hilft nur der Titel.")

st.divider()
with st.expander(f"Noch {max(0, len(gefiltert)-1)} weitere in dieser Auswahl"):
    for p in gefiltert[1:21]:
        st.write(f"· {p['titel'][:70]}  ({p['marke']})")
    if len(gefiltert) > 21:
        st.caption(f"… und {len(gefiltert)-21} weitere")

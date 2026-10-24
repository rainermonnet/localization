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
        variants(first: 10) { edges { node { sku barcode } } }
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

with st.sidebar:
    st.subheader("Auswahl")
    marken = sorted({p["marke"] or "—" for p in offen})
    marke = st.selectbox("Marke", ["alle"] + marken)
    nur_shop = st.checkbox("nur im Onlineshop sichtbar", value=True)
    nur_bestand = st.checkbox("nur mit Bestand", value=False)
    if st.button("Katalog neu laden"):
        katalog.clear()
        st.session_state.erledigt = set()
        st.rerun()

gefiltert = [p for p in offen
             if (marke == "alle" or (p["marke"] or "—") == marke)
             and (not nur_shop or p["shop"])
             and (not nur_bestand or (p["bestand"] or 0) > 0)]

a, b, c = st.columns(3)
a.metric("ohne Bild", len(offen))
b.metric("in dieser Auswahl", len(gefiltert))
c.metric("in dieser Sitzung gesetzt", len(st.session_state.erledigt))

if not gefiltert:
    st.success("In dieser Auswahl fehlt kein Bild mehr.")
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
        basis = HERSTELLER.get(produkt["marke"].lower(), "")
        st.markdown("**Selbst suchen bei**")
        if basis:
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
            weg = st.radio("Herkunft", ["Datei", "Adresse"], horizontal=True,
                           key="weg_einzeln")
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
            if st.button("Bild zu diesem Produkt setzen", type="primary",
                         width="stretch"):
                with st.spinner("Lade zu Shopify …"):
                    fehler = hochladen(produkt, daten, dateiname or "bild.jpg")
                if fehler:
                    st.error(fehler)
                    if "scope" in fehler.lower() or "access denied" in fehler.lower():
                        st.caption("Der App fehlt der Zugriffsbereich write_products.")
                else:
                    st.success("Gesetzt.")
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
        fortschritt = st.progress(0.0, "Suche …")
        ziel = gefiltert[:menge]
        for i, p in enumerate(ziel, 1):
            d, q, m = vorschlag(p["marke"], p["sku"], p["ean"], p["titel"])
            if d:
                st.session_state.stapel.append({"p": p, "daten": d, "quelle": q})
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

st.divider()
with st.expander(f"Noch {max(0, len(gefiltert)-1)} weitere in dieser Auswahl"):
    for p in gefiltert[1:21]:
        st.write(f"· {p['titel'][:70]}  ({p['marke']})")
    if len(gefiltert) > 21:
        st.caption(f"… und {len(gefiltert)-21} weitere")

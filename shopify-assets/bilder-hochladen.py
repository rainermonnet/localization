"""
bilder-hochladen.py — Produktbilder aus einem lokalen Ordner nach Shopify
==========================================================================

Lädt Bilddateien von der Festplatte zu Produkten hoch, denen das Bild
fehlt. Gedacht für Lieferantenbilder, die als Datei vorliegen — nicht
als URL.

WIE DIE ZUORDNUNG ZUSTANDE KOMMT
---------------------------------
Dateinamen sagen selten sauber, zu welchem Produkt sie gehören. Deshalb
wird nicht geraten, sondern in drei Stufen zugeordnet:

  1. Eine Artikelnummer (SKU) steckt im Dateinamen  → sicher
  2. Der Shopify-Handle steckt im Dateinamen        → sicher
  3. Wortüberschneidung mit dem Produkttitel        → nur wenn der beste
     Treffer deutlich vor dem zweitbesten liegt

Bleibt es unklar, wird die Datei NICHT hochgeladen, sondern mit ihren
Kandidaten aufgelistet. Ein Bild am falschen Produkt ist schlimmer als
gar keins: Es fällt niemandem auf und wandert in den Google-Feed.

ZUORDNUNG VON HAND
------------------
Der Probelauf schreibt `bilder-zuordnung.csv` mit allen Dateien und der
vorgeschlagenen Zuordnung. Dort lässt sich korrigieren und ergänzen:

    Datei;Handle;Produkt;Sicherheit
    ring-01.jpg;grapat-ring;Grapat Ring;SKU

Danach:  python3 bilder-hochladen.py <ordner> --zuordnung bilder-zuordnung.csv

Die Datei schlägt jede automatische Zuordnung. Eine leere Handle-Spalte
heißt: überspringen.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"

    # Probelauf — zeigt die Zuordnung, lädt nichts hoch
    python3 bilder-hochladen.py "/Users/rainermonnet/Library/Mobile Documents/com~apple~CloudDocs/Zwergenladen/Shopify"

    # nur eine Marke (Standard: alle Produkte ohne Bild)
    python3 bilder-hochladen.py <ordner> --marke Grapat

    # hochladen
    python3 bilder-hochladen.py <ordner> --marke Grapat --live

Braucht den Zugriffsbereich write_products. Vorhandene Bilder werden nie
ersetzt — es wird nur Produkten ohne Bild etwas hinzugefügt, außer mit
--auch-mit-bild.
"""

import csv
import mimetypes
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import uuid

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

ENDUNGEN = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_MB = 20
ZUORDNUNG_CSV = "bilder-zuordnung.csv"

# Wortüberschneidung: ab hier gilt ein Titeltreffer, und er muss den
# zweitbesten um diesen Abstand schlagen.
MIN_PUNKTE = 0.55
MIN_ABSTAND = 0.15

# Wörter, die in fast jedem Dateinamen stehen und nichts unterscheiden
FUELLWOERTER = {
    "img", "image", "foto", "photo", "bild", "produkt", "product", "shop",
    "shopify", "web", "klein", "gross", "original", "kopie", "copy", "final",
    "neu", "new", "dsc", "scan", "front", "back", "detail", "jpg", "jpeg", "png",
}

PRODUKTE = """
query($cursor: String, $suche: String!) {
  products(first: 50, after: $cursor, query: $suche) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        handle
        title
        vendor
        media(first: 1) { edges { node { id } } }
        variants(first: 25) { edges { node { sku } } }
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


def entschaerfen(text):
    """Kleinschreibung, Umlaute aufgelöst, nur Buchstaben und Ziffern."""
    t = unicodedata.normalize("NFKD", str(text or "").lower())
    t = t.replace("ß", "ss")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def woerter(text):
    return {w for w in entschaerfen(text).split()
            if len(w) > 2 and w not in FUELLWOERTER}


def bilder_finden(ordner):
    gefunden = []
    for wurzel, verzeichnisse, dateien in os.walk(ordner):
        verzeichnisse[:] = [v for v in verzeichnisse if not v.startswith(".")]
        for d in sorted(dateien):
            if d.startswith(".") or os.path.splitext(d)[1].lower() not in ENDUNGEN:
                continue
            pfad = os.path.join(wurzel, d)
            try:
                groesse = os.path.getsize(pfad)
            except OSError:
                continue
            gefunden.append({"pfad": pfad, "name": d, "groesse": groesse})
    return gefunden


def produkte_holen(marke, auch_mit_bild):
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
            hat_bild = bool((n.get("media") or {}).get("edges"))
            if hat_bild and not auch_mit_bild:
                continue
            skus = [str((v["node"].get("sku") or "")).strip()
                    for v in n.get("variants", {}).get("edges", [])]
            liste.append({
                "id": n["id"], "handle": n["handle"], "titel": n["title"],
                "marke": n.get("vendor", ""), "hat_bild": hat_bild,
                "skus": [s for s in skus if s],
                "woerter": woerter(n["title"]) | woerter(n["handle"]),
            })
        if not block.get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = block["pageInfo"]["endCursor"]
        time.sleep(0.2)
    return liste


def zuordnen(datei, produkte):
    """Gibt (produkt, sicherheit, kandidaten) zurück. produkt kann None sein."""
    roh = os.path.splitext(datei["name"])[0]
    flach = entschaerfen(roh).replace(" ", "")
    dwoerter = woerter(roh)

    # 1. SKU im Dateinamen
    for p in produkte:
        for sku in p["skus"]:
            s = entschaerfen(sku).replace(" ", "")
            if len(s) >= 4 and s in flach:
                return p, f"SKU {sku}", []

    # 2. Handle im Dateinamen
    for p in produkte:
        h = entschaerfen(p["handle"]).replace(" ", "")
        if len(h) >= 6 and h in flach:
            return p, "Handle", []

    # 3. Wortüberschneidung
    if not dwoerter:
        return None, "Dateiname ohne verwertbare Wörter", []
    bewertet = []
    for p in produkte:
        if not p["woerter"]:
            continue
        gemeinsam = dwoerter & p["woerter"]
        if gemeinsam:
            bewertet.append((len(gemeinsam) / len(dwoerter), p))
    if not bewertet:
        return None, "kein Treffer", []
    bewertet.sort(key=lambda t: -t[0])
    bester, zweiter = bewertet[0][0], (bewertet[1][0] if len(bewertet) > 1 else 0.0)
    kandidaten = [p["titel"] for _, p in bewertet[:3]]
    if bester >= MIN_PUNKTE and (bester - zweiter) >= MIN_ABSTAND:
        return bewertet[0][1], f"Titel {bester:.0%}", kandidaten
    return None, f"unklar ({bester:.0%} vs {zweiter:.0%})", kandidaten


def hochladen(datei):
    """Legt die Datei in Shopifys Zwischenspeicher. Gibt resourceUrl zurück."""
    typ = mimetypes.guess_type(datei["name"])[0] or "image/jpeg"
    a = shopify_http.execute(STAGED, {"input": [{
        "resource": "IMAGE", "filename": datei["name"], "mimeType": typ,
        "httpMethod": "POST", "fileSize": str(datei["groesse"])}]})
    fehler = a.get("_error") or [u.get("message") for u in
                                 (a.get("stagedUploadsCreate", {}).get("userErrors") or [])]
    if fehler:
        return None, str(fehler)
    ziele = (a.get("stagedUploadsCreate") or {}).get("stagedTargets") or []
    if not ziele:
        return None, "kein Upload-Ziel erhalten"
    ziel = ziele[0]

    grenze = "----zwergenladen" + uuid.uuid4().hex
    teile = []
    for par in ziel.get("parameters", []):
        teile.append(
            f'--{grenze}\r\nContent-Disposition: form-data; name="{par["name"]}"'
            f'\r\n\r\n{par["value"]}\r\n'.encode())
    with open(datei["pfad"], "rb") as f:
        inhalt = f.read()
    teile.append(
        f'--{grenze}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{datei["name"]}"\r\nContent-Type: {typ}\r\n\r\n'.encode())
    teile.append(inhalt)
    teile.append(f"\r\n--{grenze}--\r\n".encode())
    koerper = b"".join(teile)

    req = urllib.request.Request(
        ziel["url"], data=koerper, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={grenze}",
                 "Content-Length": str(len(koerper))})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            if r.status not in (200, 201, 204):
                return None, f"Upload-Antwort {r.status}"
    except urllib.error.HTTPError as e:
        return None, f"Upload fehlgeschlagen: HTTP {e.code} {e.read()[:200]!r}"
    except (urllib.error.URLError, OSError) as e:
        return None, f"Upload fehlgeschlagen: {e}"
    return ziel["resourceUrl"], ""


def anhaengen(produkt, quelle, alt):
    a = shopify_http.execute(ANHAENGEN, {
        "productId": produkt["id"],
        "media": [{"originalSource": quelle, "alt": alt[:500],
                   "mediaContentType": "IMAGE"}]})
    fehler = a.get("_error") or [u.get("message") for u in
                                 (a.get("productCreateMedia", {}).get("mediaUserErrors") or [])]
    return (str(fehler) if fehler else "")


def zuordnung_lesen(pfad):
    tabelle = {}
    with open(pfad, encoding="utf-8-sig") as f:
        for z in csv.DictReader(f, delimiter=";"):
            name = (z.get("Datei") or "").strip()
            handle = (z.get("Handle") or "").strip()
            if name:
                tabelle[name] = handle
    return tabelle


def main():
    frei = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not frei:
        sys.exit('Ordner angeben:\n  python3 bilder-hochladen.py "/Pfad/zum/Ordner"')
    ordner = os.path.expanduser(frei[0])
    if not os.path.isdir(ordner):
        sys.exit(f"Ordner nicht gefunden:\n  {ordner}")

    def wert(name):
        if name in sys.argv:
            k = sys.argv.index(name)
            if k + 1 < len(sys.argv):
                return sys.argv[k + 1]
        return ""

    live = "--live" in sys.argv
    marke = wert("--marke")
    auch_mit_bild = "--auch-mit-bild" in sys.argv
    vorgabe_datei = wert("--zuordnung")

    if not live:
        print("PROBELAUF — es wird nichts hochgeladen.")
        print("Zum Hochladen:  … --live\n")

    dateien = bilder_finden(ordner)
    print(f"Ordner: {ordner}")
    print(f"{len(dateien)} Bilddateien gefunden")
    zu_gross = [d for d in dateien if d["groesse"] > MAX_MB * 1024 * 1024]
    for d in zu_gross:
        print(f"  ! zu groß ({d['groesse']/1048576:.1f} MB): {d['name']}")
    dateien = [d for d in dateien if d not in zu_gross]
    if not dateien:
        sys.exit("Keine verwertbaren Bilddateien.")

    print(f"\nLese Produkte{f' der Marke {marke}' if marke else ''} …")
    produkte = produkte_holen(marke, auch_mit_bild)
    print(f"{len(produkte)} Produkte {'' if auch_mit_bild else 'ohne Bild '}gefunden")
    if not produkte:
        sys.exit("Nichts zuzuordnen.")
    nach_handle = {p["handle"]: p for p in produkte}

    vorgabe = {}
    if vorgabe_datei:
        if not os.path.exists(vorgabe_datei):
            sys.exit(f"{vorgabe_datei} nicht gefunden.")
        vorgabe = zuordnung_lesen(vorgabe_datei)
        print(f"{len(vorgabe)} Zeilen aus {vorgabe_datei} übernommen")

    paare, unklar = [], []
    for d in dateien:
        if d["name"] in vorgabe:
            handle = vorgabe[d["name"]]
            if not handle:
                continue                      # bewusst übersprungen
            p = nach_handle.get(handle)
            if not p:
                unklar.append((d, f"Handle „{handle}“ nicht unter den Produkten", []))
                continue
            paare.append((d, p, "von Hand"))
            continue
        p, sicherheit, kandidaten = zuordnen(d, produkte)
        if p:
            paare.append((d, p, sicherheit))
        else:
            unklar.append((d, sicherheit, kandidaten))

    # Mehrfachbelegung sichtbar machen
    belegt = {}
    for d, p, _ in paare:
        belegt.setdefault(p["handle"], []).append(d["name"])
    mehrfach = {h: v for h, v in belegt.items() if len(v) > 1}

    print(f"\n{'='*74}\n{len(paare)} ZUORDNUNGEN\n{'='*74}")
    for d, p, sicherheit in sorted(paare, key=lambda t: t[1]["titel"]):
        print(f"  {d['name'][:38]:<38} → {p['titel'][:30]:<30} [{sicherheit}]")
    if mehrfach:
        print(f"\n{len(mehrfach)} Produkte bekämen mehrere Bilder:")
        for h, v in mehrfach.items():
            print(f"    {nach_handle[h]['titel'][:40]}: {', '.join(v)}")
        print("  Das ist in Ordnung, wenn es Zusatzansichten sind.")

    if unklar:
        print(f"\n{len(unklar)} NICHT ZUGEORDNET — werden nicht hochgeladen")
        for d, grund, kandidaten in unklar:
            print(f"  {d['name'][:40]:<40} {grund}")
            for k in kandidaten:
                print(f"      Kandidat: {k[:56]}")

    ohne_datei = [p for p in produkte if p["handle"] not in belegt]
    if ohne_datei:
        print(f"\n{len(ohne_datei)} Produkte bleiben ohne Bild:")
        for p in ohne_datei[:15]:
            print(f"    {p['titel'][:56]}")
        if len(ohne_datei) > 15:
            print(f"    … und {len(ohne_datei)-15} weitere")

    with open(ZUORDNUNG_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Datei", "Handle", "Produkt", "Sicherheit"])
        for d, p, s in paare:
            w.writerow([d["name"], p["handle"], p["titel"], s])
        for d, grund, _ in unklar:
            w.writerow([d["name"], "", "", grund])
    print(f"\nGeschrieben: {ZUORDNUNG_CSV}")
    print("Dort korrigieren und mit --zuordnung wieder hereingeben.")

    if not live:
        print(f"\n{len(paare)} Bilder bereit. Mit --live hochladen.")
        return
    if not paare:
        print("\nNichts hochzuladen.")
        return

    antwort = input(f"\n{len(paare)} Bilder hochladen? (ja/NEIN): ").strip()
    if antwort.lower() != "ja":
        print("Abgebrochen.")
        return

    ok = fehler = 0
    for i, (d, p, _) in enumerate(paare, 1):
        quelle, meldung = hochladen(d)
        if not quelle:
            fehler += 1
            print(f"  ✗ {d['name'][:34]}: {meldung}")
            if "scope" in meldung.lower() or "access denied" in meldung.lower():
                print("\nDer App fehlt der Zugriffsbereich write_products.")
                return
            continue
        meldung = anhaengen(p, quelle, p["titel"])
        if meldung:
            fehler += 1
            print(f"  ✗ {p['titel'][:34]}: {meldung}")
        else:
            ok += 1
            print(f"  ✓ {p['titel'][:46]}")
        if i % 10 == 0:
            print(f"  … {i}/{len(paare)}")
        time.sleep(0.3)

    print(f"\nFertig: {ok} Bilder gesetzt, {fehler} fehlgeschlagen")
    print("Shopify verarbeitet die Bilder noch einige Sekunden nach.")


if __name__ == "__main__":
    main()

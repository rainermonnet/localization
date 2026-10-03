"""
shopify_zugang.py — Zugangsdaten und Katalogabruf für Zwergenladen
===================================================================

WELCHE ZUGANGSDATEN DU BRAUCHST
--------------------------------
Für einen einzelnen eigenen Shop ist der **Admin API Access Token**
(beginnt mit `shpat_`) das Richtige — nicht Client ID und Secret.

  Client ID / Client Secret  →  für den OAuth-Ablauf, wenn eine App auf
                                FREMDEN Shops installiert werden soll.
                                Das Secret dient zusätzlich der
                                Signaturprüfung von Webhooks.

  Admin API Access Token     →  für Zugriff auf den EIGENEN Shop.
                                Kein OAuth nötig, direkt verwendbar.

Da die App nur deinen eigenen Shop liest, reicht der Access Token.

WO DU IHN FINDEST
-----------------
Shopify Admin → Einstellungen → Apps und Vertriebskanäle
  → Apps entwickeln → App „Zwergenladen“
  → API-Zugangsdaten → Admin API Access Token

Benötigte Berechtigung für den Barcode-Abruf:  read_products

WO DU IHN HINTERLEGST
---------------------
Variante A — Streamlit-Secrets (empfohlen):
    Datei `.streamlit/secrets.toml` neben der App anlegen:

        shop_domain  = "zwergenladen.myshopify.com"
        access_token = "shpat_..."

Variante B — Umgebungsvariablen:

        export SHOPIFY_SHOP_DOMAIN="zwergenladen.myshopify.com"
        export SHOPIFY_ACCESS_TOKEN="shpat_..."

Variante C — Eingabe direkt in der App. Gilt nur für die laufende
Sitzung und wird nirgends gespeichert.

Beide Dateien sind über .gitignore vom Repository ausgeschlossen.
Trage den Token NIEMALS direkt in eine Quelldatei ein.
"""

import os
import re

import requests

API_VERSION = "2024-01"
TIMEOUT = 20


# ──────────────────────────────────────────────────────────
# Zugangsdaten einsammeln
# ──────────────────────────────────────────────────────────
def load_credentials(session_override=None):
    """
    Sucht Zugangsdaten in dieser Reihenfolge:
      1. was der Nutzer in der laufenden Sitzung eingegeben hat
      2. Streamlit-Secrets  (.streamlit/secrets.toml)
      3. Umgebungsvariablen

    Rückgabe: (shop_domain, access_token, quelle)
              Fehlende Werte sind None.
    """
    if session_override:
        dom, tok = session_override
        if dom and tok:
            return normalise_domain(dom), tok.strip(), "Sitzungseingabe"

    # Streamlit-Secrets — nur wenn Streamlit läuft und die Datei existiert
    try:
        import streamlit as st
        dom = st.secrets.get("shop_domain")
        tok = st.secrets.get("access_token")
        if dom and tok:
            return normalise_domain(dom), str(tok).strip(), "secrets.toml"
    except Exception:
        pass  # keine Secrets-Datei — kein Fehler, nächste Quelle probieren

    dom = os.environ.get("SHOPIFY_SHOP_DOMAIN")
    tok = os.environ.get("SHOPIFY_ACCESS_TOKEN")
    if dom and tok:
        return normalise_domain(dom), tok.strip(), "Umgebungsvariablen"

    return None, None, None


def normalise_domain(domain: str) -> str:
    """'https://zwergenladen.myshopify.com/' → 'zwergenladen.myshopify.com'"""
    d = domain.strip()
    d = re.sub(r"^https?://", "", d)
    return d.rstrip("/")


def mask(token: str) -> str:
    """Token für die Anzeige unkenntlich machen."""
    if not token or len(token) < 12:
        return "••••"
    return token[:6] + "…" + token[-4:]


# ──────────────────────────────────────────────────────────
# Katalogabruf
# ──────────────────────────────────────────────────────────
def check_access(domain: str, token: str):
    """
    Prüft die Zugangsdaten mit einem billigen Aufruf.
    Rückgabe: (True, shopname) oder (False, fehlermeldung)
    """
    url = f"https://{domain}/admin/api/{API_VERSION}/shop.json"
    try:
        r = requests.get(
            url,
            headers={"X-Shopify-Access-Token": token},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        return False, f"Shop nicht erreichbar ({type(exc).__name__})"

    if r.status_code == 401:
        return False, "Token abgelehnt — abgelaufen oder falsch kopiert"
    if r.status_code == 403:
        return False, "Token gültig, aber Berechtigung read_products fehlt"
    if r.status_code == 404:
        return False, f"Shop-Domain '{domain}' existiert nicht"
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"

    try:
        return True, r.json()["shop"]["name"]
    except (ValueError, KeyError):
        return True, domain


def fetch_barcodes(domain: str, token: str, only_with_barcode=True,
                   progress=None):
    """
    Liest alle Produktvarianten und gibt Barcode-Zeilen zurück.

    Rückgabe: (zeilen, statistik)
      zeilen     — Liste von "barcode | Produktname"
      statistik  — {'produkte':n, 'varianten':n, 'mit_barcode':n, 'ohne':n}

    Wirft nichts — Netzfehler kommen als leeres Ergebnis mit Hinweis zurück.
    """
    headers = {"X-Shopify-Access-Token": token}
    url = (f"https://{domain}/admin/api/{API_VERSION}"
           f"/products.json?limit=250&fields=id,title,variants")

    zeilen = []
    stat = {"produkte": 0, "varianten": 0, "mit_barcode": 0, "ohne": 0,
            "fehler": None}
    seite = 0

    while url:
        seite += 1
        if progress:
            progress(f"Seite {seite} wird gelesen …")

        try:
            r = requests.get(url, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as exc:
            stat["fehler"] = f"Abbruch auf Seite {seite}: {type(exc).__name__}"
            break

        if r.status_code != 200:
            stat["fehler"] = f"Abbruch auf Seite {seite}: HTTP {r.status_code}"
            break

        try:
            produkte = r.json().get("products", [])
        except ValueError:
            stat["fehler"] = f"Ungültige Antwort auf Seite {seite}"
            break

        for p in produkte:
            stat["produkte"] += 1
            titel = (p.get("title") or "").strip()

            for v in p.get("variants", []):
                stat["varianten"] += 1
                code = (v.get("barcode") or "").strip()

                vtitel = (v.get("title") or "").strip()
                if vtitel and vtitel.lower() != "default title":
                    name = f"{titel} — {vtitel}"
                else:
                    name = titel

                if code:
                    stat["mit_barcode"] += 1
                    zeilen.append(f"{code} | {name}")
                else:
                    stat["ohne"] += 1
                    if not only_with_barcode:
                        zeilen.append(f"# OHNE BARCODE: {name}")

        url = next_page_url(r.headers.get("Link", ""))

    return zeilen, stat


# ──────────────────────────────────────────────────────────
# CSV-Import — der Weg ohne Zugangsdaten
# ──────────────────────────────────────────────────────────
def parse_product_csv(datei):
    """
    Liest einen Shopify-Produktexport (CSV) und zieht die Barcodes heraus.

    Export erzeugen:
        Shopify Admin → Produkte → Exportieren
        → „Alle Produkte“ → „CSV für Excel, Numbers…“

    Shopify schreibt den Produkttitel nur in die ERSTE Zeile eines Produkts;
    die weiteren Variantenzeilen lassen ihn leer. Der Titel wird deshalb
    nach unten fortgeschrieben.

    Rückgabe: (zeilen, statistik) — gleiches Format wie fetch_barcodes()
    """
    import csv
    import io

    stat = {"produkte": 0, "varianten": 0, "mit_barcode": 0, "ohne": 0,
            "fehler": None}
    zeilen = []

    # Bytes oder Text entgegennehmen, BOM aus Excel-Exporten entfernen
    roh = datei.read() if hasattr(datei, "read") else datei
    if isinstance(roh, bytes):
        for kodierung in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                roh = roh.decode(kodierung)
                break
            except UnicodeDecodeError:
                continue
        else:
            stat["fehler"] = "Zeichenkodierung nicht erkannt"
            return [], stat

    leser = csv.DictReader(io.StringIO(roh))
    if not leser.fieldnames:
        stat["fehler"] = "Datei ist leer oder keine CSV"
        return [], stat

    # Spalten tolerant suchen — Gross/Kleinschreibung und Leerzeichen egal
    def spalte(*kandidaten):
        norm = {(f or "").strip().lower(): f for f in leser.fieldnames}
        for k in kandidaten:
            if k.lower() in norm:
                return norm[k.lower()]
        return None

    sp_barcode = spalte("Variant Barcode", "Barcode")
    sp_titel   = spalte("Title", "Titel")
    sp_opt     = [spalte(f"Option{i} Value") for i in (1, 2, 3)]

    if not sp_barcode:
        stat["fehler"] = (
            "Spalte „Variant Barcode“ fehlt. Ist das wirklich ein "
            "Shopify-Produktexport?"
        )
        return [], stat

    letzter_titel = ""
    gesehen = set()

    for reihe in leser:
        titel = (reihe.get(sp_titel) or "").strip() if sp_titel else ""
        if titel:
            letzter_titel = titel
            stat["produkte"] += 1
        titel = titel or letzter_titel

        stat["varianten"] += 1
        code = (reihe.get(sp_barcode) or "").strip()

        optionen = [
            (reihe.get(s) or "").strip()
            for s in sp_opt
            if s and (reihe.get(s) or "").strip()
            and (reihe.get(s) or "").strip().lower() != "default title"
        ]
        name = f"{titel} — {' / '.join(optionen)}" if optionen else titel

        if code:
            if code in gesehen:          # Exporte wiederholen Zeilen für Bilder
                continue
            gesehen.add(code)
            stat["mit_barcode"] += 1
            zeilen.append(f"{code} | {name}".strip(" |"))
        else:
            stat["ohne"] += 1

    return zeilen, stat


def next_page_url(link_header: str):
    """Shopify paginiert über den Link-Header mit rel="next"."""
    if not link_header:
        return None
    for teil in link_header.split(","):
        if 'rel="next"' in teil:
            treffer = re.search(r"<([^>]+)>", teil)
            if treffer:
                return treffer.group(1)
    return None

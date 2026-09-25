"""
shopify-kisme-welle2.py
=======================
Aktiviert die 21 KISME-Produkte (Welle 2) im Shopify-Kanal "Google & YouTube".

Voraussetzungen:
  pip install requests

Vor dem ersten Lauf:
  1. ACCESS_TOKEN = "<dein Shopify Admin API Token>" eintragen
  2. DRY_RUN = False setzen, wenn du bereit bist

Wie Shopify-Publikationen funktionieren:
  - Jeder Kanal hat eine `publication_id` (einmalig abfragen, s.u.)
  - POST /admin/api/2024-01/publications/{pub_id}/products.json
    mit {"product": {"id": <product_id>}}
    → macht das Produkt im Kanal sichtbar (= "Publish to channel")

WICHTIG: Dieses Skript läuft lokal auf deiner Maschine.
"""

import requests
import time

# ──────────────────────────────────────────
# Konfiguration
# ──────────────────────────────────────────
SHOP_URL = "zwergenladen.myshopify.com"
API_VERSION = "2024-01"
ACCESS_TOKEN = ""          # TODO: aus 1Password eintragen
DRY_RUN = True             # True = nur anzeigen, nichts schreiben

# ──────────────────────────────────────────
# Welle-2 KISME-Produkte
# (Shopify Produkt-IDs)
# ──────────────────────────────────────────
KISME_PRODUKTE = [
    # Börse Sommerfarben – alle Farbvarianten hängen an dieser Produkt-ID
    {"id": 15912756937077, "name": "Börse Sommerfarben"},

    # Stimmungsketten (7 Produkte)
    {"id": 15912714666357, "name": "Stimmungskette (1)"},
    {"id": 15912714895733, "name": "Stimmungskette (2)"},
    {"id": 15912715026805, "name": "Stimmungskette (3)"},
    {"id": 15912714961269, "name": "Stimmungskette (4)"},
    {"id": 15912715125109, "name": "Stimmungskette (5)"},
    {"id": 15912715190645, "name": "Stimmungskette (6)"},
    {"id": 15912714797429, "name": "Stimmungskette (7)"},

    # Stimmungsring Einhorn
    {"id": 15912756838773, "name": "Stimmungsring Einhorn"},

    # Armbänder (5 Produkte)
    {"id": 15912715223413, "name": "Armband (1)"},
    {"id": 15912715256181, "name": "Armband (2)"},
    {"id": 15912756740469, "name": "Armband (3)"},
    {"id": 15912715288949, "name": "Armband (4)"},
    {"id": 15912715354485, "name": "Armband (5)"},
]

BASE_URL = f"https://{SHOP_URL}/admin/api/{API_VERSION}"
HEADERS = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json",
}


def get_publication_id(channel_title: str = "Google & YouTube") -> str | None:
    """Findet die publication_id des Google-Kanals."""
    url = f"{BASE_URL}/publications.json"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    pubs = r.json().get("publications", [])
    for pub in pubs:
        if channel_title.lower() in pub.get("name", "").lower():
            return pub["id"]
    # Alle Kanäle ausgeben, falls nicht gefunden
    print("Verfügbare Kanäle:")
    for pub in pubs:
        print(f"  ID {pub['id']}: {pub['name']}")
    return None


def publish_product(publication_id: str, product_id: int, name: str) -> bool:
    """Fügt ein Produkt zur Publikation hinzu."""
    url = f"{BASE_URL}/publications/{publication_id}/products.json"
    payload = {"product": {"id": product_id}}

    if DRY_RUN:
        print(f"  [DRY RUN] Würde veröffentlichen: {name} (ID {product_id})")
        return True

    r = requests.post(url, json=payload, headers=HEADERS, timeout=15)
    if r.status_code == 422:
        # Bereits veröffentlicht – kein Fehler
        print(f"  ⏭  Bereits aktiv: {name}")
        return True
    if r.status_code in (200, 201):
        print(f"  ✅ Aktiviert: {name}")
        return True
    print(f"  ❌ Fehler {r.status_code} bei {name}: {r.text[:200]}")
    return False


def main():
    if not ACCESS_TOKEN:
        print("❌ ACCESS_TOKEN fehlt. Bitte in diesem Skript eintragen.")
        return

    if DRY_RUN:
        print("╔══ DRY RUN – es werden keine Änderungen vorgenommen ══╗\n")

    # Schritt 1: Publication-ID ermitteln
    print("Suche Google & YouTube Kanal …")
    pub_id = get_publication_id("Google & YouTube")
    if not pub_id:
        print("❌ Google & YouTube Kanal nicht gefunden.")
        return
    print(f"Publication-ID: {pub_id}\n")

    # Schritt 2: Alle Produkte veröffentlichen
    ok = 0
    for prod in KISME_PRODUKTE:
        success = publish_product(pub_id, prod["id"], prod["name"])
        if success:
            ok += 1
        time.sleep(0.5)   # Rate-Limit schonen

    print(f"\n{'─'*40}")
    print(f"Fertig: {ok}/{len(KISME_PRODUKTE)} Produkte aktiviert")
    if DRY_RUN:
        print("👆 DRY RUN – setze DRY_RUN = False und starte erneut")


if __name__ == "__main__":
    main()

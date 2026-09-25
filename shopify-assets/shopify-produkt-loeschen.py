"""
shopify-produkt-loeschen.py
============================
Löscht ein Shopify-Produkt per Admin API.

Verwendung: Sterne Neon (Produkt-ID 15259386872181) löschen.

Voraussetzungen:
  pip install requests

Vor dem Lauf:
  1. ACCESS_TOKEN eintragen
  2. DRY_RUN = False setzen
  3. Sicherstellen, dass das Produkt wirklich gelöscht werden soll
     (Shopify-Löschung ist NICHT rückgängig zu machen!)

WICHTIG: Dieses Skript läuft lokal auf deiner Maschine.
"""

import requests

# ──────────────────────────────────────────
# Konfiguration
# ──────────────────────────────────────────
SHOP_URL = "zwergenladen.myshopify.com"
API_VERSION = "2024-01"
ACCESS_TOKEN = ""       # TODO: aus 1Password eintragen
DRY_RUN = True          # True = nur anzeigen, NICHT löschen

# ──────────────────────────────────────────
# Zu löschendes Produkt
# ──────────────────────────────────────────
PRODUKT_ID = 15259386872181
PRODUKT_NAME = "Sterne Neon"     # zur Bestätigung

BASE_URL = f"https://{SHOP_URL}/admin/api/{API_VERSION}"
HEADERS = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json",
}


def get_product(product_id: int) -> dict | None:
    """Ruft Produktdetails ab (zur Bestätigung vor dem Löschen)."""
    url = f"{BASE_URL}/products/{product_id}.json"
    r = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code == 404:
        print(f"⚠️  Produkt {product_id} nicht gefunden (bereits gelöscht?).")
        return None
    r.raise_for_status()
    return r.json().get("product", {})


def delete_product(product_id: int) -> bool:
    """Löscht das Produkt endgültig."""
    url = f"{BASE_URL}/products/{product_id}.json"
    r = requests.delete(url, headers=HEADERS, timeout=15)
    if r.status_code == 200:
        return True
    print(f"❌ Fehler {r.status_code}: {r.text[:300]}")
    return False


def main():
    if not ACCESS_TOKEN:
        print("❌ ACCESS_TOKEN fehlt. Bitte in diesem Skript eintragen.")
        return

    print(f"Produkt-ID:    {PRODUKT_ID}")
    print(f"Erwarteter Name: {PRODUKT_NAME}")
    print()

    # Produkt abrufen und bestätigen
    prod = get_product(PRODUKT_ID)
    if prod is None:
        return

    titel = prod.get("title", "?")
    status = prod.get("status", "?")
    varianten = len(prod.get("variants", []))
    print(f"Gefunden:  {titel}")
    print(f"Status:    {status}")
    print(f"Varianten: {varianten}")
    print()

    # Sicherheits-Check: stimmt der Titel überein?
    if PRODUKT_NAME.lower() not in titel.lower():
        print(f"⛔ STOPP – Titel '{titel}' enthält '{PRODUKT_NAME}' NICHT.")
        print("   Bitte Produkt-ID überprüfen. Skript abgebrochen.")
        return

    if DRY_RUN:
        print(f"[DRY RUN] Würde löschen: {titel} (ID {PRODUKT_ID})")
        print("👆 DRY RUN – setze DRY_RUN = False und starte erneut")
        return

    # Bestätigung (bei DRY_RUN=False)
    confirm = input(f"❗ Produkt '{titel}' endgültig löschen? (ja/NEIN): ").strip()
    if confirm.lower() != "ja":
        print("Abgebrochen.")
        return

    print("Lösche …")
    if delete_product(PRODUKT_ID):
        print(f"✅ Produkt '{titel}' (ID {PRODUKT_ID}) erfolgreich gelöscht.")
    else:
        print("❌ Löschen fehlgeschlagen.")


if __name__ == "__main__":
    main()

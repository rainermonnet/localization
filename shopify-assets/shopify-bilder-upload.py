#!/usr/bin/env python3
"""
Shopify Bulk Image Upload – Zwergenladen
========================================
Lädt Produktbilder per Shopify Admin REST API hoch.

Voraussetzungen:
  pip install requests

Verwendung:
  1. SHOP_URL und ACCESS_TOKEN setzen (Custom App mit read/write products Scope)
  2. IMAGES Dictionary mit Product-ID und Bild-URL befüllen
  3. python3 shopify-bilder-upload.py

API-Dokumentation:
  https://shopify.dev/docs/api/admin-rest/2024-01/resources/product-image
"""

import json
import time
import requests

# ─── Konfiguration ─────────────────────────────────────────────────────────────
SHOP_URL      = "zwergenladen.myshopify.com"  # ohne https://
ACCESS_TOKEN  = "shpat_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # Custom App Admin API Token
API_VERSION   = "2024-01"

# ─── Produkte mit fehlenden Bildern ────────────────────────────────────────────
# Format: product_id → {"src": "https://...", "alt": "Beschreibung"}
# Bild-URLs aus Lieferanten-Portalen eintragen, BEVOR das Skript ausgeführt wird.

IMAGES: dict[str, dict] = {
    # 1. Ring (Grapat) – Bild-URL von grapat.com oder Händlerportal eintragen
    "15259381268853": {
        "src": "",  # TODO: z. B. https://grapat.com/.../ring.jpg
        "alt": "Grapat Ring – Mandala Holzspielzeug",
    },
    # 2. Kaufladen Miniaturen, Lebensmittel und Haushaltswaren im Korb (goki 51713)
    "15719930265973": {
        "src": "",  # TODO: z. B. https://goki.eu/media/.../51713.jpg
        "alt": "goki 51713 – Kaufladen Miniaturen Lebensmittel und Haushaltswaren im Korb",
    },
    # 3. HENRYS Eurodisc Frisbee Organic Ultimate Star rot 175g (A03710-03)
    "15923572539765": {
        "src": "",  # TODO: von henrys-online.de oder HENRYS Händlerportal
        "alt": "HENRYS Eurodisc Frisbee Organic Ultimate Star rot 175g – A03710-03",
    },
    # 4. HENRYS Bumerang Jaguar Design Links (A04083)
    "15923572474229": {
        "src": "",  # TODO: von henrys-online.de oder HENRYS Händlerportal
        "alt": "HENRYS Bumerang Jaguar Design Links – A04083",
    },
    # 5. Ostheimer Dalmatiner (10511)
    "15259351777653": {
        "src": "",  # TODO: von ostheimer.de oder holzatelier-lissner.de
        "alt": "Ostheimer Dalmatiner – Traditionelle Holzfigur 10511",
    },
    # 6. HENRYS Eurodisc Frisbee Organic Ultimate Star weiß
    "15923572506997": {
        "src": "",  # TODO: von henrys-online.de oder HENRYS Händlerportal
        "alt": "HENRYS Eurodisc Frisbee Organic Ultimate Star weiß 175g",
    },
    # 7. goki Brummkreisel Farbentanz (53778)
    "15259350925685": {
        "src": "",  # TODO: z. B. https://goki.eu/media/.../53778.jpg
        "alt": "goki Brummkreisel Farbentanz – Bunter Blechkreisel 53778",
    },
    # 8. Tattoo (Grätz Verlag) – erst Produkt im Admin prüfen, welches Motiv!
    "15259388346741": {
        "src": "",  # TODO: von graetz-verlag.de nach Identifikation des Motivs
        "alt": "Grätz Verlag Kindertattoo",
    },
    # 9. Käthe Kruse Buggy Flower (K0179317)
    "15816849326453": {
        "src": "",  # TODO: von kaethe-kruse.de oder Händlerportal
        "alt": "Käthe Kruse Buggy Flower – Puppenwagen K0179317",
    },
}

# ─── Hilfsfunktionen ───────────────────────────────────────────────────────────

def api_headers() -> dict:
    return {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json",
    }


def upload_image(product_id: str, src: str, alt: str) -> dict:
    """Fügt ein Bild zu einem Shopify-Produkt hinzu."""
    url = f"https://{SHOP_URL}/admin/api/{API_VERSION}/products/{product_id}/images.json"
    payload = {"image": {"src": src, "alt": alt}}
    resp = requests.post(url, headers=api_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_product_title(product_id: str) -> str:
    """Gibt den Produktnamen zurück."""
    url = f"https://{SHOP_URL}/admin/api/{API_VERSION}/products/{product_id}.json?fields=title"
    resp = requests.get(url, headers=api_headers(), timeout=15)
    if resp.status_code == 200:
        return resp.json().get("product", {}).get("title", f"Produkt {product_id}")
    return f"Produkt {product_id}"


def validate_config() -> bool:
    """Prüft Pflichtfelder vor der Ausführung."""
    if "XXXXXXXX" in ACCESS_TOKEN:
        print("❌ ACCESS_TOKEN ist noch nicht gesetzt. Bitte anpassen.")
        return False
    missing = [pid for pid, img in IMAGES.items() if not img.get("src")]
    if missing:
        print(f"⚠️  Fehlende Bild-URLs für {len(missing)} Produkte:")
        for pid in missing:
            print(f"   • Produkt-ID {pid}")
        print("   → Bitte src-URLs im IMAGES Dictionary eintragen, dann erneut ausführen.")
        return False
    return True


# ─── Hauptprogramm ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Shopify Bulk Image Upload – Zwergenladen")
    print("=" * 60)

    if not validate_config():
        return

    results = []
    for product_id, image_data in IMAGES.items():
        src = image_data.get("src", "")
        alt = image_data.get("alt", "")

        if not src:
            print(f"⏭  {product_id}: übersprungen (keine src-URL)")
            continue

        title = get_product_title(product_id)
        print(f"\n📦 {title} (ID: {product_id})")
        print(f"   URL: {src[:80]}...")

        try:
            result = upload_image(product_id, src, alt)
            image_id = result.get("image", {}).get("id", "?")
            print(f"   ✅ Hochgeladen – Bild-ID: {image_id}")
            results.append({"product_id": product_id, "title": title, "status": "OK", "image_id": image_id})
        except requests.exceptions.HTTPError as e:
            print(f"   ❌ Fehler: {e.response.status_code} – {e.response.text[:200]}")
            results.append({"product_id": product_id, "title": title, "status": "ERROR", "error": str(e)})
        except Exception as e:
            print(f"   ❌ Unerwarteter Fehler: {e}")
            results.append({"product_id": product_id, "title": title, "status": "ERROR", "error": str(e)})

        # Rate-Limit: Shopify erlaubt 2 Anfragen/Sekunde (Leaky Bucket)
        time.sleep(0.6)

    print("\n" + "=" * 60)
    print(f"  Fertig: {sum(1 for r in results if r['status'] == 'OK')}/{len(results)} erfolgreich")
    print("=" * 60)

    # Ergebnis speichern
    output_file = "upload-ergebnis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📄 Ergebnis gespeichert in: {output_file}")


if __name__ == "__main__":
    main()

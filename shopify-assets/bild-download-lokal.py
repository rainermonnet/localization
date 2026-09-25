#!/usr/bin/env python3
"""
Bild-Downloader & Shopify-Uploader – lokal ausführen (kein Proxy)
==================================================================
Dieses Skript auf deinem eigenen Rechner ausführen (nicht im Server).

Voraussetzungen:
  pip install requests playwright
  playwright install chromium

Verwendung:
  python3 bild-download-lokal.py

Was es tut:
  1. Öffnet die Hersteller-Produktseiten mit Playwright
  2. Extrahiert das Hauptproduktbild (größtes Bild ≥ 500px)
  3. Speichert es lokal unter ./downloaded-images/
  4. Optional: lädt es direkt per Shopify Admin API hoch

Danach: Bilder manuell über Shopify Admin hochladen oder
        ACCESS_TOKEN setzen und UPLOAD_TO_SHOPIFY = True
"""

import os, re, time, urllib.parse
from pathlib import Path
from playwright.sync_api import sync_playwright
import requests

# ─── Konfiguration ────────────────────────────────────────────────────────────
SHOP_URL         = "zwergenladen.myshopify.com"
ACCESS_TOKEN     = ""              # Shopify Admin API Token – leer lassen für nur Download
UPLOAD_TO_SHOPIFY = False          # True: direkt hochladen; False: nur herunterladen
OUTPUT_DIR       = Path("./downloaded-images")
API_VERSION      = "2024-01"

# ─── Produkte ─────────────────────────────────────────────────────────────────
PRODUCTS = [
    {
        "shopify_id": "15259381268853",
        "name": "Ring (Grapat)",
        "url": "https://grapat.com/en/product/rings/",
        "alt": "Grapat Ring – Mandala Holzspielzeug",
        "filename": "grapat-ring.jpg",
    },
    {
        "shopify_id": "15719930265973",
        "name": "Kaufladen Miniaturen (goki 51713)",
        "url": "https://goki.eu/en/toy-shop-miniatures-in-a-basket-food-and-household-goods/item-1-51713.html",
        "alt": "goki 51713 – Kaufladen Miniaturen Lebensmittel im Korb",
        "filename": "goki-51713-kaufladen-miniaturen.jpg",
    },
    {
        "shopify_id": "15923572539765",
        "name": "HENRYS Eurodisc rot (A03710-03)",
        "url": "https://www.henrys-online.de/Frisbee-Eurodisc-175g-Organic-Ultimate-Star-rot/A03710-03",
        "alt": "HENRYS Eurodisc Frisbee Organic Ultimate Star rot 175g",
        "filename": "henrys-eurodisc-rot-a03710-03.jpg",
    },
    {
        "shopify_id": "15923572506997",
        "name": "HENRYS Eurodisc weiß",
        "url": "https://www.henrys-online.de/shop/activity/aerobies-frisbees/",
        "alt": "HENRYS Eurodisc Frisbee Organic Ultimate Star weiß 175g",
        "filename": "henrys-eurodisc-weiss.jpg",
        "note": "Auf der Seite nach dem weißen Star-Modell suchen",
    },
    {
        "shopify_id": "15923572474229",
        "name": "HENRYS Bumerang Jaguar Links (A04083)",
        "url": "https://www.henrys-online.de/Bumerang-Jaguar-Ori-Links/A04083",
        "alt": "HENRYS Bumerang Jaguar Design Links A04083",
        "filename": "henrys-bumerang-jaguar-links-a04083.jpg",
    },
    {
        "shopify_id": "15259351777653",
        "name": "Ostheimer Dalmatiner (10511)",
        "url": "https://www.ostheimer.de/en/ostheimer-toys/dalmatian",
        "alt": "Ostheimer Dalmatiner – Traditionelle Holzfigur 10511",
        "filename": "ostheimer-dalmatiner-10511.jpg",
    },
    {
        "shopify_id": "15259350925685",
        "name": "goki Brummkreisel Farbentanz (53778)",
        "url": "https://goki.eu/en/humming-top-colour-dance/item-1-53778.html",
        "alt": "goki Brummkreisel Farbentanz – Bunter Blechkreisel 53778",
        "filename": "goki-53778-brummkreisel.jpg",
    },
    {
        "shopify_id": "15259388346741",
        "name": "Tattoo (Grätz Verlag – Motiv im Admin prüfen!)",
        "url": "https://www.graetz-verlag.de/tattoos",
        "alt": "Grätz Verlag Kindertattoo",
        "filename": "graetz-tattoo.jpg",
        "note": "Erst Shopify Admin öffnen → Produkt 15259388346741 → Motiv/Artikelnummer prüfen → URL anpassen",
    },
    {
        "shopify_id": "15816849326453",
        "name": "Käthe Kruse Buggy Flower (K0179317)",
        "url": "https://kaethe-kruse.de/de/buggy-flower-k0179317",
        "alt": "Käthe Kruse Buggy Flower – Puppenwagen K0179317",
        "filename": "kaethe-kruse-buggy-flower-k0179317.jpg",
    },
]

JS_EXTRACT = """
() => {
    const results = [];
    for (const img of document.querySelectorAll('img')) {
        const src = img.currentSrc || img.src
            || img.getAttribute('data-src') || img.getAttribute('data-lazy-src')
            || img.getAttribute('data-original') || '';
        if (!src || src.startsWith('data:')) continue;
        results.push({src, w: img.naturalWidth, h: img.naturalHeight, alt: img.alt || ''});
    }
    // Also check source elements (picture/srcset)
    for (const s of document.querySelectorAll('source')) {
        const srcset = s.getAttribute('srcset') || '';
        const src = srcset.split(',')[0].trim().split(' ')[0];
        if (src && !src.startsWith('data:')) results.push({src, w: 0, h: 0, alt: 'srcset'});
    }
    return results;
}
"""


def best_image(imgs):
    """Return the largest product image URL."""
    product_imgs = [
        img for img in imgs
        if img.get('src')
        and not img['src'].startswith('data:')
        and re.search(r'\.(jpg|jpeg|png|webp)', img['src'], re.I)
        and img.get('w', 0) >= 100  # skip tiny icons
    ]
    if not product_imgs:
        return None
    return max(product_imgs, key=lambda x: x.get('w', 0) * x.get('h', 0)).get('src')


def download_image(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        dest.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"    ⚠️  Download-Fehler: {e}")
        return False


def upload_to_shopify(product_id: str, image_path: Path, alt: str) -> bool:
    if not ACCESS_TOKEN:
        print("    ⚠️  ACCESS_TOKEN nicht gesetzt – Upload übersprungen")
        return False
    url = f"https://{SHOP_URL}/admin/api/{API_VERSION}/products/{product_id}/images.json"
    # Upload via multipart or src URL
    import base64
    data = base64.b64encode(image_path.read_bytes()).decode()
    ext = image_path.suffix.lstrip('.')
    payload = {"image": {"attachment": data, "filename": image_path.name, "alt": alt}}
    r = requests.post(url, json=payload, headers={
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json",
    }, timeout=60)
    if r.status_code in (200, 201):
        img_id = r.json().get("image", {}).get("id", "?")
        print(f"    ✅ Shopify: Bild-ID {img_id}")
        return True
    else:
        print(f"    ❌ Shopify API Fehler {r.status_code}: {r.text[:200]}")
        return False


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for prod in PRODUCTS:
            print(f"\n{'='*60}")
            print(f"📦 {prod['name']}")
            if prod.get('note'):
                print(f"   ⚠️  {prod['note']}")

            dest = OUTPUT_DIR / prod['filename']
            if dest.exists():
                print(f"   ✅ Schon vorhanden: {dest}")
                img_url = str(dest)
            else:
                try:
                    page.goto(prod['url'], wait_until='domcontentloaded', timeout=20000)
                    page.wait_for_timeout(1500)
                    imgs = page.evaluate(JS_EXTRACT)
                    img_url = best_image(imgs)
                    if img_url:
                        print(f"   🖼  Bild gefunden: {img_url[:100]}")
                        if download_image(img_url, dest):
                            print(f"   💾 Gespeichert: {dest}")
                        else:
                            img_url = None
                    else:
                        print(f"   ❌ Kein Produktbild gefunden – URL manuell prüfen: {prod['url']}")
                except Exception as e:
                    print(f"   ❌ Fehler beim Laden der Seite: {e}")
                    img_url = None

            if img_url and UPLOAD_TO_SHOPIFY and dest.exists():
                upload_to_shopify(prod['shopify_id'], dest, prod['alt'])
                time.sleep(0.7)

            results.append({
                "shopify_id": prod['shopify_id'],
                "name": prod['name'],
                "local_file": str(dest) if dest.exists() else None,
                "image_url": img_url,
            })

        browser.close()

    # Summary
    print(f"\n{'='*60}")
    ok = sum(1 for r in results if r['local_file'])
    print(f"✅ {ok}/{len(results)} Bilder heruntergeladen → {OUTPUT_DIR}/")
    print("Nächste Schritte:")
    print("  1. Bilder in ./downloaded-images/ prüfen")
    print("  2. ACCESS_TOKEN setzen und UPLOAD_TO_SHOPIFY = True")
    print("  3. Skript erneut ausführen für automatischen Upload")
    print("  ODER: Bilder manuell im Shopify Admin hochladen")


if __name__ == "__main__":
    main()

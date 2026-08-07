#!/usr/bin/env python3
"""
KISME Händlerportal – Produkt-Bilder scrapen
=============================================
Loggt sich in shop.click-kisme.com ein, sucht die KISME-Produkte
und lädt die Produktbilder herunter.

Voraussetzungen:
  pip install playwright requests
  playwright install chromium

Verwendung:
  1. PASSWORD eintragen (aus 1Password: monnet@zwergenladen.info)
  2. python3 kisme-bilder-scrapen.py

Was es tut:
  1. Login auf shop.click-kisme.com
  2. Suche nach jedem KISME-Produkt anhand des Namens
  3. Download des größten Produktbildes → ./downloaded-images/kisme-*.jpg
  4. Optional: direkter Upload zu Shopify (ACCESS_TOKEN setzen)

Shopify-Produkt-IDs sind vorbelegt – nach Download einfach
shopify-bilder-upload.py mit den src-Pfaden ausführen.
"""

import os, re, time, json
from pathlib import Path
from playwright.sync_api import sync_playwright
import requests

# ─── Credentials ──────────────────────────────────────────────────────────────
KISME_USER     = "monnet@zwergenladen.info"
KISME_PASS     = ""        # TODO: aus 1Password eintragen
KISME_LOGIN    = "https://shop.click-kisme.com/account"

SHOP_URL       = "zwergenladen.myshopify.com"
ACCESS_TOKEN   = ""        # Shopify Admin Token – leer = nur Download
API_VERSION    = "2024-01"
UPLOAD         = False     # True = direkt zu Shopify hochladen
OUTPUT_DIR     = Path("./downloaded-images")

# ─── KISME-Produkte (Shopify-IDs aus Google MC Export) ───────────────────────
# Format: (shopify_product_id, shopify_variant_id, suchbegriff_kisme, dateiname)
KISME_PRODUCTS = [
    # Stimmungsketten
    ("15912714666357", "57303374463349", "Stimmungskette Einhornkopf",        "kisme-stimmungskette-einhornkopf.jpg"),
    ("15912714895733", "57303374758261", "Stimmungskette Donut",               "kisme-stimmungskette-donut.jpg"),
    ("15912715026805", "57303374889333", "Stimmungskette Gecko",               "kisme-stimmungskette-gecko.jpg"),
    ("15912714961269", "57303374823797", "Stimmungskette Pferd",               "kisme-stimmungskette-pferd.jpg"),
    ("15912715125109", "57303375315317", "Stimmungskette Kreuz",               "kisme-stimmungskette-kreuz.jpg"),
    ("15912715190645", "57303375380853", "Stimmungskette Yin Yang",            "kisme-stimmungskette-yinyang.jpg"),
    ("15912714797429", "57303374659957", "Stimmungskette Einhorn springend",   "kisme-stimmungskette-einhorn-springend.jpg"),
    # Stimmungsring
    ("15912756838773", "57303428661621", "Stimmungsring Einhorn",              "kisme-stimmungsring-einhorn.jpg"),
    # Börsen (Sommerfarben) – gleiche Shopify Produkt-ID, verschiedene Varianten
    ("15912756937077", "57318869565813", "Börse Sommerfarben Gelb",            "kisme-boerse-sommerfarben-gelb.jpg"),
    ("15912756937077", "57318870057333", "Börse Sommerfarben Lila",            "kisme-boerse-sommerfarben-lila.jpg"),
    ("15912756937077", "57318868975989", "Börse Sommerfarben Orange",          "kisme-boerse-sommerfarben-orange.jpg"),
    ("15912756937077", "57318869762421", "Börse Sommerfarben Beige",           "kisme-boerse-sommerfarben-beige.jpg"),
    ("15912756937077", "57318872088949", "Börse Sommerfarben Hellblau",        "kisme-boerse-sommerfarben-hellblau.jpg"),
    ("15912756937077", "57318872482165", "Börse Sommerfarben Hellgrün",        "kisme-boerse-sommerfarben-hellgruen.jpg"),
    ("15912756937077", "57318871990645", "Börse Sommerfarben Rosa",            "kisme-boerse-sommerfarben-rosa.jpg"),
    # Armbänder
    ("15912715223413", "57303375479157", "Armband Glasperlen blau Metallperle","kisme-armband-glasperlen-blau.jpg"),
    ("15912715256181", "57303375511925", "Armband Süßwasserperle orange rot",  "kisme-armband-susswasser-orange-rot.jpg"),
    ("15912756740469", "57303428563317", "Armband Deep Glow rot",              "kisme-armband-deepglow-rot.jpg"),
    ("15912715288949", "57303375544693", "Armband Süßwasserperle rot marmoriert","kisme-armband-susswasser-rot-marmoriert.jpg"),
    ("15912715354485", "57303375610229", "Armband Süßwasserperle rot orange",  "kisme-armband-susswasser-rot-orange.jpg"),
]

JS_IMGS = """
() => {
    const out = [];
    for (const img of document.querySelectorAll('img')) {
        const src = img.currentSrc || img.src
            || img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || '';
        if (!src || src.startsWith('data:')) continue;
        out.push({src, w: img.naturalWidth, h: img.naturalHeight, alt: img.alt||''});
    }
    return out;
}
"""

def best_image(imgs, min_px=150):
    candidates = [
        i for i in imgs
        if i.get('w', 0) >= min_px and i.get('h', 0) >= min_px
        and re.search(r'\.(jpe?g|png|webp)', i['src'], re.I)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda x: x['w'] * x['h'])['src']

def save_image(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        dest.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"    Download-Fehler: {e}")
        return False

def upload_shopify(product_id, variant_id, image_path, alt):
    if not ACCESS_TOKEN:
        return False
    import base64
    url = f"https://{SHOP_URL}/admin/api/{API_VERSION}/products/{product_id}/images.json"
    payload = {"image": {
        "attachment": base64.b64encode(image_path.read_bytes()).decode(),
        "filename": image_path.name,
        "alt": alt,
        "variant_ids": [int(variant_id)],
    }}
    r = requests.post(url, json=payload, headers={
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json",
    }, timeout=60)
    if r.status_code in (200, 201):
        print(f"    ✅ Shopify-Upload: Bild-ID {r.json().get('image',{}).get('id')}")
        return True
    print(f"    ❌ Shopify-Fehler {r.status_code}: {r.text[:200]}")
    return False

def login(page):
    print(f"🔐 Login auf {KISME_LOGIN}")
    page.goto(KISME_LOGIN, wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(1500)

    # Versuche Standard-Login-Formular-Felder
    for email_sel in ['input[type="email"]', 'input[name="email"]', 'input[name="username"]', '#email']:
        if page.locator(email_sel).count() > 0:
            page.fill(email_sel, KISME_USER)
            break

    for pass_sel in ['input[type="password"]', 'input[name="password"]', '#password']:
        if page.locator(pass_sel).count() > 0:
            page.fill(pass_sel, KISME_PASS)
            break

    for btn_sel in ['button[type="submit"]', 'input[type="submit"]', 'button:has-text("Login")',
                    'button:has-text("Anmelden")', 'button:has-text("Sign in")']:
        if page.locator(btn_sel).count() > 0:
            page.click(btn_sel)
            break

    page.wait_for_timeout(3000)
    url = page.url
    print(f"   → Aktuelle URL nach Login: {url}")
    return "account" in url or "dashboard" in url or "catalog" in url

def search_product(page, search_term):
    """Sucht ein Produkt auf der Portal-Seite."""
    current_url = page.url

    # Versuche Suchfeld
    for sel in ['input[type="search"]', 'input[name="q"]', 'input[name="search"]',
                'input[placeholder*="Such"]', 'input[placeholder*="search"]']:
        if page.locator(sel).count() > 0:
            page.fill(sel, search_term)
            page.keyboard.press("Enter")
            page.wait_for_timeout(2000)
            return True

    # Fallback: URL-basierte Suche
    base = current_url.split('?')[0].rstrip('/')
    for search_url in [
        f"{base}?search={search_term}",
        f"{base}?q={search_term}",
        "https://shop.click-kisme.com/search?q=" + search_term.replace(' ', '+'),
    ]:
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=10000)
            page.wait_for_timeout(1500)
            return True
        except:
            pass
    return False

def main():
    if not KISME_PASS:
        print("❌ KISME_PASS ist leer. Bitte Passwort aus 1Password eintragen.")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=False zum Debuggen
        page = browser.new_page()

        # Login
        logged_in = login(page)
        if not logged_in:
            print("⚠️  Login evtl. fehlgeschlagen – Portal-Struktur manuell prüfen")
            print("   Aktueller Seiteninhalt:")
            print(page.content()[:500])

        # Screenshot nach Login
        page.screenshot(path=str(OUTPUT_DIR / "01_nach_login.png"))
        print(f"   Screenshot: {OUTPUT_DIR}/01_nach_login.png")

        # Katalog-Seite suchen
        for catalog_url in [
            "https://shop.click-kisme.com/catalog",
            "https://shop.click-kisme.com/products",
            "https://shop.click-kisme.com/shop",
            "https://shop.click-kisme.com/",
        ]:
            try:
                page.goto(catalog_url, wait_until="domcontentloaded", timeout=10000)
                page.wait_for_timeout(1000)
                if page.url != KISME_LOGIN:
                    print(f"   ✅ Katalog gefunden: {page.url}")
                    break
            except:
                pass

        page.screenshot(path=str(OUTPUT_DIR / "02_katalog.png"))

        # Jedes Produkt suchen und Bild herunterladen
        for prod_id, var_id, search_term, filename in KISME_PRODUCTS:
            dest = OUTPUT_DIR / filename
            print(f"\n{'─'*55}")
            print(f"🔍 {search_term}")

            if dest.exists():
                print(f"   ✅ Schon vorhanden: {dest}")
                results.append({"name": search_term, "file": str(dest), "status": "exists"})
                continue

            search_product(page, search_term)
            imgs = page.evaluate(JS_IMGS)
            img_url = best_image(imgs)

            if img_url:
                print(f"   🖼  {img_url[:80]}")
                if save_image(img_url, dest):
                    print(f"   💾 {dest}")
                    if UPLOAD and ACCESS_TOKEN:
                        upload_shopify(prod_id, var_id, dest, search_term)
                        time.sleep(0.7)
                    results.append({"name": search_term, "file": str(dest), "status": "OK"})
                else:
                    results.append({"name": search_term, "file": None, "status": "download_failed"})
            else:
                print(f"   ❌ Kein Bild gefunden")
                page.screenshot(path=str(OUTPUT_DIR / f"debug_{filename}.png"))
                results.append({"name": search_term, "file": None, "status": "not_found"})

        browser.close()

    # Zusammenfassung
    ok = sum(1 for r in results if r["status"] in ("OK", "exists"))
    print(f"\n{'='*55}")
    print(f"Fertig: {ok}/{len(results)} Bilder → {OUTPUT_DIR}/")
    with open(OUTPUT_DIR / "kisme-ergebnis.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Shopify Sale-Preise setzen – Zwergenladen
==========================================
Setzt compare_at_price (Streichpreis) = aktueller Preis
und price (Aktionspreis) = vorgeschlagener Preis
für 16 Produkte aus dem Google-Merchant-Center-Export
"Vorgeschlagene Sonderangebotspreise" (Wirksamkeit: Hoch).

Voraussetzungen:
  pip install requests

Verwendung:
  1. ACCESS_TOKEN eintragen (Custom App, Scope: write_products)
  2. DRY_RUN = False setzen wenn bereit
  3. python3 shopify-salepreise-setzen.py

Rückgängig machen:
  DRY_RUN = False, dann REVERT = True setzen
  → setzt price = compare_at_price und compare_at_price = None
"""

import json
import time
import requests

# ─── Konfiguration ─────────────────────────────────────────────────────────────
SHOP_URL      = "zwergenladen.myshopify.com"
ACCESS_TOKEN  = "shpat_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # TODO: eintragen
API_VERSION   = "2024-01"
DRY_RUN       = True    # True = nur ausgeben, nichts ändern
REVERT        = False   # True = Preissenkung rückgängig machen

# ─── Produkte (aus Google MC Export, Wirksamkeit: Hoch) ────────────────────────
# Format: (variant_id, product_title, aktueller_preis, vorgeschlagener_preis)
PRODUCTS = [
    ("56179284443509", "Grimms Scheibenturm",                          35.50, 28.40),
    ("55752491794805", "Grimms Große Stufenzählstäbe 4x4 cm",         119.50, 95.60),
    ("56143070855541", "Grimms Regenbogen Babyroller",                  39.50, 31.60),
    ("56176367010165", "Grimms Kleines Glitzermandala",                124.50, 99.60),
    ("55752457159029", "Nanchen Puppe Pimpel hellblau",                 21.50, 18.06),
    ("56138769826165", "Grapat 36 Ringe in 6 Grundfarben",             19.50, 15.60),
    ("56146314854773", "Grimms Biegepüppchen Frau Erle",               35.50, 28.40),
    ("55752436810101", "Ostheimer Heuwagen",                            88.50, 70.80),
    ("55752416264565", "Grapat Dear Universe Planetensystem",           46.50, 37.20),
    ("55752445886837", "Ostheimer Krippenstall mit Stern",             189.50,151.60),
    ("57191919223157", "Grapat 7 Monde Wochenkalender",                 46.15, 36.92),
    ("55752460665205", "Grimms Biegepüppchen Lena",                    35.50, 28.40),
    ("55752464499061", "Grapat 36 Ringe in 6 Komplementärfarben",      22.50, 18.00),
    ("55752446804341", "Grapat 6 bunte Holzkugeln",                    12.50, 10.00),
    ("55752410988917", "Ostheimer Blumenelfen Mobile",                  67.50, 54.00),
    ("56146257248629", "Grimms Biegepüppchen Ida",                     35.50, 28.40),
]

# ─── Hilfsfunktionen ───────────────────────────────────────────────────────────

def api_headers():
    return {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json",
    }


def update_variant(variant_id: str, price: float, compare_at_price):
    """Aktualisiert Preis und Vergleichspreis einer Variante."""
    url = f"https://{SHOP_URL}/admin/api/{API_VERSION}/variants/{variant_id}.json"
    payload = {
        "variant": {
            "id": int(variant_id),
            "price": f"{price:.2f}",
            "compare_at_price": f"{compare_at_price:.2f}" if compare_at_price else None,
        }
    }
    resp = requests.put(url, headers=api_headers(), json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json().get("variant", {})


# ─── Hauptprogramm ─────────────────────────────────────────────────────────────

def main():
    mode = "REVERT" if REVERT else "SALE"
    dry = " [DRY RUN]" if DRY_RUN else ""

    print("=" * 65)
    print(f"  Shopify Preisupdate – {mode}{dry}")
    print(f"  {len(PRODUCTS)} Produkte | Zwergenladen")
    print("=" * 65)

    if "XXXXXXXX" in ACCESS_TOKEN:
        print("\n❌ ACCESS_TOKEN ist noch nicht gesetzt. Bitte anpassen.")
        return

    results = []
    for variant_id, title, orig_price, sale_price in PRODUCTS:
        if REVERT:
            new_price = orig_price
            new_compare = None
            label = f"€{sale_price:.2f} → €{orig_price:.2f} (Streichpreis entfernen)"
        else:
            new_price = sale_price
            new_compare = orig_price
            disc = (1 - sale_price / orig_price) * 100
            label = f"€{orig_price:.2f} → €{sale_price:.2f} (-{disc:.0f}%)"

        print(f"\n  {title[:52]:<52}")
        print(f"  Variante {variant_id}  |  {label}")

        if DRY_RUN:
            print("  → [trockenläuf] keine Änderung")
            results.append({"variant": variant_id, "title": title, "status": "DRY_RUN"})
            continue

        try:
            updated = update_variant(variant_id, new_price, new_compare)
            actual_price = updated.get("price", "?")
            actual_cat = updated.get("compare_at_price", "–")
            print(f"  ✅ Gesetzt: price={actual_price}  compare_at={actual_cat}")
            results.append({"variant": variant_id, "title": title, "status": "OK",
                             "price": actual_price, "compare_at": actual_cat})
        except requests.HTTPError as e:
            print(f"  ❌ API-Fehler {e.response.status_code}: {e.response.text[:200]}")
            results.append({"variant": variant_id, "title": title, "status": "ERROR"})
        except Exception as e:
            print(f"  ❌ Fehler: {e}")
            results.append({"variant": variant_id, "title": title, "status": "ERROR"})

        time.sleep(0.5)  # Shopify Rate Limit (2 req/s)

    # Zusammenfassung
    print("\n" + "=" * 65)
    ok = sum(1 for r in results if r["status"] == "OK")
    print(f"  Ergebnis: {ok}/{len(results)} erfolgreich")
    if not DRY_RUN:
        with open("salepreise-ergebnis.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("  Protokoll: salepreise-ergebnis.json")
    print("=" * 65)


if __name__ == "__main__":
    main()

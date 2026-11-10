"""
ausverkauft-pruefen.py — warum ausverkaufte Produkte im Shop stehen
=====================================================================

Im Onlineshop erscheinen Produkte mit „Ausverkauft". Früher waren sie
ausgeblendet. Dieses Skript sammelt die Fakten, bevor irgendwo etwas
umgestellt wird.

WO SO ETWAS ÜBERHAUPT EINGESTELLT SEIN KANN
--------------------------------------------
1. THEME-EINSTELLUNG. Die meisten Themes haben im Produktraster einen
   Schalter „Ausverkaufte Produkte ausblenden". Die Einstellung gehört
   zum Theme, nicht zum Shop — nach einem Theme-Wechsel ist sie weg.
   Das lässt sich von hier nicht auslesen (braucht read_themes), aber
   es ist nach einem Wechsel die wahrscheinlichste Ursache.

2. AUTOMATISCHE KATEGORIE mit der Bedingung „Lagerbestand größer als 0".
   Das kann dieses Skript lesen und zeigt es unten an.

3. PRODUKT AUS DEM VERKAUFSKANAL GENOMMEN. Wirkt sofort, kostet aber
   die Platzierung bei Google und die Nachfrage-Signale. Wird hier nur
   gezählt, nicht geändert.

WAS DAGEGEN SPRICHT, ALLE AUSZUBLENDEN
---------------------------------------
Ausverkaufte Artikel mit Klickhistorie sind belegte Nachfrage. Verstecken
heißt: Google verliert die Seite, die Platzierung fällt, und wenn die
Ware wiederkommt, fängt sie von vorn an. Bei Dauerartikeln lohnt eher
ein Hinweis „bald wieder da" als das Ausblenden. Bei Einzelstücken, die
nie wiederkommen, ist Ausblenden richtig.

Deshalb trennt die Auswertung beides: wiederbeschaffbar oder nicht.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 ausverkauft-pruefen.py

Nur Lesezugriff. Es wird nichts geändert.
"""

import csv
import sys
import time
from collections import Counter

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

PRODUKTE = """
query($cursor: String) {
  products(first: 50, after: $cursor, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        handle
        title
        vendor
        totalInventory
        tracksInventory
        resourcePublicationsV2(first: 10) {
          edges { node { isPublished publication { name } } }
        }
        variants(first: 50) {
          edges { node { inventoryQuantity inventoryPolicy } }
        }
      }
    }
  }
}
"""

KATEGORIEN = """
query($cursor: String) {
  collections(first: 50, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        title
        handle
        productsCount { count }
        ruleSet { appliedDisjunctively rules { column relation condition } }
      }
    }
  }
}
"""


def kurz(gid):
    return gid.rsplit("/", 1)[-1] if gid else ""


def seiten(abfrage, feld):
    cursor = None
    while True:
        for versuch in range(5):
            a = shopify_http.execute(abfrage, {"cursor": cursor})
            f = str(a.get("_error", ""))
            if not f:
                break
            if "THROTTLED" in f.upper() and versuch < 4:
                time.sleep(2 ** versuch)
                continue
            sys.exit(f"{feld} nicht lesbar: {f}")
        block = a.get(feld, {})
        for k in block.get("edges", []):
            yield k["node"]
        if not block.get("pageInfo", {}).get("hasNextPage"):
            return
        cursor = block["pageInfo"]["endCursor"]
        time.sleep(0.2)


def main():
    print("Lese Katalog …")
    im_shop, leer, weiterverkauf = [], [], []
    gesamt = 0
    for p in seiten(PRODUKTE, "products"):
        gesamt += 1
        kanaele = [(k["node"]["publication"] or {}).get("name", "")
                   for k in p.get("resourcePublicationsV2", {}).get("edges", [])
                   if k["node"].get("isPublished")]
        sichtbar = any("online" in k.lower() for k in kanaele)
        if not sichtbar:
            continue
        im_shop.append(p)
        bestand = p.get("totalInventory")
        if p.get("tracksInventory") and (bestand is None or bestand <= 0):
            leer.append(p)
            politik = {(v["node"].get("inventoryPolicy") or "")
                       for v in p.get("variants", {}).get("edges", [])}
            if "CONTINUE" in politik:
                weiterverkauf.append(p)

    print(f"\n{gesamt} aktive Produkte · {len(im_shop)} im Onlineshop sichtbar")
    print(f"{len(leer)} davon ausverkauft — das sind die mit dem Badge"
          f" ({len(leer)/max(1,len(im_shop)):.0%} der Shopseiten)")
    if weiterverkauf:
        print(f"{len(weiterverkauf)} davon auf „Weiterverkauf bei 0 Bestand“ —")
        print("   die zeigen KEIN Ausverkauft-Badge und sind bestellbar.")

    if leer:
        nach_marke = Counter((p.get("vendor") or "—").strip() for p in leer)
        print("\nAUSVERKAUFT NACH MARKE")
        for marke, n in nach_marke.most_common(12):
            print(f"  {n:>4}  {marke}")

    print("\nLese Kategorien …")
    kategorien = list(seiten(KATEGORIEN, "collections"))
    automatisch = [c for c in kategorien if c.get("ruleSet")]
    print(f"{len(kategorien)} Kategorien · {len(automatisch)} automatisch")

    mit_bestand = []
    for c in automatisch:
        regeln = (c["ruleSet"] or {}).get("rules") or []
        if any("INVENTORY" in (r.get("column") or "").upper() for r in regeln):
            mit_bestand.append(c)

    if mit_bestand:
        print(f"\n{len(mit_bestand)} Kategorien filtern bereits nach Bestand:")
        for c in mit_bestand:
            print(f"  {c['title']}  ({c['productsCount']['count']} Produkte)")
            for r in (c["ruleSet"] or {}).get("rules") or []:
                print(f"      {r['column']} {r['relation']} {r['condition']}")
    else:
        print("\nKeine einzige automatische Kategorie filtert nach Bestand.")
        print("Die Ursache liegt also nicht bei den Kategorien.")

    if automatisch:
        print("\nAUTOMATISCHE KATEGORIEN UND IHRE REGELN")
        for c in automatisch[:15]:
            regeln = (c["ruleSet"] or {}).get("rules") or []
            verknuepft = "ODER" if (c["ruleSet"] or {}).get("appliedDisjunctively") else "UND"
            print(f"  {c['title'][:40]:<40} {c['productsCount']['count']:>4} Prod. "
                  f"({verknuepft})")
            for r in regeln[:4]:
                print(f"      {r['column']} {r['relation']} {r['condition']}")
        if len(automatisch) > 15:
            print(f"  … und {len(automatisch)-15} weitere")

    hand = [c for c in kategorien if not c.get("ruleSet")]
    if hand:
        print(f"\n{len(hand)} Kategorien sind von Hand gepflegt — bei denen")
        print("hilft keine Bestandsregel, dort muss das Theme ausblenden.")

    if leer:
        with open("ausverkauft-im-shop.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Produkt-ID", "Marke", "Titel", "Bestand", "Handle"])
            for p in sorted(leer, key=lambda x: (x.get("vendor") or "", x["title"])):
                w.writerow([kurz(p["id"]), p.get("vendor", ""), p["title"],
                            p.get("totalInventory"), p["handle"]])
        print("\nGeschrieben: ausverkauft-im-shop.csv")

    print("\n" + "=" * 70)
    print("WO DU NACHSEHEN MUSST")
    print("=" * 70)
    print("Online-Shop → Themes → beim aktiven Theme auf „Anpassen“.")
    print("Dort die Kategorieseite öffnen und im Abschnitt mit dem")
    print("Produktraster nach einem Schalter zum Ausblenden ausverkaufter")
    print("Produkte suchen. Wie er genau heißt, hängt vom Theme ab —")
    print("ich kann die Theme-Einstellungen von hier nicht lesen.")
    print("\nFindest du keinen, schick einen Screenshot der Einstellungen")
    print("dieses Abschnitts. Raten hilft hier niemandem.")


if __name__ == "__main__":
    main()

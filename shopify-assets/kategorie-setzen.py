"""
kategorie-setzen.py — Produktkategorie nachtragen
===================================================

719 von 800 Varianten im Google-Feed haben keine Produktkategorie,
darunter 205 von 206 Ostheimer-Artikeln. Die Kategorie steuert, welche
Attribute Google verlangt und wie es ein Produkt einordnet — sie ist die
Wurzel hinter „Fehlende Altersgruppe" und „Fehlendes Geschlecht".

ZWEI ENTWURFSENTSCHEIDUNGEN
---------------------------
1. Keine fest eingetragenen Kategorie-IDs. Shopifys Taxonomie wird
   gepflegt und umgebaut; hartkodierte IDs veralten still und setzen
   dann falsche oder gar keine Werte. Das Skript fragt die Kategorien
   beim Shop ab und löst die Namen zur Laufzeit auf.

2. Zuordnung über Wörter im Titel, nicht über die Marke. goki führt
   Autos, Puzzles, Musikinstrumente und Greiflinge — eine Kategorie je
   Marke wäre bei den großen Lieferanten durchweg falsch. Die Marke
   dient nur als Rückfall, wenn kein Titelwort greift.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 kategorie-setzen.py --vorschlaege   # zeigt echte Kategoriepfade
    python3 kategorie-setzen.py                # Probelauf
    python3 kategorie-setzen.py --live         # schreibt

Der Probelauf zeigt je Kategorie, welche Produkte sie bekämen. Prüf das,
bevor du schreibst — eine falsch gesetzte Kategorie ist schlechter als
keine, weil Google dann falsche Pflichtattribute verlangt.

Umkehrbar: Die Kategorie lässt sich jederzeit ändern.
"""

import re
import sys
import time
from collections import defaultdict

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

# ──────────────────────────────────────────
# Zuordnung: Titelwort → Kategorie (Suchbegriff in Shopifys Taxonomie)
# Reihenfolge zählt — der erste Treffer gewinnt, deshalb Spezielles oben.
# ──────────────────────────────────────────
NACH_TITEL = [
    (r"\b(malbuch|malbücher)\b",                          "Malbuch"),
    (r"\b(buch|bücher|bilderbuch|liederbuch)\b",          "Buch"),
    (r"\b(puppe|püppchen|wichtel|kuschelpuppe|anziehpuppe|"
     r"stoffpuppe|waldorfpuppe|biegepüppchen)\b",          "Puppen"),
    (r"\b(puzzle|steckpuzzle|einlegepuzzle|schichtenpuzzle|"
     r"soundpuzzle)\b",                                    "Puzzle"),
    (r"\b(bauklotz|bauklötze|baustein|bausteine|holzbausteine)\b",
                                                           "Bauklötze"),
    (r"\b(bausatz|baukasten|seilbahn|konstruktion|steckturm)\b",
                                                           "Baukasten"),
    (r"\b(greifling|rassel|beißring|schnullerkette|mobile)\b",
                                                           "Babyspielzeug"),
    (r"\b(knetwachs|knete|modellierwachs|modelliermasse|"
     r"bienenwachs)\b",                                    "Knete"),
    (r"\b(aquarellfarbe|malfarbe|wasserfarbe|tusche|"
     r"pflanzenfarbe)\b",                                  "Malfarbe"),
    (r"\b(stift|stifte|bleistift|buntstift|wachsmalstift|"
     r"wachsmalblock|wachsmalblöcke)\b",                   "Stifte"),
    (r"\b(seccorell|malblock|malset|bastelset|bastelmaterial)\b",
                                                           "Bastelmaterial"),
    (r"\b(diabolo|jonglier\w*|bumerang|frisbee|eurodisc|"
     r"kendama|yo-?yo)\b",                                 "Jonglieren"),
    (r"schuh\w*",                                          "Schuhe"),
    (r"\b(geldbörse|börse|portemonnaie|geldbeutel)\b",     "Geldbörse"),
    (r"\b(schreibetui|stecketui|schlüsseletui|etui|"
     r"stiftemäppchen|mäppchen)\b",                        "Etui"),
    (r"\b(raumspray|raumduft|duftmischung|naturduft|"
     r"duftöl|raumluft)\b",                                "Raumduft"),
    (r"\b(seife|lotion|creme|shampoo|zahnpasta|pflegeöl|"
     r"massageöl)\b",                                      "Körperpflege"),
    (r"\b(trommel|flöte|klangstab|glockenspiel|leier|"
     r"kalimba)\b",                                        "Musikspielzeug"),
    (r"\b(auto|automobil|käfer|bus|isetta|feuerwehr|"
     r"modellauto|lastwagen|traktor)\b",                   "Fahrzeuge"),
    (r"\b(kette|armband|ring|schmuck|stimmungskette)\b",   "Schmuck"),
    (r"\b(tier|tiere|figur|figuren|holzfigur|schiebetier|"
     r"zwerge|elfen|drache)\b",                            "Spielfiguren"),
]

# Verlage: Deren Sortiment ist durchweg Buch, egal was im Titel steht.
# „Wo unsere Tiere wohnen“ ist ein Bilderbuch und wurde von der
# Tier-Regel sonst zu einer Spielfigur gemacht. Deshalb vor den Titeln.
VERLAGE = {"thienemann", "urachhaus", "geistesleben", "grätz", "graetz",
           "freies geistesleben", "verlag freies geistesleben"}

# Rückfall je Marke, wenn kein Titelwort greift
NACH_MARKE = {
    "ostheimer":   "Spielfiguren",
    "nanchen":     "Puppen",
    "käthe kruse": "Puppen",
    "stockmar":    "Stifte",
    "lyra":        "Stifte",
    "mercurius":   "Bastelmaterial",
    "seccorell":   "Bastelmaterial",
    "kraul":       "Baukasten",
    "henrys":      "Jonglieren",
    "kendama":     "Jonglieren",
    "kisme":       "Schmuck",
    "sonnenleder": "Ledertasche",
    "primavera":   "Raumduft",
    "sonett":      "Körperpflege",
}

# Wenn weder Titel noch Marke greifen
STANDARD = "Spielzeug"

# Suchbegriff + exakter Zielpfad in Shopifys Taxonomie. Beides stammt aus
# `--vorschlaege` gegen diesen Shop, nicht aus dem Gedächtnis: Die Suche
# muss den Pfad zurückliefern, sonst greift nichts und das Produkt wird
# übersprungen. Bewusst eine Ebene höher, wo das Blatt zu eng wäre —
# „Play Vehicles“ statt „Toy Helicopters“, „Juggling“ statt
# „Juggling Rings“, „Jewelry“ statt „Jewelry Sets“.
ZIEL_PFAD = {
    "Puppen":         ("Dolls", "Toys & Games > Toys > Dolls, Playsets & Toy Figures > Dolls"),
    "Spielfiguren":   ("Dolls", "Toys & Games > Toys > Dolls, Playsets & Toy Figures"),
    "Puzzle":         ("Puzzles", "Toys & Games > Puzzles"),
    "Baukasten":      ("Construction Toys", "Toys & Games > Toys > Building Toys > Construction Set Toys"),
    "Bauklötze":      ("Wooden Toys", "Toys & Games > Toys > Building Toys > Wooden Blocks"),
    "Babyspielzeug":  ("Baby Toys", "Baby & Toddler > Baby Toys & Activity Equipment"),
    "Stifte":         ("Art Supplies", "Office Supplies > Office Instruments > Writing & Drawing Instruments > Pens & Pencils > Pencils > Art Pencils"),
    "Bastelmaterial": ("Art & Crafting Materials", "Arts & Entertainment > Hobbies & Creative Arts > Arts & Crafts > Art & Crafting Materials"),
    "Knete":          ("Modeling Clay", "Arts & Entertainment > Hobbies & Creative Arts > Arts & Crafts > Art & Crafting Materials > Pottery & Sculpting Materials > Clay & Modeling Dough > Modeling Dough"),
    "Malfarbe":       ("Craft Paint", "Arts & Entertainment > Hobbies & Creative Arts > Arts & Crafts > Art & Crafting Materials > Craft Paint, Ink & Glaze > Art & Craft Paint"),
    "Jonglieren":     ("Juggling", "Arts & Entertainment > Hobbies & Creative Arts > Juggling"),
    "Schuhe":         ("Athletic Shoes", "Apparel & Accessories > Shoes > Athletic Shoes"),
    "Geldbörse":      ("Wallets", "Apparel & Accessories > Handbags, Wallets & Cases > Wallets & Money Clips > Wallets"),
    "Etui":           ("Pencil Cases", "Office Supplies > Filing & Organization > Pen & Pencil Cases"),
    "Ledertasche":    ("Handbags", "Apparel & Accessories > Handbags, Wallets & Cases"),
    "Raumduft":       ("Room Fresheners", "Home & Garden > Decor > Home Fragrances > Air Fresheners"),
    "Körperpflege":   ("Bath and Body", "Health & Beauty > Personal Care > Cosmetics > Bath & Body"),
    "Buch":           ("Books", "Media > Books"),
    "Malbuch":        ("Books", "Toys & Games > Toys > Art & Drawing Toys > Coloring Books & Pads"),
    "Musikspielzeug": ("Musical Toys", "Toys & Games > Toys > Musical Toys"),
    "Fahrzeuge":      ("Toy Vehicles", "Toys & Games > Toys > Play Vehicles"),
    "Schmuck":        ("Jewelry", "Apparel & Accessories > Jewelry"),
    "Spielzeug":      ("Toys", "Toys & Games > Toys"),
}

# Begriffe, die --vorschlaege zusätzlich abfragt, um Lücken zu schließen.
SUCHE_OFFEN = []

PRO_SEITE = 50
PAUSE = 0.3

TAXONOMIE = """
query($suche: String!) {
  taxonomy {
    categories(first: 8, search: $suche) {
      edges { node { id name fullName isLeaf isArchived } }
    }
  }
}
"""

PRODUKTE = """
query($cursor: String, $n: Int!) {
  products(first: $n, after: $cursor, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        title
        vendor
        category { id fullName }
        resourcePublicationsV2(first: 10) {
          edges { node { isPublished publication { name } } }
        }
      }
    }
  }
}
"""

SCHREIBEN = """
mutation($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id category { fullName } }
    userErrors { field message }
  }
}
"""

_gefunden = {}


def kategorie_id(suche):
    """Löst einen Kategorienamen gegen Shopifys Taxonomie auf (mit Zwischenspeicher)."""
    if suche in _gefunden:
        return _gefunden[suche]

    begriff, ziel_pfad = ZIEL_PFAD.get(suche, (None, None))
    if not begriff:
        _gefunden[suche] = (None, None)
        return _gefunden[suche]

    antwort = shopify_http.execute(TAXONOMIE, {"suche": begriff})
    if antwort.get("_error"):
        print(f"  ! Taxonomie nicht lesbar: {antwort['_error']}")
        _gefunden[suche] = (None, None)
        return _gefunden[suche]

    treffer = [k["node"] for k in
               (antwort.get("taxonomy") or {}).get("categories", {}).get("edges", [])
               if not k["node"].get("isArchived")]

    # NUR exakte Pfadtreffer. Kein „nimm den ersten", kein Blattfilter.
    #
    # Die frühere Fassung bevorzugte Blattkategorien und nahm den ersten
    # Treffer. Shopifys Suche antwortet auf „Toys" mit irgendeinem tiefen
    # Blatt, und der Filter erzwang den Abstieg dorthin: Holzfiguren wurden
    # zu Schaukeln, Geldbörsen zu Pferdehalftern, der halbe Katalog zu
    # Spielzeugwaffen. Lieber keine Kategorie als eine erfundene.
    ziel = ziel_pfad.strip().lower()
    gewaehlt = next((t for t in treffer
                     if (t.get("fullName") or "").strip().lower() == ziel), None)

    _gefunden[suche] = ((gewaehlt or {}).get("id"), (gewaehlt or {}).get("fullName"))
    return _gefunden[suche]


def zielkategorie(titel, marke):
    t = (titel or "").lower()
    m_roh = (marke or "").strip().lower()

    # Verlage zuerst — ihr Sortiment ist Buch, auch wenn Tiere, Zwerge
    # oder Autos im Titel stehen.
    if any(v in m_roh for v in VERLAGE):
        return "Malbuch" if "malbuch" in t else "Buch"

    for muster, name in NACH_TITEL:
        if re.search(muster, t):
            return name
    for schluessel, name in NACH_MARKE.items():
        if schluessel in m_roh:
            return name
    return STANDARD


def seite(cursor):
    for v in range(5):
        a = shopify_http.execute(PRODUKTE, {"cursor": cursor, "n": PRO_SEITE})
        f = a.get("_error", "")
        if not f:
            return a, ""
        if "THROTTLED" in f.upper() and v < 4:
            time.sleep(2 ** v)
            continue
        return {}, f
    return {}, "dauerhaft gedrosselt"


def vorschlaege():
    """Zeigt je Suchbegriff, welche Kategorien Shopify tatsächlich kennt.

    Nur lesend. Daraus wird ZIEL_PFAD gefüllt — mit echten Pfaden aus dem
    Shop statt mit Pfaden aus dem Gedächtnis.
    """
    begriffe = sorted({b for b, _ in ZIEL_PFAD.values()} | set(SUCHE_OFFEN))
    print(f"{len(begriffe)} Suchbegriffe · Kandidaten aus Shopifys Taxonomie\n")
    for begriff in begriffe:
        antwort = shopify_http.execute(TAXONOMIE, {"suche": begriff})
        if antwort.get("_error"):
            print(f"{begriff}\n  ! {antwort['_error']}\n")
            continue
        knoten = [k["node"] for k in
                  (antwort.get("taxonomy") or {}).get("categories", {}).get("edges", [])
                  if not k["node"].get("isArchived")]
        print(f"„{begriff}“")
        for n in knoten:
            print(f"    {n.get('fullName')}")
        if not knoten:
            print("    (nichts gefunden)")
        print()
        time.sleep(0.25)
    print("Diese Ausgabe in den Chat kopieren — daraus wird die Zuordnung")
    print("gebaut, mit exakten Pfaden statt Suchtreffern.")


def main():
    if "--vorschlaege" in sys.argv:
        vorschlaege()
        return
    live = "--live" in sys.argv
    if not live:
        print("PROBELAUF — es wird nichts geändert.")
        print("Zum Schreiben:  python3 kategorie-setzen.py --live\n")

    print("Lese Katalog …")
    offen, hat_schon, gesamt = [], 0, 0
    cursor = None
    while True:
        antwort, fehler = seite(cursor)
        if fehler:
            print(f"Abbruch: {fehler}")
            if not gesamt:
                return
            break
        block = antwort.get("products", {})
        for kante in block.get("edges", []):
            p = kante["node"]
            gesamt += 1
            if p.get("category"):
                hat_schon += 1
                continue
            kanaele = [(k["node"]["publication"] or {}).get("name", "")
                       for k in p.get("resourcePublicationsV2", {}).get("edges", [])
                       if k["node"].get("isPublished")]
            offen.append({
                "id": p["id"],
                "titel": p.get("title", ""),
                "marke": p.get("vendor", ""),
                "google": any("google" in k.lower() for k in kanaele),
            })
        info = block.get("pageInfo", {})
        if not info.get("hasNextPage"):
            break
        cursor = info.get("endCursor")
        time.sleep(PAUSE)

    print(f"{gesamt} aktive Produkte · {hat_schon} mit Kategorie · "
          f"{len(offen)} ohne\n")
    if not offen:
        print("Alle Produkte haben eine Kategorie. Nichts zu tun.")
        return

    # Zuordnen
    nach_kat = defaultdict(list)
    for o in offen:
        nach_kat[zielkategorie(o["titel"], o["marke"])].append(o)

    print("Löse Kategorien gegen Shopifys Taxonomie auf …")
    aufgeloest = {}
    for name in sorted(nach_kat):
        kid, voll = kategorie_id(name)
        aufgeloest[name] = (kid, voll)
        zeichen = "ok   " if kid else "OFFEN"
        ziel = (ZIEL_PFAD.get(name) or (None, None))[1]
        if kid:
            print(f"  {zeichen} „{name}“ → {voll}")
        elif ziel:
            print(f"  {zeichen} „{name}“ → Pfad „{ziel}“ im Shop nicht gefunden")
        else:
            print(f"  {zeichen} „{name}“ → kein Zielpfad hinterlegt, wird übersprungen")
        time.sleep(0.2)

    print("\n" + "=" * 70)
    for name, liste in sorted(nach_kat.items(), key=lambda t: -len(t[1])):
        kid, voll = aufgeloest[name]
        im_google = sum(1 for o in liste if o["google"])
        print(f"\n{len(liste):>4} Produkte → {voll or '(nicht auflösbar)'}"
              f"   [{im_google} im Google-Kanal]")
        for o in liste[:4]:
            print(f"       {o['marke'][:14]:<14} {o['titel'][:48]}")
        if len(liste) > 4:
            print(f"       … und {len(liste)-4} weitere")

    machbar = [(o, aufgeloest[name][0])
               for name, liste in nach_kat.items() if aufgeloest[name][0]
               for o in liste]
    unloesbar = sum(len(l) for n, l in nach_kat.items() if not aufgeloest[n][0])

    print("\n" + "=" * 70)
    print(f"{len(machbar)} Produkte können gesetzt werden")
    if unloesbar:
        print(f"{unloesbar} übersprungen — Kategorie nicht auflösbar")

    if not live:
        print("\nPrüf die Zuordnung oben. Eine falsche Kategorie ist schlechter")
        print("als keine, weil Google dann falsche Pflichtattribute verlangt.")
        print("Passt es, dann:  python3 kategorie-setzen.py --live")
        return

    antwort = input(f"\n{len(machbar)} Produkte ändern? (ja/NEIN): ").strip()
    if antwort.lower() != "ja":
        print("Abgebrochen.")
        return

    ok = fehler = 0
    for i, (o, kid) in enumerate(machbar, 1):
        e = shopify_http.execute(SCHREIBEN, {"input": {"id": o["id"], "category": kid}})
        meldungen = e.get("_error") or [
            u.get("message")
            for u in (e.get("productUpdate", {}).get("userErrors") or [])]
        if meldungen:
            fehler += 1
            if fehler <= 5:
                print(f"  ✗ {o['titel'][:40]}: {meldungen}")
        else:
            ok += 1
        if i % 50 == 0:
            print(f"  … {i}/{len(machbar)}")
        time.sleep(0.25)

    print(f"\nFertig: {ok} gesetzt, {fehler} fehlgeschlagen")
    print("Merchant Center übernimmt die Änderung mit dem nächsten Feed-Abruf.")


if __name__ == "__main__":
    main()

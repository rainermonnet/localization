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
    (r"\b(puppe|püppchen|wichtel|kuschelpuppe|anziehpuppe|stoffpuppe|"
     r"waldorfpuppe|biegepüppchen)\b",          "Dolls"),
    (r"\b(puzzle|steckpuzzle|einlegepuzzle|schichtenpuzzle|soundpuzzle)\b",
                                                 "Puzzles"),
    (r"\b(bausatz|baukasten|seilbahn|konstruktion|steckturm|bauklötze|"
     r"bauklotz)\b",                             "Construction Toys"),
    (r"\b(greifling|rassel|beißring|schnullerkette|mobile)\b",
                                                 "Baby Toys"),
    (r"\b(stift|stifte|bleistift|buntstift|wachsmal|knetbienenwachs|"
     r"aquarellfarbe|malfarbe|malset|malblock|modellierwachs|"
     r"seccorell)\b",                            "Art Supplies"),
    (r"\b(diabolo|jonglier|bumerang|frisbee|eurodisc|kendama|yo-?yo)\b",
                                                 "Juggling"),
    (r"\b(schuh|schuhe|eurythmieschuh)\b",       "Athletic Shoes"),
    (r"\b(seife|öl|lotion|creme|shampoo|zahnpasta|pflegeöl|massageöl)\b",
                                                 "Bath and Body"),
    (r"\b(buch|bücher|bilderbuch|malbuch|liederbuch)\b",
                                                 "Books"),
    (r"\b(trommel|flöte|klangstab|glockenspiel|leier|kalimba)\b",
                                                 "Musical Toys"),
    (r"\b(auto|automobil|käfer|bus|isetta|feuerwehr|modellauto|"
     r"lastwagen|traktor)\b",                    "Toy Vehicles"),
    (r"\b(kette|armband|ring|börse|schmuck|stimmungskette)\b",
                                                 "Jewelry"),
    (r"\b(tier|tiere|figur|figuren|holzfigur|schiebetier|zwerge|"
     r"elfen|drache)\b",                         "Play Figures"),
]

# Rückfall je Marke, wenn kein Titelwort greift
NACH_MARKE = {
    "ostheimer":   "Play Figures",
    "nanchen":     "Dolls",
    "käthe kruse": "Dolls",
    "stockmar":    "Art Supplies",
    "lyra":        "Art Supplies",
    "seccorell":   "Art Supplies",
    "mercurius":   "Art Supplies",
    "kraul":       "Construction Toys",
    "henrys":      "Juggling",
    "kendama":     "Juggling",
    "sonett":      "Bath and Body",
    "primavera":   "Bath and Body",
    "kisme":       "Jewelry",
    "sonnenleder": "Leather Goods",
}

# Wenn weder Titel noch Marke greifen
STANDARD = "Toys"

# Der exakte Pfad in Shopifys Taxonomie, den ein Suchbegriff treffen MUSS.
# Was hier nicht eingetragen oder im Shop nicht auffindbar ist, wird
# übersprungen — nicht geraten. Gefüllt wird die Tabelle aus der Ausgabe von
#     python3 kategorie-setzen.py --vorschlaege
ZIEL_PFAD = {}

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

    antwort = shopify_http.execute(TAXONOMIE, {"suche": suche})
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
    ziel = ZIEL_PFAD.get(suche, "").strip().lower()
    gewaehlt = next((t for t in treffer
                     if (t.get("fullName") or "").strip().lower() == ziel), None)

    _gefunden[suche] = ((gewaehlt or {}).get("id"), (gewaehlt or {}).get("fullName"))
    return _gefunden[suche]


def zielkategorie(titel, marke):
    t = (titel or "").lower()
    for muster, name in NACH_TITEL:
        if re.search(muster, t):
            return name
    m = (marke or "").strip().lower()
    for schluessel, name in NACH_MARKE.items():
        if schluessel in m:
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
    begriffe = sorted({name for _, name in NACH_TITEL}
                      | set(NACH_MARKE.values()) | {STANDARD})
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
        ziel = ZIEL_PFAD.get(name)
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

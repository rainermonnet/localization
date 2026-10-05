"""
robots-anpassen.py — Googlebot ausdrücklich in robots.txt erlauben
===================================================================

Merchant Center meldet bei `goki VW Käfer 1967 Modellauto 1:32`
(Shopify-ID 15883509432693):

    „Qualitäts- und Richtlinienüberprüfungen auf Produktseiten
      nicht möglich"

Google verlangt dafür eigene Gruppen für `Googlebot` und
`Googlebot-Image` in der robots.txt. Shopify liefert die nicht mit —
sie entstehen nur über die Theme-Datei `config/robots.txt.liquid`.

WARUM NICHT EINFACH „Allow: /"
-------------------------------
In robots.txt gewinnt die spezifischste passende User-agent-Gruppe,
und zwar vollständig: Sobald eine eigene `Googlebot`-Gruppe existiert,
ignoriert Googlebot den `*`-Block samt aller Sperren darin. Shopifys
Standard sperrt dort rund ein Dutzend Pfade — /cart, /checkout, /search,
/collections/*sort_by*, /*/account und weitere.

Ein nacktes

    User-agent: Googlebot
    Allow: /

würde Google also genau diese Seiten zum Crawlen öffnen: Warenkorb,
Kasse, Suchergebnisse, jede Sortier- und Filtervariante jeder
Kollektion. Das kostet Crawl-Budget und erzeugt Doppelinhalte.

Dieses Skript übernimmt deshalb die Standardsperren in die
Googlebot-Gruppen mit. `Allow: /` und `Disallow: /checkout` zusammen
sind kein Widerspruch — Google wertet die längste passende Regel, die
Sperre bleibt also wirksam, alles andere ist ausdrücklich erlaubt.
Google bekommt die Erlaubnis, die das Merchant Center sehen will, ohne
dass der Rest aufgeht.

WAS DIE DATEI SPÄTER ENTHÄLT
-----------------------------
Keine abgeschriebene Liste, sondern Shopifys eigene Standardgruppen per
`robots.default_groups` plus die zwei neuen Gruppen. Ändert Shopify den
Standard, zieht die Datei automatisch mit.

Falls `config/robots.txt.liquid` schon existiert, wird nur angefügt —
vorhandener Inhalt bleibt unangetastet.

BRAUCHT
-------
Zugriffsbereich `write_themes` in der App. Fehlt der, bricht das Skript
mit klarer Meldung ab und zeigt den Dateiinhalt zum Einfügen von Hand.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 robots-anpassen.py            # Probelauf, zeigt die Datei
    python3 robots-anpassen.py --live     # schreibt ins aktive Theme
    python3 robots-anpassen.py --pruefen  # liest die öffentliche robots.txt

Umkehrbar: Die Datei lässt sich im Theme-Editor löschen, dann gilt
wieder Shopifys Standard.
"""

import re
import sys
import time
import urllib.error
import urllib.request

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

DATEI = "config/robots.txt.liquid"
AGENTEN = ("Googlebot", "Googlebot-Image")
MARKER = "# Zwergenladen: eigene robots.txt aktiv"
STAND = "2026-10-05c"           # steht in jeder Ausgabe, damit erkennbar ist,
                                # welche Fassung gerade läuft
SCHALTER = {"--live", "--pruefen", "--theme", "--roh", "--frisch"}

# Kandidaten für die ausgelieferte robots.txt. Die myshopify-Adresse steht
# mit drin, weil sie immer funktioniert — auch wenn die Wunschdomain woanders
# hinzeigt. Eigene Adresse geht vor:  --pruefen https://meineadresse.de
HOSTS = [
    "https://zwergenladen.info",
    "https://www.zwergenladen.info",
    "https://zwergenladen-fr.myshopify.com",
]

# ──────────────────────────────────────────────────────────────
# Der Liquid-Block, der angefügt wird.
#
# `standard_regeln` sammelt die Disallow-Zeilen aus Shopifys *-Gruppe,
# damit die Googlebot-Gruppen sie mitführen. Die Objekte werden ganz
# ausgegeben ({{ rule }}, nicht {{ rule.directive }}: {{ rule.value }}) —
# sie rendern sich selbst als „Disallow: /pfad" und können so nicht
# auseinanderlaufen, wenn Shopify das Format ändert.
# ──────────────────────────────────────────────────────────────
ZUSATZ = """
{%- comment -%}
  Zwergenladen: Google ausdrücklich erlauben (Merchant Center verlangt
  eigene Gruppen für Googlebot und Googlebot-Image).

  Die Standardsperren aus der *-Gruppe werden mitgeführt, weil eine
  eigene Gruppe den *-Block sonst vollständig ersetzt und Warenkorb,
  Kasse, Suche und Filter-URLs zum Crawlen aufgingen.
{%- endcomment -%}
{%- capture standard_regeln -%}
{%- for gruppe in robots.default_groups -%}
{%- if gruppe.user_agent.value == '*' -%}
{%- for rule in gruppe.rules %}
{{ rule }}
{%- endfor -%}
{%- endif -%}
{%- endfor -%}
{%- endcapture %}
User-agent: Googlebot
Allow: /
{{- standard_regeln }}

User-agent: Googlebot-Image
Allow: /
{{- standard_regeln }}
"""

# Shopifys dokumentierte Standardausgabe — nur nötig, wenn die Datei neu ist.
GRUNDGERUEST = """# Zwergenladen: eigene robots.txt aktiv (config/robots.txt.liquid)
{% for group in robots.default_groups %}
  {{- group.user_agent }}
  {%- for rule in group.rules %}
    {{ rule }}
  {%- endfor %}
  {%- if group.sitemap != blank %}
    {{ group.sitemap }}
  {%- endif %}
{% endfor %}
"""

THEMES = """
query {
  themes(first: 20, roles: [MAIN]) {
    edges { node { id name role } }
  }
}
"""

DATEI_LESEN = """
query($id: ID!, $namen: [String!]) {
  theme(id: $id) {
    id
    name
    files(filenames: $namen, first: 1) {
      nodes {
        filename
        body {
          ... on OnlineStoreThemeFileBodyText { content }
        }
      }
    }
  }
}
"""

SCHREIBEN = """
mutation($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $themeId, files: $files) {
    upsertedThemeFiles { filename }
    userErrors { field message }
  }
}
"""


def handweg(grund):
    """Zeigt Dateiinhalt und Klickweg, wenn die API nicht herankommt."""
    print(f"\n{grund}\n")
    print("Dann von Hand — dauert zwei Minuten und ist einmalige Arbeit:")
    print("  1. Shopify Admin → Online-Shop → Themes")
    print("  2. Beim aktiven Theme auf ··· → Code bearbeiten")
    print("  3. Links „Neue Datei hinzufügen“ → Ordner config →")
    print("     Dateiname robots.txt → Endung .liquid")
    print("  4. Den folgenden Inhalt vollständig einsetzen und speichern:")
    print("\n" + "=" * 70)
    print(GRUNDGERUEST + ZUSATZ)
    print("=" * 70)
    print("\nDanach prüfen:  python3 robots-anpassen.py --pruefen")
    print("(Das liest nur die öffentliche robots.txt und braucht keinen Zugang.)")
    print("\nLieber doch per Skript? Dann fehlen der App die Zugriffsbereiche")
    print("read_themes und write_themes. Nach dem Nachtragen im Dev Dashboard")
    print("muss die Installation erneut bestätigt werden.")
    sys.exit(0)


def _scope_fehlt(fehler):
    t = str(fehler).lower()
    return "access_denied" in t or "access scope" in t or "_themes" in t


def aktives_theme():
    antwort = shopify_http.execute(THEMES)
    if antwort.get("_error"):
        if _scope_fehlt(antwort["_error"]):
            handweg("Der App fehlt der Zugriffsbereich read_themes — "
                    "das Theme ist über die API nicht lesbar.")
        sys.exit(f"Themes nicht lesbar: {antwort['_error']}")
    kanten = (antwort.get("themes") or {}).get("edges", [])
    if not kanten:
        sys.exit("Kein aktives Theme gefunden.")
    n = kanten[0]["node"]
    return n["id"], n.get("name", "")


def bestand_lesen(theme_id):
    """Gibt den aktuellen Dateiinhalt zurück — oder None, wenn es die Datei nicht gibt."""
    antwort = shopify_http.execute(DATEI_LESEN, {"id": theme_id, "namen": [DATEI]})
    if antwort.get("_error"):
        print(f"  ! Datei nicht lesbar: {antwort['_error']}")
        return None
    knoten = ((antwort.get("theme") or {}).get("files") or {}).get("nodes") or []
    if not knoten:
        return None
    return (knoten[0].get("body") or {}).get("content")


def holen(basis, frisch=False):
    """Holt <basis>/robots.txt und gibt (text, ziel_url) zurück — oder (None, Grund).

    `frisch` hängt einen Zufallswert an und bittet um eine ungepufferte
    Antwort. Shopify liefert robots.txt über ein CDN aus; ohne das sieht
    man unter Umständen minutenlang die alte Fassung.
    """
    url = basis.rstrip("/") + "/robots.txt"
    kopf = {"User-Agent": "Zwergenladen-Pruefung"}
    if frisch:
        url += f"?cb={int(time.time())}"
        kopf["Cache-Control"] = "no-cache"
        kopf["Pragma"] = "no-cache"
    try:
        anfrage = urllib.request.Request(url, headers=kopf)
        with urllib.request.urlopen(anfrage, timeout=20) as a:
            if frisch:
                alter = a.headers.get("Age") or a.headers.get("age")
                cache = a.headers.get("CF-Cache-Status") or a.headers.get("X-Cache")
                hinweise = [x for x in (f"Age: {alter}" if alter else None,
                                        f"Cache: {cache}" if cache else None) if x]
                if hinweise:
                    print(f"      {' · '.join(hinweise)}")
            return a.read().decode("utf-8", "replace"), a.geturl()
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except (urllib.error.URLError, OSError) as e:
        return None, str(e)


def auswerten(text, zeige_inhalt=False):
    """Sagt, welche der verlangten Gruppen fehlen. Gibt [] zurück, wenn alles da ist."""
    zeilen = [z.strip() for z in text.splitlines()]
    nicht_leer = [z for z in zeilen if z]
    gruppen = [z for z in nicht_leer if z.lower().startswith("user-agent:")]
    print(f"      {len(nicht_leer)} Zeilen, {len(gruppen)} User-agent-Gruppen")

    # Unter 10 Zeilen ist das keine Shopify-robots.txt — Shopifys Standard
    # allein bringt mehrere Gruppen und ein Dutzend Regeln mit.
    if len(nicht_leer) < 10 or zeige_inhalt:
        print("      ── tatsächlicher Inhalt ──")
        grenze = len(nicht_leer) if zeige_inhalt else 25
        for z in nicht_leer[:grenze]:
            print(f"      {z}")
        if len(nicht_leer) > grenze:
            print(f"      … und {len(nicht_leer)-grenze} weitere Zeilen"
                  " — vollständig mit --roh")
        print("      ──────────────────────────")

    if MARKER in text:
        print("      Theme-Vorlage wird angewendet: ja")
    else:
        print("      Theme-Vorlage wird angewendet: NEIN — Shopify liefert")
        print("                                     seine eingebaute Datei aus")

    fehlt = []
    for agent in AGENTEN:
        da = any(z.lower() == f"user-agent: {agent.lower()}" for z in nicht_leer)
        print(f"      {'ok   ' if da else 'FEHLT'} {agent}")
        if not da:
            fehlt.append(agent)
        else:
            # Gruppe vorhanden — stehen auch die Sperren darunter?
            i = next(i for i, z in enumerate(nicht_leer)
                     if z.lower() == f"user-agent: {agent.lower()}")
            block = []
            for z in nicht_leer[i+1:]:
                if z.lower().startswith("user-agent:"):
                    break
                block.append(z)
            sperren = sum(1 for z in block if z.lower().startswith("disallow:"))
            print(f"            Allow: / {'ja' if 'Allow: /' in block else 'FEHLT'}"
                  f" · {sperren} Sperren übernommen")
            if sperren == 0:
                print("            ! Ohne Sperren wären Warenkorb, Kasse und Suche")
                print("              für Google offen — capture-Block prüfen.")
    return fehlt


def veroeffentlichtes_theme(basis):
    """Liest aus dem Quelltext der Startseite, welches Theme der Shop ausliefert.

    Shopify schreibt in jede Storefront-Seite einen Block
        Shopify.theme = {"name":"…","id":123,"role":"main", …}
    Das ist die einzige Auskunft, die nicht davon abhängt, was im Admin
    angezeigt wird — und damit der Schiedsrichter bei der Frage, ob die
    bearbeitete Datei überhaupt im ausgelieferten Theme liegt.
    """
    url = basis.rstrip("/") + f"/?cb={int(time.time())}"
    try:
        anfrage = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 Zwergenladen-Pruefung",
                          "Cache-Control": "no-cache"})
        with urllib.request.urlopen(anfrage, timeout=25) as a:
            seite = a.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        print(f"  Startseite nicht lesbar: {e}")
        return None

    treffer = re.search(r"Shopify\.theme\s*=\s*(\{.*?\})\s*;", seite, re.S)
    if not treffer:
        print("  Kein Shopify.theme im Quelltext gefunden.")
        print("  Entweder antwortet hier kein Shopify-Shop, oder die Seite")
        print("  wird von einer Zwischenschicht ausgeliefert.")
        return None

    roh = treffer.group(1)
    def feld(name):
        m = re.search(rf'"{name}"\s*:\s*"?([^",}}]+)"?', roh)
        return m.group(1).strip() if m else "?"

    tid, name, rolle = feld("id"), feld("name"), feld("role")
    print(f"  Der Shop liefert aus Theme:  {name}")
    print(f"                     ID:       {tid}")
    print(f"                     Rolle:    {rolle}")
    return tid


def oeffentlich_pruefen(eigene=None, zeige_inhalt=False, frisch=False):
    """Prüft die ausgelieferte robots.txt — erst die eigene Adresse, sonst alle Kandidaten."""
    hosts = [eigene] if eigene else HOSTS
    bester = None
    for basis in hosts:
        print(f"\n  {basis}/robots.txt{' (Cache umgangen)' if frisch else ''}")
        text, ziel = holen(basis, frisch)
        if text is None:
            print(f"      nicht erreichbar: {ziel}")
            continue
        if ziel.rstrip("/") != basis.rstrip("/") + "/robots.txt":
            print(f"      weitergeleitet nach: {ziel}")
        fehlt = auswerten(text, zeige_inhalt)
        if bester is None or not fehlt:
            bester = fehlt
    return bester


HOLEN = ('cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app" && '
         'curl -fsSL -o robots-anpassen.py "https://raw.githubusercontent.com/'
         'rainermonnet/localization/claude/shopify-opti-assets-miijc7/'
         'shopify-assets/robots-anpassen.py"')


def argumente_pruefen():
    """Bricht bei unbekannten Argumenten ab, statt stillschweigend etwas anderes zu tun.

    Ein nicht erkanntes --irgendwas fiel vorher in den Normalbetrieb und
    versuchte zu schreiben. Das ist genau falsch herum: Ein Tippfehler oder
    eine veraltete Kopie darf nicht in den schreibenden Zweig führen.
    """
    unbekannt = [a for a in sys.argv[1:]
                 if a.startswith("-") and a not in SCHALTER]
    if unbekannt:
        print(f"Unbekanntes Argument: {' '.join(unbekannt)}")
        print(f"Bekannt sind: {' '.join(sorted(SCHALTER))}")
        print("\nFalls du den Schalter aus einer Anleitung hast, ist diese")
        print(f"Kopie veraltet (Stand {STAND}). Neu holen:\n")
        print(f"  {HOLEN}")
        sys.exit(1)


def main():
    print(f"robots-anpassen.py · Stand {STAND}\n")
    argumente_pruefen()
    live = "--live" in sys.argv

    if "--theme" in sys.argv:
        basis = next((a for a in sys.argv[1:] if a.startswith("http")), HOSTS[0])
        print(f"Lese {basis} …\n")
        tid = veroeffentlichtes_theme(basis)
        if tid and tid != "?":
            print(f"\nVergleich diese ID mit der in deiner Editor-Adresse:")
            print(f"  admin.shopify.com/store/zwergenladen-fr/themes/{tid}")
            print("\nStimmt sie nicht mit der überein, in der du gearbeitet")
            print("hast, lag die Datei im falschen Theme. Dann dort anlegen.")
        return

    if "--pruefen" in sys.argv:
        eigene = next((a for a in sys.argv[1:] if a.startswith("http")), None)
        print("Lese die ausgelieferte robots.txt …")
        if not eigene:
            print("(Eigene Adresse geht vor:  --pruefen https://meineadresse.de)")
        fehlt = oeffentlich_pruefen(eigene,
                                    zeige_inhalt="--roh" in sys.argv,
                                    frisch="--frisch" in sys.argv)

        if fehlt == []:
            print("\nBeide Gruppen sind draußen. Jetzt im Merchant Center den")
            print("URL-Test für goki VW Käfer 1967 (15883509432693) wiederholen.")
        elif fehlt is None:
            print("\nKeine der Adressen war erreichbar. Welche Adresse ruft ein")
            print("Kunde auf? Die hier eintragen:")
            print("  python3 robots-anpassen.py --pruefen https://deine-adresse.de")
        else:
            print("\nNoch nicht draußen. Drei Ursachen, in dieser Reihenfolge prüfen:")
            print("  1. Falsches Theme. Die Datei muss im VERÖFFENTLICHTEN Theme")
            print("     liegen, nicht im Entwurf. Online-Shop → Themes →")
            print("     ganz oben unter „Aktuelles Theme“.")
            print("  2. Falsche Adresse. Steht oben eine robots.txt mit nur")
            print("     ein, zwei Zeilen, ist das nicht dein Shopify-Shop —")
            print("     dann zeigt die Domain woanders hin.")
            print("  3. Cache. Shopify liefert robots.txt über ein CDN aus.")
            print("     Mit Cache umgehen:  --pruefen --frisch")
        return

    if not live:
        print("PROBELAUF — es wird nichts geändert.")
        print("Zum Schreiben:  python3 robots-anpassen.py --live\n")

    theme_id, theme_name = aktives_theme()
    print(f"Aktives Theme: {theme_name}\n")

    vorher = bestand_lesen(theme_id)

    if vorher is None:
        print(f"{DATEI} existiert nicht — wird neu angelegt.")
        print("Shopifys Standardgruppen kommen über robots.default_groups mit,")
        print("damit durch die neue Datei keine Sperre verloren geht.")
        neu = GRUNDGERUEST + ZUSATZ
    elif "Googlebot" in vorher:
        print(f"{DATEI} enthält bereits eine Googlebot-Regel.")
        print("Nichts zu tun. Vorhandenes wird nicht überschrieben.\n")
        print("Was der Shop tatsächlich ausliefert:")
        oeffentlich_pruefen()
        return
    else:
        print(f"{DATEI} existiert ({len(vorher)} Zeichen) — Block wird angefügt.")
        print("Der vorhandene Inhalt bleibt unverändert.")
        neu = vorher.rstrip() + "\n" + ZUSATZ

    print("\n" + "=" * 70)
    print(neu)
    print("=" * 70)

    if not live:
        print("\nPrüf den Inhalt oben. Passt es, dann:")
        print("  python3 robots-anpassen.py --live")
        return

    antwort = input(f"\n{DATEI} im Theme „{theme_name}“ schreiben? (ja/NEIN): ").strip()
    if antwort.lower() != "ja":
        print("Abgebrochen.")
        return

    e = shopify_http.execute(SCHREIBEN, {
        "themeId": theme_id,
        "files": [{"filename": DATEI, "body": {"type": "TEXT", "value": neu}}]})

    fehler = e.get("_error")
    if not fehler:
        fehler = [u.get("message")
                  for u in (e.get("themeFilesUpsert", {}).get("userErrors") or [])]
        fehler = fehler or None

    if fehler:
        if _scope_fehlt(fehler):
            handweg("Der App fehlt der Zugriffsbereich write_themes — "
                    "schreiben ist über die API nicht möglich.")
        print(f"\nFehlgeschlagen: {fehler}")
        return

    print(f"\nGeschrieben: {DATEI}")
    print("\nPrüfe, was der Shop ausliefert …")
    fehlt = oeffentlich_pruefen()
    if fehlt:
        print("\nNoch nicht sichtbar — Shopify cacht robots.txt einige Minuten.")
        print("Später nachsehen:  python3 robots-anpassen.py --pruefen")
    elif fehlt == []:
        print("\nDraußen. Jetzt im Merchant Center den URL-Test für")
        print("goki VW Käfer 1967 (ID 15883509432693) wiederholen.")


if __name__ == "__main__":
    main()

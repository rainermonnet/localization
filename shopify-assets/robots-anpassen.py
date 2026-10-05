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

import sys
import urllib.error
import urllib.request

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

DATEI = "config/robots.txt.liquid"
SHOP_URL = "https://zwergenladen.de/robots.txt"
AGENTEN = ("Googlebot", "Googlebot-Image")

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
GRUNDGERUEST = """{% for group in robots.default_groups %}
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


def oeffentlich_pruefen():
    """Liest die ausgelieferte robots.txt und sagt, was Google dort sieht."""
    try:
        anfrage = urllib.request.Request(
            SHOP_URL, headers={"User-Agent": "Zwergenladen-Pruefung"})
        with urllib.request.urlopen(anfrage, timeout=20) as a:
            text = a.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        print(f"  {SHOP_URL} nicht erreichbar: {e}")
        return None

    zeilen = [z.strip() for z in text.splitlines()]
    gruppen = [z for z in zeilen if z.lower().startswith("user-agent:")]
    print(f"  {len(zeilen)} Zeilen, {len(gruppen)} User-agent-Gruppen")
    fehlt = []
    for agent in AGENTEN:
        da = any(z.lower() == f"user-agent: {agent.lower()}" for z in zeilen)
        print(f"  {'ok   ' if da else 'FEHLT'} {agent}")
        if not da:
            fehlt.append(agent)
    return fehlt


def main():
    live = "--live" in sys.argv

    if "--pruefen" in sys.argv:
        print(f"Lese {SHOP_URL} …")
        fehlt = oeffentlich_pruefen()
        if fehlt == []:
            print("\nBeide Gruppen sind draußen. Jetzt im Merchant Center den")
            print("URL-Test für das Produkt wiederholen.")
        elif fehlt:
            print("\nNoch nicht draußen. Shopify liefert robots.txt gecacht aus —")
            print("nach dem Schreiben können einige Minuten vergehen.")
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

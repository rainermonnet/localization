# robots.txt – Googlebot ausdrücklich erlauben

**Problem:** Google Merchant Center meldet
> „Qualitäts- und Richtlinienüberprüfungen auf Produktseiten nicht möglich"
> → User-Agents `Googlebot` und `Googlebot-Image` fehlen in robots.txt

**Betroffenes Produkt:**
goki VW Käfer 1967 Modellauto 1:32 – Shopify-ID `15883509432693`

---

## Der einfache Weg: Skript

```bash
cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
python3 robots-anpassen.py            # Probelauf, zeigt die fertige Datei
python3 robots-anpassen.py --live     # schreibt ins aktive Theme
python3 robots-anpassen.py --pruefen  # liest die öffentliche robots.txt
```

Das Skript legt `config/robots.txt.liquid` an, falls sie fehlt, und fügt
nur an, falls sie existiert. Es braucht den Zugriffsbereich
`write_themes`. Fehlt der, bricht es ab und zeigt den Inhalt zum
Einfügen von Hand — dann weiter bei „Von Hand".

---

## Zuerst verstehen: eine Googlebot-Gruppe ersetzt den \*-Block

In robots.txt gilt pro Crawler **genau eine** Gruppe: die spezifischste
passende — und die gilt vollständig. Sobald eine eigene
`User-agent: Googlebot`-Gruppe existiert, liest Googlebot den
`User-agent: *`-Block **gar nicht mehr**, auch nicht die Sperren darin.

Shopifys Standard sperrt im \*-Block unter anderem:

```
Disallow: /admin
Disallow: /cart
Disallow: /orders
Disallow: /checkouts/
Disallow: /checkout
Disallow: /*/account
Disallow: /collections/*sort_by*
Disallow: /*/collections/*sort_by*
Disallow: /collections/*+*
Disallow: /search
```

Ein nacktes

```
User-agent: Googlebot
Allow: /
```

öffnet Google also Warenkorb, Kasse, Suchergebnisse und jede Sortier-
und Filtervariante jeder Kollektion. Das kostet Crawl-Budget und
erzeugt Doppelinhalte, ohne dass eine dieser Seiten ranken soll.

**Lösung:** Die Standardsperren in die Googlebot-Gruppe mitnehmen.
`Allow: /` und `Disallow: /checkout` widersprechen sich nicht — Google
wertet die **längste passende** Regel, die Sperre bleibt also wirksam,
alles andere ist ausdrücklich erlaubt. Genau das tut das Skript, und
genau das steht unten im Code zum Einfügen.

---

## Von Hand

**Shopify Admin → Online-Shop → Themes → ··· (drei Punkte) → Code bearbeiten**

Links in der Dateiliste nach `config/robots.txt.liquid` suchen.
Gibt es die Datei nicht:

- „Neue Datei hinzufügen" klicken
- Ordner: **config** → Dateiname: `robots.txt` → Endung `.liquid`
- Shopify erstellt `config/robots.txt.liquid`

### Wenn die Datei NEU ist — kompletter Inhalt

Die Datei ersetzt die ausgelieferte robots.txt vollständig. Steht nur
der Googlebot-Block darin, sind **alle** Standardsperren weg. Deshalb
muss der `robots.default_groups`-Durchlauf mit hinein:

```liquid
{% for group in robots.default_groups %}
  {{- group.user_agent }}
  {%- for rule in group.rules %}
    {{ rule }}
  {%- endfor %}
  {%- if group.sitemap != blank %}
    {{ group.sitemap }}
  {%- endif %}
{% endfor %}

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
```

Wichtig an der Schreibweise: `{{ group.user_agent }}` und `{{ rule }}`
werden **ganz** ausgegeben. Diese Objekte rendern sich selbst als
`User-agent: *` beziehungsweise `Disallow: /cart`. Wer `User-agent:
{{ group.user_agent }}` schreibt, bekommt `User-agent: User-agent: *` —
eine kaputte Datei, die Google komplett verwirft.

### Wenn die Datei SCHON EXISTIERT

Nur den Teil ab `{%- capture standard_regeln -%}` am Ende anfügen.
Vorhandenes nicht anfassen.

---

## Prüfen

```bash
python3 robots-anpassen.py --pruefen
```

oder im Browser `https://zwergenladen.de/robots.txt` aufrufen.
Erwartet: beide Gruppen erscheinen, **und** die Disallow-Zeilen stehen
unter ihnen.

Shopify liefert robots.txt gecacht aus — nach dem Speichern können
einige Minuten vergehen.

Erst danach im Merchant Center: Produkt → Diagnose → URL-Test
wiederholen.

---

## Richtigstellung zu einer früheren Fassung

In einer früheren Version dieser Datei stand, Shopify biete seit 2022
eine native robots.txt-Bearbeitung unter *Online-Shop →
Voreinstellungen*. **Das gibt es nicht.** robots.txt lässt sich bei
Shopify ausschließlich über die Theme-Datei
`config/robots.txt.liquid` ändern. Wer in den Voreinstellungen sucht,
sucht umsonst.

Ebenfalls falsch war der oben gezeigte Code in der alten Fassung
(`User-agent: {{ group.user_agent }}`) — siehe Hinweis zur
Schreibweise.

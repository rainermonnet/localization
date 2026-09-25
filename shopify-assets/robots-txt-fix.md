# robots.txt Fix – goki VW Käfer / Googlebot-Image

**Problem:** Google Merchant Center meldet  
> "Qualitäts- und Richtlinienüberprüfungen auf Produktseiten nicht möglich"  
> → User-Agents `Googlebot` und `Googlebot-Image` fehlen in robots.txt

**Betroffenes Produkt:**  
goki VW Käfer 1967 Modellauto 1:32 – Shopify-ID `15883509432693`

---

## Fix im Shopify-Theme

### Schritt 1 – robots.txt.liquid öffnen

**Shopify Admin → Online-Shop → Themes → ... (drei Punkte) → Code bearbeiten**  
→ In der Dateiliste links: `config/robots.txt.liquid` suchen

Falls die Datei nicht existiert:
- Auf "Neue Datei hinzufügen" klicken
- Typ: **Config** → Dateiname: `robots.txt`
- Shopify erstellt `config/robots.txt.liquid`

### Schritt 2 – Code einfügen

Folgenden Block **am Ende** der Datei ergänzen:

```liquid
{%- comment -%}
  Explizite Erlaubnis für Google-Crawler (Merchant Center Pflicht)
  Hinzugefügt: 2026-08-25
{%- endcomment -%}

User-agent: Googlebot
Allow: /

User-agent: Googlebot-Image
Allow: /
```

### Schritt 3 – Prüfen

Nach dem Speichern: `https://zwergenladen.de/robots.txt` aufrufen  
→ Googlebot und Googlebot-Image müssen in der Ausgabe erscheinen.

Dann im Merchant Center: Produkt → Diagnostics → URL-Test wiederholen.

---

## Komplette robots.txt.liquid (falls neu erstellt)

```liquid
{% for group in robots.default_groups %}
  User-agent: {{ group.user_agent }}
  {% for rule in group.rules %}
  {{ rule.directive }}: {{ rule.value }}
  {%- endfor %}
  {% if group.sitemap %}
  Sitemap: {{ group.sitemap.link }}
  {%- endif %}

{% endfor %}

User-agent: Googlebot
Allow: /

User-agent: Googlebot-Image
Allow: /
```

---

## Alternative: robots.txt über Shopify Admin bearbeiten (kein Code nötig)

Shopify bietet seit 2022 eine native Bearbeitung:  
**Admin → Online-Shop → Voreinstellungen → robots.txt bearbeiten**  
→ Dort direkt die zwei Blöcke einfügen.

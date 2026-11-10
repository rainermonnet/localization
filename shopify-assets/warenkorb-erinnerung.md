# Warenkorb-Erinnerung — Einrichtung und Texte

Shopify verschickt die Erinnerung an abgebrochene Warenkörbe selbst. Es
kostet nichts extra, muss aber **aktiviert** werden — im Auslieferungszustand
ist es aus.

---

## Teil 1 · Einschalten

**Shopify Admin → Einstellungen → Checkout**

Abschnitt **Abgebrochene Checkouts**:

| Einstellung | Empfehlung |
|---|---|
| E-Mail bei abgebrochenem Checkout senden | **einschalten** |
| Empfänger | Alle (nicht nur Abonnenten) |
| Zeitpunkt | **10 Stunden** nach Abbruch |

Zehn Stunden statt einer Stunde: Wer abends stöbert, bekommt die Mail am
nächsten Morgen statt mitten in der Nacht. Bei Spielzeug wird selten
spontan entschieden — oft wird mit dem Partner Rücksprache gehalten.

---

## Teil 2 · Text ersetzen

**Einstellungen → Benachrichtigungen → Abgebrochener Checkout**

Shopifys Standardtext ist neutral und austauschbar. Ersetze ihn.

### Betreff

```
Dein Warenkorb wartet noch auf dich
```

Kein "Du hast etwas vergessen!" — das unterstellt Vergesslichkeit. Und
kein Ausrufezeichen; es klingt nach Drücken.

### E-Mail-Text

Im Editor auf **Code bearbeiten** umschalten und den Textbereich ersetzen.
Alles in `{{ }}` sind Platzhalter, die Shopify beim Versand füllt.

```liquid
<p>Hallo{% if checkout.customer.first_name %} {{ checkout.customer.first_name }}{% endif %},</p>

<p>
  du hast dir bei uns etwas ausgesucht und den Einkauf noch nicht
  abgeschlossen. Wir haben deine Auswahl aufgehoben — hier ist sie:
</p>

{{ checkout.line_items | line_items_for_email }}

<p style="margin: 28px 0;">
  <a href="{{ url }}"
     style="background:#3f6b52;color:#ffffff;padding:13px 26px;
            text-decoration:none;border-radius:2px;font-weight:600;
            display:inline-block;">
    Einkauf fortsetzen
  </a>
</p>

<p>
  Falls du unsicher bist, ob das Richtige dabei ist: Schreib uns einfach
  zurück. Wir führen einen echten Laden in Freiburg und kennen jedes
  Stück, das wir anbieten — vom Holzgreifling bis zur Waldorfpuppe.
</p>

<p>
  Herzliche Grüße<br>
  Rainer Monnet<br>
  Zwergenladen
</p>

<p style="font-size:12px;color:#7c8783;margin-top:26px;">
  Du bekommst diese Nachricht einmalig, weil du den Einkauf nicht
  abgeschlossen hast. Es folgt keine weitere Erinnerung.
</p>
```

Der letzte Absatz ist kein Kleingedrucktes, sondern ein Versprechen:
Wer weiß, dass nichts nachkommt, empfindet die eine Mail nicht als
Bedrängung.

---

## Teil 3 · Zweite Erinnerung (optional)

Shopify verschickt von Haus aus **genau eine** Mail. Wer eine Abfolge will,
braucht **Shopify Email** — kostenlos bis 10.000 Mails im Monat, bei deinem
Volumen also dauerhaft gratis.

**Apps → Shopify Email → Automatisierungen → Warenkorbabbruch**

Sinnvolle Abfolge:

| Zeitpunkt | Inhalt |
|---|---|
| 10 Stunden | Erinnerung (Text oben) |
| 3 Tage | Beratungsangebot, kein Verkaufsdruck |

Für die zweite Mail:

> **Betreff:** Können wir dir bei der Auswahl helfen?
>
> Vor ein paar Tagen hattest du etwas im Warenkorb. Vielleicht war es
> doch nicht das Passende — das kommt vor, gerade bei Spielzeug, das
> lange halten soll.
>
> Falls du eine Frage hattest, die dich zögern ließ: Antworte einfach
> auf diese Mail. Wir beraten gern, auch wenn am Ende kein Kauf steht.

**Keine dritte Mail.** Wer nach zwei Nachrichten nicht kauft, will nicht
kaufen. Ab der dritten schadest du deinem Ruf mehr, als die Bestellung
wert wäre.

---

## Was das realistisch bringt

Übliche Rückgewinnungsquote bei abgebrochenen Warenkörben: **5 bis 15 %**.

Bei deinem derzeitigen Volumen — rund 135 Shop-Klicks in 28 Tagen — sind
das vielleicht **eine bis drei zusätzliche Bestellungen im Monat**.

Das ist wenig. Aber es kostet dich einmalig eine halbe Stunde Einrichtung
und danach nichts mehr. Und es skaliert mit: Wenn der Traffic steigt,
arbeitet es ohne weiteres Zutun mit.

Die 7.581 € aus der Werbemail sind damit nicht zu erreichen. Die wären
auch mit einem bezahlten Anbieter nicht zu erreichen — dafür fehlt schlicht
die Besucherzahl.

---

## Prüfen, ob es läuft

**Analysen → Berichte → „Abgebrochene Checkouts"**

Dort steht, wie viele Warenkörbe abgebrochen und wie viele nach der Mail
doch noch abgeschlossen wurden. Nach vier Wochen hast du eine belastbare
Zahl — und weißt, ob sich eine zweite Mail lohnt.

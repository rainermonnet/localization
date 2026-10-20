# Newsletter-Anmeldung auf /pages/newsletter

Die Seite enthielt nur Text und verwies auf ein Formular „ganz unten auf
dieser Seite" — das kam aus dem Footer des alten Themes und gibt es im
neuen nicht mehr. Kein einziges Eingabefeld war vorhanden.

Eingesetzt am 20.10.2026 über `pageUpdate` (Seite 703742280053),
Nachname am selben Tag ergänzt.

## Warum reines HTML und kein Liquid

Seiteninhalte in Shopify verarbeiten **kein Liquid**. Ein
`{% form 'customer' %}` im Seitentext bliebe wirkungslos. Das Formular
sendet deshalb direkt an Shopifys Kundenendpunkt:

    <form method="post" action="/contact#newsletter-danke">
      <input type="hidden" name="form_type" value="customer">
      <input type="hidden" name="utf8" value="✓">
      <input type="hidden" name="contact[tags]" value="newsletter">

`form_type=customer` ist das, was aus dem Absenden eine Newsletter-
Anmeldung macht. Ohne dieses Feld passiert nichts.

## Die Felder

| Feld | Name | Pflicht |
|---|---|---|
| Vorname | `contact[first_name]` | nein |
| Name | `contact[last_name]` | nein |
| E-Mail | `contact[email]` | ja (`type=email` prüft das Format) |
| Einwilligung | `einwilligung` | ja (`required`) |

Die Einwilligung trägt bewusst **keinen** `contact[`-Präfix: Shopify
ignoriert unbekannte Felder, und das Häkchen wird ohnehin vom Browser
erzwungen. Mit `contact[`-Präfix bestünde die Gefahr, dass der Wert
unbeabsichtigt am Kundendatensatz landet.

`contact[tags]=newsletter` markiert die Herkunft, sodass sich später
unterscheiden lässt, wer über diese Seite kam.

## Rechtlicher Teil (§ 7 UWG)

Die Einwilligung muss ausdrücklich sein, deshalb ein Pflichthäkchen und
keine Vorauswahl. Der Text nennt Absender, Inhalt, Abmeldemöglichkeit
und verlinkt die Datenschutzerklärung.

**Das allein genügt nicht.** Nachweisbar wird die Einwilligung erst
durch Double Opt-in. Das ist eine Shop-Einstellung, kein Formularfeld:

    Einstellungen → Benachrichtigungen → Kundenbenachrichtigungen
    → Abschnitt „Double-Opt-in für Marketing"

Wirkt nur für künftige Anmeldungen; wer vorher eingetragen wurde,
bekommt keine Bestätigungsmail mehr. Die Bestätigungsmail darf laut
Shopify keine Werbung enthalten.

Quellen:
- https://help.shopify.com/en/manual/promoting-marketing/create-marketing/shopify-messaging/email/subscriber-list-management
- https://help.shopify.com/en/manual/privacy-and-security/privacy/customer-privacy-settings/understanding-customer-privacy-settings

## Rückmeldung nach dem Absenden

Shopify leitet nach dem Absenden auf die Seite zurück und hängt den
Anker aus dem `action`-Attribut an. Der Dank-Absatz ist über
`#newsletter-danke:target` eingeblendet — ohne JavaScript, das in
Seiteninhalten ohnehin meist entfernt wird.

Sollte Shopify den `<style>`-Block entfernen, erscheint die Meldung
nicht; das Formular funktioniert trotzdem. Beim Rücklesen der Seite war
der Block vorhanden.

## Zu prüfen

1. Double Opt-in einschalten (siehe oben) — ohne das ist die Anmeldung
   rechtlich angreifbar.
2. Eine Testanmeldung mit eigener Adresse durchführen.
3. Den Verweis auf das Footer-Formular gibt es nicht mehr; falls im
   Theme ein Newsletter-Abschnitt im Footer fehlt, lohnt er sich dort
   zusätzlich — die Seite allein findet kaum jemand.

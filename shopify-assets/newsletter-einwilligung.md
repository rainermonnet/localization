# Nachträgliche Einwilligung einholen

Für den Teil des Verteilers, der von Hand aufgenommen wurde.

## Warum der Abmeldelink allein nicht genügt

Er ist **Pflicht**, keine Kulanz: § 7 Abs. 2 UWG und Art. 21 DSGVO
verlangen ihn in jeder Werbemail, auch bei einwandfrei eingeholter
Einwilligung. Shopify setzt ihn automatisch. Er macht aus einer
unzulässigen Zusendung keine zulässige — er ist nur die Bedingung
dafür, dass eine ohnehin zulässige zulässig bleibt.

Wer ohne Grundlage angeschrieben wird, hat den Verstoß bereits erlebt,
bevor er den Link sieht.

## Die zwei Gruppen

**Mit Bestellung.** Hier greift womöglich § 7 Abs. 3 UWG: Werbung für
eigene ähnliche Waren an Bestandskunden, ohne vorherige Einwilligung.
Vier Bedingungen müssen zusammen erfüllt sein:

1. Adresse stammt aus dem Verkauf einer Ware
2. Werbung für **eigene ähnliche** Waren — bei einem Spielzeugladen,
   der Spielzeugkäufern Spielzeugneuheiten schickt, unkritisch
3. Kein Widerspruch erfolgt
4. Hinweis auf das Widerspruchsrecht **bei der Erhebung** und **in
   jeder Mail**, kostenfrei außer Übermittlungskosten

Punkt 4 ist der Haken: Der Hinweis musste schon beim Einsammeln der
Adresse erfolgen. Wurde er das nicht, trägt die Ausnahme streng
genommen nicht.

**Ohne Bestellung.** Hier gibt es nichts, worauf man sich stützen
könnte. Persönliche Bekanntschaft ist keine Rechtsgrundlage, auch
nicht bei Stammkundschaft, die nur im Laden bar bezahlt hat, ohne dass
eine Bestellung erfasst wurde.

## Was zu tun ist

Eine **Einwilligungsmail** an die Gruppe ohne belegbare Grundlage.
Keine Werbung darin — sonst ist die Mail selbst schon der Verstoß,
den sie heilen soll.

Der heikle Punkt: Diese eine Mail ist rechtlich ebenfalls angreifbar.
In der Praxis wird sie als das mildere Mittel gegenüber fortgesetztem
Versand angesehen, rechtssicher ist sie nicht. Die ganz saubere
Alternative ist, diese Adressen stillzulegen und beim nächsten
Ladenbesuch oder Kauf um die Einwilligung zu bitten.

Die Entscheidung liegt beim Kaufmann, nicht beim Werkzeug. Bei
Unsicherheit über die Größenordnung lohnt eine Stunde Anwalt mehr als
jedes Skript — ich bin keiner, und das hier ist Einschätzung, keine
Rechtsberatung.

## Entwurf der Einwilligungsmail

> **Betreff:** Kurze Frage: Newsletter aus dem Zwergenladen — weiter so?
>
> Hallo [Vorname],
>
> Sie haben bei uns im Zwergenladen eingekauft, und wir haben Ihre
> E-Mail-Adresse in unseren Newsletter-Verteiler aufgenommen. Das war
> gut gemeint, aber wir haben Sie nie ausdrücklich gefragt. Das holen
> wir hiermit nach.
>
> Im Newsletter schreiben wir etwa einmal im Monat über Neuigkeiten
> aus dem Laden, Spielideen und besondere Produkte.
>
> **Wenn Sie ihn bekommen möchten, bestätigen Sie das bitte hier:**
> [Ja, ich möchte den Newsletter]
>
> Melden Sie sich nicht, hören Sie von uns nichts mehr — wir nehmen
> Sie dann aus dem Verteiler. Sie müssen also nichts tun, wenn Sie
> kein Interesse haben.
>
> Herzliche Grüße
> Rainer Monnet, Zwergenladen
> Schwimmbadstraße 36, Freiburg
>
> *Abmelden: [Link]*

Zwei Eigenschaften machen den Text brauchbar:

**Keine Werbung.** Kein Produkt, kein Angebot, kein Rabatt. Ein Rabatt
als Anreiz wäre naheliegend und genau falsch — dann ist es wieder eine
Werbemail.

**Schweigen bedeutet Nein.** Wer nicht klickt, fliegt raus. Die
umgekehrte Formulierung („Wenn wir nichts hören, schreiben wir
weiter") wäre eine Opt-out-Konstruktion und unwirksam.

## Danach aufräumen

Wer nicht bestätigt, wird auf `UNSUBSCRIBED` gesetzt — nicht gelöscht.
Der Datensatz bleibt als Beleg dafür, dass gefragt wurde. Löschen
vernichtet genau diesen Nachweis.

## Zur Opt-in-Stufe in Shopify

Shopify führt je Kunde `CONFIRMED_OPT_IN` oder `SINGLE_OPT_IN`.
`CONFIRMED_OPT_IN` behauptet, dieser Mensch habe einen
Bestätigungslink angeklickt.

Steht das bei jemandem, der von Hand eingetragen wurde, dokumentiert
die eigene Datenbank einen Vorgang, der nie stattgefunden hat. Im
Streitfall ist das schlechter als gar kein Eintrag: Es sieht aus wie
ein Beleg, hält aber keiner Nachfrage stand.

`newsletter-rechtslage.py` zählt aus, bei wie vielen Datensätzen das
zutrifft.

## Was danach gilt

Für alles Neue ist der Weg sauber: Formular auf
`/pages/newsletter` mit Pflichthäkchen, Double Opt-in eingeschaltet,
Bestätigungsmail. Was ab jetzt in den Verteiler kommt, ist belegt.

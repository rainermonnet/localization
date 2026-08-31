# Zwergenladen — Werbematerial und Texte

Gestaltung und Texte für Plakate, Postkarten, Aufkleber, Gutschein-, Danke- und
Reparaturkarten. Ohne Social Media und ohne Webseite.

**Zwergenladen** · Schwimmbadstraße 36 · 79100 Freiburg-Wiehre · 0761 1376456 ·
zwergenladen.info · seit 1998
Zwergenbilder © Barbara Monnet

## Dateien

| Datei | Inhalt |
| --- | --- |
| `konzept.html` | Das vollständige Konzept als eigenständige Seite. Schriften und Bilder sind eingebettet, die Datei läuft offline und lässt sich als PDF drucken. |
| `zwerge/zwerg-1-ruecken.png` | Freigestellter Zwerg von hinten (595 × 1000 px). Nur für den Einsatz im Laden. |
| `zwerge/zwerg-2-blick-nach-oben.png` | Freigestellt, 1000 × 1637 px. |
| `zwerge/zwerg-3-profil.png` | Freigestellt, 1800 × 1800 px — der größte und damit einzige, der bis A2 trägt. |
| `zwerge/zwerg-4-frontal.png` | Freigestellt, 600 × 1000 px. Die Leitfigur. |
| `zwerge/stempel-bestand.pdf` | Vorhandene Stempelvorlage. |
| `zwerge/stempel-strichfassung-2231px.png` | Die Strichzeichnung aus dem Stempel, aus dem PDF extrahiert. Vorlage für die Vektorisierung. |
| `zwerge/gemaelde-2012-vorderseite.jpg` | Das Gemälde aus dem Entwurf 2026, 3749 × 2711 px = 626 dpi im Endformat. |
| `zwerge/postkarte-*.pdf` und `.png` | Postkarte 11/2023 (Vorder- und Rückseite) und Adventskarte 2024 im Original. |
| `quelle/` | Bauquellen von `konzept.html`: Vorlage, Schriften und Skript. |
| `druck/postkarte-vorderseite.pdf` | Zwei Fassungen: S. 1 gerahmt mit 5 mm Papierrand, Signatur bleibt stehen; S. 2 randabfallend, Signatur wird angeschnitten. Vor dem Bestellen eine Seite löschen. |
| `druck/postkarte-rueckseite.pdf` | Rückseite, 148 × 105 mm + 2 mm Beschnitt. |
| `druck/visitenkarte.pdf` | 85 × 55 mm + 2 mm Beschnitt, zwei gleiche Karten zu 85 × 27,5 mm mit Schnittmarken für den Mittelschnitt. |
| `druck/gutschein.pdf` | 95 × 95 mm + 2 mm Beschnitt, zweiseitig, Ecken gerundet r = 5 mm, Code-128-Barcode. |
| `druck/flagge.pdf` | Zwei Aufstellerflaggen, Entwurf im Maßstab 1:10 für 60 × 200 cm. |

## Druckdateien neu bauen

Die Vorlagen sind HTML mit Millimeterangaben, gebaut wird über Chromium:

```
pip install pillow playwright
python3 druck/bauen.py
```

Farbraum ist RGB. Die meisten Onlinedruckereien wandeln selbst nach CMYK; wer ein
CMYK-PDF verlangt, konvertiert die fertigen Dateien.

## konzept.html neu bauen

Texte und Layout stehen in `quelle/vorlage.html`. Nach einer Änderung:

```
pip install pillow
python3 quelle/build.py
```

Das schreibt `konzept.html` neu — eine eigenständige Datei mit eingebetteten
Schriften und Bildern, die offline läuft und sich im Browser als PDF drucken lässt.
Netz wird nicht gebraucht, die Schriften liegen in `quelle/schriften.json` bei.

## Der Kern

**Der Rückenzwerg ist raus.** Ein abgewandter Rücken ist die Körpersprache von jemandem,
der keine Zeit hat — als erste Aussage über einen kleinen Laden ist das die falsche.

An seiner Stelle steht **Auf Augenhöhe**: Der Zwerg steht auf Kinderhöhe und sieht den
Betrachter an. Daraus drei Regeln:

1. Jeder Zwerg, der nach außen zeigt, hat ein Gesicht. Die Rückenansicht darf nach innen.
2. Der Zwerg steht auf der orangen Linie, nie darüber.
3. Ein Blick pro Fläche.

Der Aufbau aus grauer Wand und orangem Boden stammt von der Postkarte 11/2023 und bleibt.
Er ist Barbara Monnets Entwurf, nicht meiner.

## Was aus dem Bestandsmaterial folgt

- **Hausschrift ist Avenir** (Black und Book), nicht Fraunces wie im ersten Entwurf
  vorgeschlagen. Avenir ist lizenzpflichtig; Empfehlung ist behalten, solange nur wenige
  Stücke gesetzt werden. Kostenfreie Alternative mit sehr ähnlichen Proportionen: Mulish.
- **Eine einfarbige Strichfassung existiert bereits** im Stempel und ist gut. Sie liegt
  aber als Pixelbild vor, nicht als Vektor — das ist die einzige echte Lücke. Diese
  Zeichnung vektorisieren lassen, statt eine neue zu entwerfen.
- **Die Stempelzeile ist zu lang.** `www.zwergenladen.info / email@zwergenladen.info` sind
  47 Zeichen; bei 40 mm Stempelbreite laufen die Punzen im Gummi zu. Kürzen auf
  `zwergenladen.info`.
- **Auflösung:** Die Freisteller reichen bei 300 dpi bis rund 150 mm Höhe. Für A1 reicht
  keiner. Falls die Originalgemälde existieren, löst ein 600-dpi-Scan das dauerhaft.

## Farben

Aus der Postkartendatei ausgelesen, nicht geschätzt.

| Farbe | HEX | Einsatz |
| --- | --- | --- |
| Bodenorange | `#F3390A` | nur die Bodenzone, nie hinter Lesetext |
| Mützenrot | `#CF2634` | kleine Marken, max. 10 % Fläche |
| Wandgrau | `#C8C7C6` | die große Ruhefläche |
| Leinen | `#CCB9A1` | Zwischentöne, Papierwahl |
| Adventblau | `#273465` | nur November bis Dezember |
| Kohle | `#23211D` | aller Text, alle Linien |

Orange und Rot berühren sich nie direkt. Text steht nie auf Orange.

## Offene Entscheidungen

1. Sie oder Du — gesetzt ist Sie.
2. Avenir lizenzieren oder auf Mulish wechseln.
3. Stimmt die Negativliste wörtlich? Plastik, Batterien, Bildschirme — alle drei?
4. Reparaturkarte ja oder nein. Sie ist der beste Beweis im Konzept und die einzige
   Zusage darin.
5. Gibt es die Gemälde im Original?
6. Wie soll Barbara Monnet genannt werden?

Hinweise zu Sondernutzungserlaubnis, Gutscheinverjährung und Werbeaussagenrecht sind
sorgfältig recherchiert, aber keine Rechtsberatung.

# Würfelgürtel v3: einteilig gedruckt (Print-in-Place)

Gebaut in der Machart des „origami transforming cube“: Alle 6 Glieder liegen flach auf dem Bett, und die Gelenke werden
gleich mitgedruckt. Die Waben auf der Bettseite sind nach dem Zusammenklappen außen.

## Prinzip

Beim Schatz-Würfelgürtel liegen die beiden Gelenkkanten eines Glieds windschief zueinander, gegenüber und um 90° gedreht.
Deshalb können nicht alle Gelenke flach auf dem Bett liegen wie in der Vorlage. Die Lösung ist eine abwechselnde Lage:
Jedes Glied liegt auf einer Außenfläche. Die Gelenke 1, 3 und 5 liegen flach auf dem Bett. Die Gelenke 2 und 4 stehen
senkrecht; ihre Knöchel haben 45°-Kegelflächen und tragen sich deshalb selbst. Gelenk 6 bleibt offen und wird nach dem Druck
mit einem Stück 1,75-mm-Filament geschlossen.

## Dateien

| Datei | Inhalt |
|---|---|
| `Wuerfelguertel_einteilig_A1_weiss.3mf` | **Bambu-Studio-Projekt mit fertigen Schnell-Einstellungen**, Filamentfarbe weiß |
| `Wuerfelguertel_einteilig_A1_holz.3mf` | dasselbe für Holzfilament |
| `Wuerfelguertel_einteilig_A1_weiss_holz_wechsel.3mf` | **zweifarbig: Glieder 1, 3, 5 weiß, Glieder 2, 4, 6 Holz** (braucht das AMS lite) |
| `…_Teil_weiss.stl` und `…_Teil_holz.stl` | dieselben Glieder als zwei passgenaue STL-Dateien (Ersatz, falls das Zweifarben-Projekt nicht lädt) |
| `Wuerfelguertel_einteilig_A1_Spiel05.stl` | nur das Modell, falls du die Einstellungen selbst machst |

Gelenkspiel 0,5 mm, Bolzen Ø 2,4 mm. Größe 147 × 147 × 39 mm, 6 ineinandergreifende Glieder, Waben außen.
Die Datei bereits richtig ausgerichtet lassen: nicht drehen, nicht skalieren.

## Schnell-Einstellungen (in den 3MF-Projekten schon eingetragen)

| Einstellung | Wert | statt vorher |
|---|---|---|
| Schichthöhe | 0,24 mm | 0,20 mm |
| Wände | 2 | 3 |
| Deckschichten oben / unten | 4 / 3 | 5 / 3 |
| Füllung | 10 % Blitz (Lightning) | 15 % |
| Stützen | aus | |
| Brim | nur außen, 5 mm | |
| Elefantenfuß-Kompensation | 0,15 mm | |
| Platte | Textured PEI | |

Damit sinkt die Druckzeit nach meiner Schätzung von etwa 4 bis 5 h auf etwa 2½ bis 3 h. Bambu Studio zeigt die genaue Zeit.
Die Blitzfüllung stützt nur die Deckflächen und spart am meisten Material. Knöchel und Bolzen werden ohnehin massiv gedruckt.

**Filament wählen:** Nach dem Öffnen links unter „Filament“ das tatsächlich eingelegte Material auswählen,
also „Bambu PLA Basic“ (weiß) oder „Bambu PLA Wood“ bzw. dein Holzfilament. Erst dann gelten dessen Temperaturen
und Geschwindigkeitsgrenzen.

**Holzfilament:** Es sieht mit den Waben schön aus, ist aber spröder und zieht mehr Fäden. Nach dem Druck die
Gelenke besonders behutsam lösen. Beim A1 die 0,4-mm-Düse verwenden, nicht 0,2 mm. Den Drucker nicht lange heiß warten lassen,
sonst verstopft die Düse.

**Weiß und Holz im Wechsel (3 + 3 Glieder):** Das geht nur mit dem **AMS lite**, denn der A1 wechselt dann
in fast jeder Schicht die Farbe, bis 34 mm Höhe etwa 140-mal. Darüber druckt er nur noch Holz.
- Das Projekt `…_weiss_holz_wechsel.3mf` hat Filament 1 = weiß und Filament 2 = Holz. Nach dem Öffnen bei Filament 2 dein
  Holzprofil wählen. Die Farbe ist nur zur Ansicht eingetragen.
- Der Reinigungsturm ist an. Das Spülen geht soweit möglich in die Füllung.
- Ein Farbwechsel dauert etwa eine Minute. Rechne mit grob 2 bis 3 h zusätzlich und etwa 40 bis 70 g Spülabfall.
  Bambu Studio zeigt beides nach dem Slicen genau an.
- Lädt das Zweifarben-Projekt nicht, beide `…_Teil_…stl` gleichzeitig importieren und die Frage „als ein Objekt mit mehreren
  Teilen laden?“ mit Ja beantworten. Dann rechts jedem Teil sein Filament zuweisen. Die Lage stimmt bereits.

**Alternative mit nur einem Wechsel:** Am Schichtregler bei 0,68 mm „Filament wechseln“ setzen. Dann haben die Waben auf
den Bettseiten Holzstege mit weißem Grund.

## Nach dem Druck

1. Die Kette vorsichtig von der Platte lösen.
2. Jedes Gelenk sanft hin und her bewegen, bis es frei läuft.
3. Ring schließen: Die Knöchel von Glied 6 und Glied 1 ineinanderlegen und ein Stück 1,75-mm-Filament (ca. 33 mm)
   durch die 2-mm-Bohrung schieben. Die Enden mit einem Tropfen Sekundenkleber sichern.
4. In der Würfellage zeigen die Waben nach außen.

## Geprüft

- Die STL-Datei ist wasserdicht und hat keine offenen Kanten.
- In der Drucklage berühren sich die Glieder nicht. Der kleinste Abstand ist 0,49 mm.
- Alle 1359 Stellungen der Umstülpung wurden am Modell durchgerechnet: Es gibt keine Berührung.
- Jedes Gelenk erreicht vom Druckwinkel aus den ganzen Bewegungsbereich. Es kann sich um 254° frei drehen.

## Maße und Toleranzen

Würfelkante 70 mm. Die Außenflächen sind um 2,6 mm nach außen versetzt, damit die Gelenkachse über dem Bett liegt.
Knöchelradius 3 mm, Bolzen Ø 2,4 mm, Spiel 0,5 mm (auch senkrecht zu den Kegelflächen).

---
**Achtung, nicht mehr empfohlen:** Der Druck von v3 ist gescheitert. Die stehenden Gelenke 2 und 4 haben am unteren Knöchelrand
kein Material darunter und werden zu Spaghetti. Bitte die zuverlässige Bauweise in `../wuerfelguertel-v4-zuverlaessig/` verwenden.

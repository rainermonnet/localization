# Bambu Studio: Einstellungen für die Oloide mit Stützwänden (A1, PLA)

## 1. Auf die Werkseinstellungen zurück
- Drucker: **Bambu Lab A1 0.4 nozzle**
- Filament: **Bambu PLA Basic @BBL A1M** (oder das PLA, das du verwendest)
- Prozess: **0.16mm Optimal @BBL A1M**
- Steht hinter einem Preset „geändert“ bzw. ein Sternchen: das System-Preset neu auswählen und die Änderungen verwerfen.

## 2. Nur diese Werte ändern (Prozess)
| Reiter | Einstellung | Wert |
|---|---|---|
| Qualität | Schichthöhe | 0,16 mm (aus dem Preset) |
| Qualität | Naht | Ausgerichtet |
| Festigkeit | Wandschleifen | 3 |
| Festigkeit | Obere / untere Schalenschichten | 5 / 3 |
| Festigkeit | Fülldichte / Muster | 15 % / Gyroid |
| Geschwindigkeit | alles | Werte des Presets lassen; bei hohen Oloiden höchstens Außenwand auf 150 mm/s |
| Stützen | Stützen aktivieren | **aus** (die Stützwände sind im Modell) |
| Andere | Brim | nur außen, 3–5 mm |

## 3. Kühlung (Filament-Einstellungen)
- „Langsamer drucken für bessere Schichtkühlung“: **an**
- Mindest-Schichtzeit: **8–10 s**
- Bauteillüfter: 100 % ab Schicht 2

Das ist der wichtigste Punkt gegen Spaghetti an der dünnen Spitze: dort sind die Schichten so klein, dass sie ohne Mindest-Schichtzeit nicht abkühlen.

## 4. Tipps
- Zwei Oloide gleichzeitig drucken verlängert die Zeit je Schicht an der Spitze.
- Fadenloch nach dem Druck bohren: 0,6–0,8 mm Bohrer im Handbohrer, mittig auf dem oberen Grat, etwa 6 mm tief entlang der Achse.
- Vor dem nächsten Druck Düse von Fadenresten säubern.

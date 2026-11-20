# Würfelgürtel v2: Probedruck für den Bambu Lab A1

Neuanfang nach dem fehlgeschlagenen Druck (Glieder standen auf einer Kante).
Das neue Prinzip stammt aus dem Video: Die Tetraeder liegen flach, die Gelenke sind
eigene kleine Scharniere, die in Taschen geklebt werden. Die Flächen tragen Bienenwaben.

## Dateien

Waben nur **außen**: auf den beiden Flächen, die in der Würfellage auf der Würfeloberfläche liegen.
Eine davon ist die Bettfläche. Ihre Waben (0,6 mm tief) druckt der A1 direkt auf die PEI-Platte.
Ein 3 mm breiter glatter Rand bleibt für die Haftung. Die Innenflächen mit den Scharniertaschen sind glatt.

| Datei | Inhalt |
|---|---|
| `Platte1_A1_6_Glieder.stl` | alle 6 Glieder auf einer Platte (A–B–A–B–A–B) |
| `Platte2_A1_6_Scharniere_Spiel_0.4.stl` | 6 Scharniere, Spiel 0,4 mm |
| `Glied_1_A.stl` … `Glied_6_B.stl` | die Glieder einzeln; A und B sind Spiegelbilder |
| `Scharnier_Spiel_0.3.stl` … `_0.5.stl` | einzelne Scharniere zum Ausprobieren |
| `Probedruck_A1_2Glieder_3Scharniere.stl` | Glied 1 und 2 und 3 Probe-Scharniere |
| `Wuerfelguertel-v2-alle-Glieder.png` | Übersichtsblatt |
| `quellen/` | Python-Skripte (Geometrie, Kollisionsprüfung, Export) |

Maße: Würfelkante 70 mm, Glied 65 × 33 × 33 mm, Scharnier 25 × 28 × 5,6 mm.

## Bambu Studio (A1, 0,4-mm-Düse, PLA Basic)

- Profil **0.20mm Standard @BBL A1**. Geschwindigkeit nicht herabsetzen.
- Wände 3, Deckschichten oben 5, unten 3, Füllung 15 % Gyroid
- **Stützen aus.** **Brim: „Nur äußerer Rand“, 5 mm** (nach dem ersten Fehldruck: die spitzen Ecken und die kleinen Scharniere lösen sich sonst)
- In Bambu Studio als Plattentyp **Textured PEI Plate** wählen (PLA: Bett 65 °C). Bei „Cool Plate“ bleibt das Bett zu kalt.
- Im Druckdialog **Druckbett-Nivellierung** einschalten
- Platte reinigen: warmes Wasser mit Spülmittel (keine Handseife), weiche Bürste, gründlich klar spülen,
  mit fusselfreiem Papier trocknen, danach nicht mehr mit den Fingern anfassen. Zwischen den Drucken mit Isopropanol abwischen.
- Die STL-Dateien liegen bereits richtig herum. Nicht drehen.
- Druckzeit: Platte 1 ca. 3 h, Platte 2 ca. 30 min. Bambu Studio zeigt die genaue Zeit.

## Zusammenbau

1. Die drei Probe-Scharniere vorsichtig durchbewegen. Nimm das kleinste Spiel, das ohne Haken läuft.
2. Eine Lasche kommt in die Tasche der **schrägen** Fläche von Glied A. Die andere Lasche kommt in die Tasche der
   **senkrechten** Fläche von Glied B. Die Taschen sitzen außermittig auf der Kante, deshalb passt nur eine Lage.
3. Sekundenkleber-Gel nur hinten auf den Taschenboden geben, nie an die Walze. 30 s andrücken.
4. Reihenfolge Glied 1–2–3–4–5–6: Ein Scharnier verbindet die schräge Tasche von Glied n mit der senkrechten Tasche von Glied n+1. Scharnier 6 verbindet Glied 6 mit Glied 1 und schließt den Ring.

## Geprüft

- Alle STL-Dateien sind wasserdicht und haben keine offenen Kanten.
- Alle 1359 Stellungen der Umstülpung wurden am 3D-Modell durchgerechnet. Glieder und Scharniere berühren
  sich nie. Auch mit 0,3 mm dickeren Gliedern gibt es keine Berührung.

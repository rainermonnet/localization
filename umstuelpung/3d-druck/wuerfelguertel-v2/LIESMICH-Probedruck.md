# Würfelgürtel v2: Probedruck für den Bambu Lab A1

Neuanfang nach dem fehlgeschlagenen Druck (Glieder standen auf einer Kante).
Das neue Prinzip stammt aus dem Video: Die Tetraeder liegen flach, die Gelenke sind
eigene kleine Scharniere, die in Taschen geklebt werden. Die Flächen tragen Bienenwaben.

## Dateien

| Datei | Inhalt |
|---|---|
| `Probedruck_A1_2Glieder_3Scharniere.stl` | **Zuerst drucken.** Glied A, Glied B, dazu 3 Scharniere mit Spiel 0,3 / 0,4 / 0,5 mm |
| `Vollsatz_A1_6Glieder_6Scharniere.stl` | ganzer Gürtel auf einer Platte (Scharniere mit Spiel 0,4 mm) |
| `Glied_A_3x.stl`, `Glied_B_spiegel_3x.stl` | Einzelteile; je 3× drucken (B ist das Spiegelbild von A) |
| `Scharnier_Spiel_0.3.stl` … `_0.5.stl` | Einzelne Scharniere, 6× im passenden Spiel |
| `Wuerfelguertel-v2-Probedruck.png` | Übersichtsblatt |
| `quellen/` | Python-Skripte (Geometrie, Kollisionsprüfung, Export) |

Maße: Würfelkante 70 mm, Glied 65 × 33 × 33 mm, Scharnier 25 × 28 × 5,6 mm.

## Bambu Studio (A1, 0,4-mm-Düse, PLA Basic)

- Profil **0.20mm Standard @BBL A1**. Geschwindigkeit nicht herabsetzen.
- Wände 3, Deckschichten oben 5, unten 3, Füllung 15 % Gyroid
- **Stützen aus.** Brim aus. Löst sich die spitze Ecke vom Bett, nimm Brim 3 mm.
- Textured-PEI-Platte, vorher mit Spülmittel waschen
- Die STL-Dateien liegen bereits richtig herum. Nicht drehen.
- Druckzeit: Probedruck ca. 1 bis 1½ h, Vollsatz ca. 3 bis 4 h. Bambu Studio zeigt die genaue Zeit.

## Zusammenbau

1. Die drei Probe-Scharniere vorsichtig durchbewegen. Nimm das kleinste Spiel, das ohne Haken läuft.
2. Eine Lasche kommt in die Tasche der **schrägen** Fläche von Glied A. Die andere Lasche kommt in die Tasche der
   **senkrechten** Fläche von Glied B. Die Taschen sitzen außermittig auf der Kante, deshalb passt nur eine Lage.
3. Sekundenkleber-Gel nur hinten auf den Taschenboden geben, nie an die Walze. 30 s andrücken.
4. Vollsatz: Reihenfolge A–B–A–B–A–B, immer schräg → senkrecht. Das sechste Scharnier schließt den Ring.

## Geprüft

- Alle STL-Dateien sind wasserdicht und haben keine offenen Kanten.
- Alle 1359 Stellungen der Umstülpung wurden am 3D-Modell durchgerechnet. Glieder und Scharniere berühren
  sich nie. Auch mit 0,3 mm dickeren Gliedern gibt es keine Berührung.

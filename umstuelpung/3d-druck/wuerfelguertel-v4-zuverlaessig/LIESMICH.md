# Würfelgürtel v4: zuverlässige Bauweise

Nach dem dritten Fehldruck (v3, einteilig): Die stehenden Druckgelenke von v3 hatten an ihrem unteren Rand kein Material
darunter und wurden zu Spaghetti. Der Fehler liegt im Entwurf. v4 verzichtet deshalb ganz auf Druckgelenke in den Gliedern.

## Prinzip

- **Glieder:** massive Tetraeder ohne Gelenkteile. Jedes liegt flach auf seiner Außenfläche. Waben außen, Stützen keine.
  Sie haben nur zwei Taschen für die Scharniere. Diese Form hat bei dir schon sauber gedruckt.
- **Scharniere:** klassische, flach gedruckte Print-in-Place-Scharniere mit waagrechter Achse, Spiel 0,5 mm.
  Diese Bauart gilt als die zuverlässigste. Sie werden in die Taschen geklebt.
- **Farben ohne AMS-Wechsel:** Jede Platte hat nur eine Farbe. Glieder 1, 3, 5 sind weiß, Glieder 2, 4, 6 Holz.
  Es gibt keinen Spülabfall.
- Alle 1359 Stellungen der Umstülpung wurden am Modell mit 0,5 mm Spiel geprüft: Es gibt keine Berührung.

## Reihenfolge

| Schritt | Datei | Filament | Zeit (geschätzt) |
|---|---|---|---|
| 1 | `Test_1_Scharnier_Spiel_0.5.3mf` | weiß | ca. 10 min |
| 2 | `Platte_A_Glieder_1-3-5_weiss.3mf` | weiß | ca. 1–1½ h |
| 3 | `Platte_B_Glieder_2-4-6_Holz.3mf` | Holz | ca. 1–1½ h |
| 4 | `Platte_C_6_Scharniere_Spiel_0.5_weiss.3mf` | weiß | ca. 30–40 min |

**Zuerst Schritt 1:** Das Testscharnier muss sich nach dem Abnehmen mit leichtem Druck frei bewegen lassen.
Erst dann geht es mit den anderen Platten weiter. Zu jeder 3MF-Datei liegt auch die STL-Datei bei.

## Einstellungen (in den 3MF-Projekten eingetragen)

- Glieder: 0,24 mm Schichthöhe, 2 Wände, 10 % Blitzfüllung, Brim nur außen 5 mm, Stützen aus, Textured PEI
- Scharniere: 0,20 mm Schichthöhe (feiner für das Gelenkspiel), sonst gleich
- Nach dem Öffnen links das eingelegte Filament wählen: „Bambu PLA Basic“ für weiß oder dein Holzprofil.
- Wenn das AMS beide Rollen hat: in Bambu Studio nur das jeweils passende Filament verwenden. Dann wechselt der Drucker nie.

## Zusammenbau

1. Scharniere durchbewegen.
2. Eine Lasche kommt in die Tasche der **schrägen** Fläche von Glied n, die andere in die Tasche der **senkrechten** Fläche von Glied n+1.
   Die Taschen sitzen außermittig, deshalb passt nur eine Lage.
3. Sekundenkleber-Gel nur hinten auf den Taschenboden geben, nie an die Walze. 30 s andrücken.
4. Reihenfolge 1 (weiß) – 2 (Holz) – 3 (weiß) – 4 (Holz) – 5 (weiß) – 6 (Holz). Das sechste Scharnier verbindet Glied 6 mit Glied 1.

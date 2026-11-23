# Würfelgürtel v5: sechs Einzelglieder, Gelenke angeformt, ohne Kleber

## Prinzip

Jedes Glied liegt beim Druck auf einer Außenfläche und trägt an seinen beiden Gelenkkanten:

- **Walze** an der Kante, die auf dem Bett liegt: ein waagrechter Zylinder, der flach auf dem Bett aufliegt.
  Er hat eine Bohrung für den Stift (Presssitz).
- **Lagersäule** an der senkrechten Kante: Sie wächst direkt vom Bett nach oben. Sie hat eine Spielbohrung für den Stift
  und unten eine Senkung für den Stiftkopf.

Verbunden wird mit einem **Drahtstift 2,0 × 35 mm**. Du schiebst ihn von unten durch die Säule des einen Glieds und drückst
ihn in die Walze des Nachbarglieds. In der Walze sitzt der Stift fest, in der Säule dreht er sich. Der Kopf verhindert,
dass sich das Gelenk auseinanderzieht. Es gibt keinen Kleber und keine Wartezeit.

## Warum es diesmal druckbar ist

v3 ist gescheitert, weil die unteren Ränder der stehenden Knöchel in der Luft begannen. v5 hat keine solchen Stellen:

- Die Walze liegt auf dem Bett.
- Die Säule beginnt auf dem Bett.
- Die Nut über der Säule ist nach oben offen.
- Der Kanal unter der Walze des Nachbarn hat ein 45°-Dach.

Eine schichtweise Prüfung zeigt: Kein Material beginnt ohne Auflage. Dieselbe Prüfung meldet bei v3 genau die
Knöchelränder, die beim Druck zu Spaghetti wurden.

Außerdem wurden alle 1359 Stellungen der Umstülpung mit eingesetzten Stiften durchgerechnet: Es gibt keine Berührung.

## Dateien

| Datei | Inhalt |
|---|---|
| `Probe_Glied_1_und_2.3mf` | **zuerst:** Glied 1 und Glied 2 in weiß, zum Testen eines Gelenks |
| `Platte_Glieder_1-3-5_weiss.3mf` | 3 Glieder weiß |
| `Platte_Glieder_2-4-6_Holz.3mf` | 3 Glieder Holz |
| `Glied_1_weiss.stl` … `Glied_6_Holz.stl` | die Glieder einzeln |
| gleichnamige `.stl` zu jeder `.3mf` | falls du die Einstellungen selbst machst |

Jede Platte hat nur eine Farbe. Der Drucker wechselt nie das Filament, es gibt keinen Spülabfall.

## Einstellungen (in den 3MF eingetragen)

0,24 mm Schichthöhe, 2 Wände, 10 % Blitzfüllung, Brim nur außen 5 mm, Stützen aus, Textured PEI.
Nach dem Öffnen links das eingelegte Filament wählen.

## Zusammenbau je Gelenk

1. Die Walze von Glied n auf die Säule von Glied n+1 setzen, sodass die Bohrungen fluchten.
2. Den Drahtstift von unten (Außenseite) durch die Säule in die Walze drücken, mit Zange oder Schraubstock,
   bis der Kopf in der Senkung liegt.
3. Reihenfolge 1–2–3–4–5–6. Das sechste Gelenk verbindet Glied 6 mit Glied 1.

**Tipps:**
- Geht der Stift zu schwer in die Walze, die Bohrung einmal mit einem 1,9-mm-Bohrer nachziehen.
- Sitzt er zu locker, mit 2,1 mm statt 2,0 mm Stift arbeiten oder einen Tropfen Sekundenkleber an die Spitze geben.
- Holzfilament ist spröder: Den Stift langsam eindrücken.

## Maße

Würfelkante 70 mm, Außenflächen um 2,6 mm nach außen versetzt. Glied 78 × 37 × 34 mm.
Walze und Säule Ø 6 mm, Spiel zwischen ihnen 0,5 mm. Bohrung Walze Ø 2,0 mm (Presssitz), Bohrung Säule Ø 2,3 mm,
Senkung für den Kopf Ø 4,8 × 1,4 mm.

# Bildgröße 500 × 500 (Merchant Center, Frist 31.01.2027)

STAND 2026-11-10 · Grundlage: `bildgroesse-pruefen.py` (80 Produkte mit Titelbild unter 500 Pixel)

## Erledigt: 47 Produkte
Pro Produkt wurde ein neues Bild hinzugefügt und an Position 1 gestellt. **Die alten kleinen
Bilder liegen weiter dahinter, gelöscht wurde nichts.**

| Quelle | Anzahl | Produkte | Zuordnung |
|---|---|---|---|
| grapat.eu | 8 | 15-101, 16-138, 22-235, 24-260, 18-178, 18-201, 24-256, 15-109 | Artikelnummer |
| ostheimer.de | 4 | Delfin hoch (2292), Delfin tief (2293), Esel bockend (11202), Papagei bunt (21403) | SKU |
| Mercurius | 4 | Stockmar Wachsmalblöcke (8 ohne schwarz, 8 mit schwarz Blechetui, 16 Farben, Kombisortiment) | Produktname + Bild |
| gokitoys.com (goki Download-Center) | 8 | Microbus 1962 (12030), Isetta (12307), Stempelkissen (15346), Microbus 1963 (12338), Autotransporter (55860), Koffer (51444), Pfützenschiffchen (63873), Greifling 4 Ringen (65322) | Artikelnummer/EAN, Isetta über Farbbeschreibung |
| sonett.eu | 16 | alle Sonett-Produkte der Liste | SKU = Sonett-Artikelnummer, Preisliste PS02 bestätigt |
| henrys-online.de | 5 | Bumerang Spirit, V-Shape, Diabolo Handstäbe, Yo-Yo Lizard rot/blau | Artikelnummer; Originale nur 500 px, auf weiße Fläche 560 × 560 gelegt (nicht vergrößert) |
| cuboro.ch / nebotools.co.uk | 2 | Cuboro Standard 50, Nebo BIG LARRY 2 | Produktname |

Außerdem schon vorher: Grapat 10 Spielzeuge aus Drive (siehe oben), Lyra/Stockmar 7 Produkte (Mercurius).

## Bewusst nicht angefasst: 33 Produkte
Auftrag vom 2026-11-10: „alle anderen Produkte lassen wir so".

| Gruppe | Anzahl | Grund |
|---|---|---|
| Kendama/Mayaflaya | 7 | kein Lager, keine Herstellerseite freigegeben |
| Aurich (Aeronaut, Kaleidoskop, Balu) | 3 | Lieferant insolvent |
| Kraul | 2 | keine Herstellerseite freigegeben |
| Grapat ohne eindeutige Nummer | 4 | siehe unten |
| goki: VW Käfer 1967, Kaleidoskop, Greiflinge (Regenbogen, Elastik Stern), Schnullerkette Regenbogen, Schwimmtier, Kubb XL, Wohnwagen-Set | 8 | Nummer fehlerhaft oder Modell bei goki nicht eindeutig (Kandidat Käfer: 12345 Blumenmuster) |
| Henrys Bumerang Jaguar Links (A04083) | 1 | bei Henrys nur Rechtshänder-Version (A04082) |
| Eigene Produkte: Purzelbube, Purzelzwerg groß/klein, Eurythmieschuhe | 4 | keine Herstellerquelle, eigene Fotos nötig |
| Käthe Kruse Toni | 1 | kein Lager |
| Waldow Wildkräuter-Quartett, Nic Klein-Ausstecher | 2 | keine Hersteller-Adresse gefunden |
| Ferby Vielfarben einzeln (Lager 7) | 1 | keine SKU, Mercurius-Seite nicht geprüft |

### Grapat, vier Produkte
`Baby Zwerge & Schale` (15259367571829), `Vögelspielzeug Birds` (15259349746037),
`Mates Töpfe 6 farbig` (15259372552565), `Mates Töpfe natur` (15567464989045, beide SKU 18-183).
Die EANs im Shop (8436580…) stehen nicht auf den Grapat-Seiten, die Beschreibungen sind
Fließtext ohne Packungsgröße. Eine Zuordnung wäre geraten. `Birds` überschneidet sich mit den
drei Einzelprodukten Chill Pink / Mellow Orange / Flowing Yellow (dort sind die Bilder gesetzt).

## Datenfehler, die dabei auffielen (nicht korrigiert)
- Käfer, Isetta und Wohnwagen-Set tragen dieselbe SKU 4013594120303/…304.
- „Schnullerkette Regenbogen": SKU 65358 ist bei goki die „Schnullerkette Van".
- „Greifling Regenbogen": SKU 65354 gibt es bei goki nicht.
- Cuboro Standard 50: EAN im Shop 4032066011603, auf cuboro.ch eine andere.
- Nebo BIG LARRY 2: Hersteller ist Nebo, im Shop steht Herbertz (= Vertrieb).

## Netzwerk-Freigaben (Default-Umgebung)
`goki.eu`, `gokitoys.com`, `sonett.eu`, `henrys-online.de`, `cuboro.ch`, `nebotools.co.uk`
(zusätzlich zu mercurius-deutschland.de, grapat.eu, ostheimer.de u. a.).

## Prüfen
`python3 bildgroesse-pruefen.py` erneut ausführen: Erwartet sind rund 33 Produkte mit zu kleinem Titelbild.

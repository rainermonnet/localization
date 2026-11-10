# Google Merchant Center – Feed-Regeln

Ergänzt fehlende Pflichtattribute für zwei Produktgruppen:
**Eurythmieschuhe** und **KISME-Schmuck**.

---

## A · Eurythmieschuhe

### Fehlende Attribute

| Attribut | Problem |
|---|---|
| `age_group` | fehlt → Pflichtfeld für Bekleidung/Schuhe in DE |
| `size` | fehlt → Pflichtfeld für Schuhe (Schuhgröße) |
| `gender` | empfohlen (meist unisex) |

### Feed-Regeln einrichten

**Merchant Center → Feed → Regeln → Regelbereich → Regel hinzufügen**

#### Regel 1 – age_group

```
Wenn:      [Produkt-ID / Titel] enthält "Eurythm"
Dann:      age_group = adult
```

#### Regel 2 – size (aus Titel extrahieren)

Die Größe steht im Titel, z.B. "Eurythmieschuhe Gr. 38".

```
Wenn:      [Titel] enthält "Eurythm"
Dann:      size = [Titel] → Wert extrahieren mit RegEx: "Gr\.?\s*(\d+)"
```

Falls der Titel keine Größe enthält, muss die Größe im Shopify-Produkt
als Varianten-Attribut (Größe) gepflegt sein → erscheint automatisch im Feed.

#### Regel 3 – gender

```
Wenn:      [Titel] enthält "Eurythm"
Dann:      gender = unisex
```

### Alternative: direkt in Shopify pflegen

In Shopify Admin → Produkt → Variante → Google Kanal:
- Altersgruppe: Erwachsene
- Geschlecht: Unisex
- Größentyp: Normal

Das ist nachhaltiger als Feed-Regeln und wirkt sofort.

---

## B · KISME-Schmuck (Börse, Stimmungsketten, Armbänder)

### Fehlende Attribute

| Attribut | Problem |
|---|---|
| `age_group` | fehlt → required für Accessoires in DE |
| `color` | fehlt → stark empfohlen (verbesserter Traffic) |
| `gender` | fehlt → empfohlen |

### KISME-Produkt-IDs (Welle 2)

```
15912756937077  Börse Sommerfarben
15912714666357–15912714797429  Stimmungsketten (7 Stück)
15912756838773  Stimmungsring Einhorn
15912715223413–15912715354485  Armbänder (5 Stück)
```

### Feed-Regeln einrichten

#### Regel 1 – age_group (alle KISME-Produkte)

KISME-Produkte haben "KISME" im Titel oder im Vendor-Feld.

```
Wenn:      [Hersteller / Vendor] = "KISME"   ODER
           [Titel] enthält "Stimmung"         ODER
           [Titel] enthält "Armband"          ODER
           [Titel] enthält "Börse"
Dann:      age_group = adult
```

#### Regel 2 – color (aus Titel extrahieren)

Die Farbe steht meistens im Variantentitel (z.B. "Sommerflieder", "Smaragdgrün").

```
Wenn:      [Hersteller / Vendor] = "KISME"
Dann:      color = [Variantentitel]   (= option1 im Shopify-Feed)
```

Falls kein Variantentitel vorhanden:
```
Dann:      color = bunt
```

#### Regel 3 – gender

```
Wenn:      [Hersteller / Vendor] = "KISME"
Dann:      gender = female
```

(KISME-Schmuck richtet sich überwiegend an Mädchen/Frauen.)

---

## Wo Feed-Regeln im Merchant Center anlegen

1. **Merchant Center → Produkte → Feeds**
2. Primären Feed (shopify_DE_…) anklicken
3. Tab **"Regeln"** → **"Neue Regel"**
4. Bedingung + Aktion wie oben eingeben
5. **Speichern & Anwenden**

Nächster automatischer Feed-Abruf: innerhalb von 24 Stunden.  
Manuell beschleunigen: Feed → **"Jetzt abrufen"**.

---

## Prüfung nach Anwendung der Regeln

**Merchant Center → Produkte → Diagnose**
- Filter: "Fehlende Attribute"
- Prüfen ob `age_group`, `size`, `color`, `gender` nicht mehr rot erscheinen

Bei Eurythmieschuhen zusätzlich:
- **Merchant Center → Produkte → [Produkt wählen] → Attribute-Tab**
- Attribute `size` sollte mit Schuhgröße befüllt sein

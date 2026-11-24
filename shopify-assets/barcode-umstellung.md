# Barcode-Feld: Umstellung vorbereitet

Shopify hat `ProductVariant.barcode` abgelöst. Was sich ändert und was
davon gefährlich ist.

## Der Unterschied, auf den es ankommt

| | alt | neu |
|---|---|---|
| **Lesen** | `barcode` | `barcodes(first: 5) { nodes { value type } }` |
| **Schreiben** | `barcode: "4013594…"` | `barcodes: [{ value: "4013594…", type: EAN }]` |

**Beim Lesen** ist `barcode` *veraltet*: Es funktioniert weiter und
Shopify warnt. **Beim Schreiben** ist es *weg*:
`ProductVariantsBulkInput` kennt nur noch `barcodes`. Wer dort
`barcode` sendet, bekommt einen Fehler, keine Warnung.

Deshalb brechen die schreibenden Skripte sofort und die lesenden erst
später. Das bestimmt die Reihenfolge der Arbeit.

Neu ist außerdem: Eine Variante kann bis zu **20 Barcodes** tragen,
jeder mit einem Typ — `ASIN`, `EAN`, `GTIN`, `ISBN`, `NS_PID`, `UPC`.

## Was das für den Zwergenladen bedeutet

Der Typ ist nicht nur Kosmetik. Bei den Buchverlagen steht damit
erkennbar eine **ISBN** im Feld und keine beliebige Zahl. Bei goki und
HENRYS eine **EAN**. `barcode_feld.typ_fuer()` leitet das aus dem Wert
ab: 978 oder 979 am Anfang einer 13-stelligen Zahl heißt ISBN, sonst
EAN; zwölf Stellen heißt UPC.

## Die Zwischenschicht

`barcode_feld.py` kapselt den Unterschied an einer Stelle:

```python
import barcode_feld as bc

ABFRAGE = "variants(first: 10) { edges { node { id sku %BARCODE% } } }"
antwort  = shopify_http.execute(ABFRAGE.replace("%BARCODE%", str(bc.LESEN)))

wert    = bc.lies(variantenknoten)          # aus beiden Antwortformen
eingabe = {"id": vid, **bc.schreiben(wert)} # in die passende Eingabeform
```

Warum ein Platzhalter und kein f-String: GraphQL steckt voller
geschweifter Klammern, die in f-Strings alle verdoppelt werden
müssten. Ein `%BARCODE%` ist schlicht weniger fehleranfällig.

**Die Erkennung läuft über eine Probeabfrage gegen den Shop, nicht
über einen Versionsvergleich.** Wann Shopify das neue Feld eingeführt
hat, muss so niemand wissen — und ein Irrtum über die
Einführungsversion kann keine falschen Barcodes erzeugen. Antwortet
der Shop mit etwas anderem als einer klaren Feldfehlermeldung (etwa
Drosselung), bleibt die Schicht vorsichtig bei der alten Form.

## Stand prüfen

```bash
python3 barcode-umstellung-pruefen.py
```

Zeigt die eingestellte API-Version, probiert beide Formen gegen den
Shop und listet, welche Dateien im Ordner noch die alte Form
verwenden — getrennt nach schreibend und lesend. Ändert nichts.

Die Schreiberkennung verlangt beides: das Feld **und** eine Mutation,
die Varianten schreibt. Das Wort „barcode" allein steht auch in
Antworten und Testdaten; danach zu suchen erzeugte Fehlalarme.

## Was bereits umgestellt ist

- `gtin-nachtragen.py` — liest und schreibt über die Schicht
- `pages/1_Produktbilder.py` — liest über die Schicht, schreibt die
  ISBN ausdrücklich mit Typ `ISBN`

Beide laufen auf alter wie neuer API unverändert.

## Was noch aussteht

Diese lesen die alte Form. Sie warnen nur, brechen aber nicht:

- `kanal-uebersicht.py`
- `bilder-suchen.py`
- `duplikat-loeschen.py`
- `produkt-loeschen.py`
- `bildluecken-aufarbeiten.py`
- `bestand-und-bilder-pruefen.py`

Umstellung jeweils: `import barcode_feld as bc`, im GraphQL `barcode`
durch `%BARCODE%` ersetzen, Abfrage durch `.replace()` schicken, und
`v.get("barcode")` durch `bc.lies(v)`.

Die REST-Skripte (`shopify-salepreise-setzen.py`,
`shopify-bilder-upload.py` und weitere auf API 2024-01) sind ein
eigenes Thema — REST hat seine eigene Zeitschiene.

## Wann umstellen

Solange `barcode-umstellung-pruefen.py` **beide Formen als ok** meldet,
ist Zeitfenster: Umstellen kostet nichts und lässt sich sofort
nachprüfen. Meldet es nur noch die neue Form, ist der Schreibpfad
bereits defekt.

Der Wechsel selbst ist dann ein Einzeiler — `API_VERSION` in
`shopify_http.py` anheben. Die Schicht merkt es von allein.

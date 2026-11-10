# Kategorie „Geschenke für Männer" — Messer ans Ende

Stand 31.10.2026.

## Was geändert wurde

`/collections/maennergeschenke` (Collection 727787536757):

| | vorher | jetzt |
|---|---|---|
| Sortierung | `MOST_RELEVANT` (Beliebteste, von Shopify gesteuert) | `MANUAL` |
| Regeln | unverändert | unverändert |
| Produkte | 52 | 52 |

Sonst nichts. Insbesondere keine Produkte entfernt oder verschoben.

## Reihenfolge jetzt

Plätze 1–32: Primavera (8), Sonnenleder (8), Sonett (16)
Plätze 33–52: OTTER (4) und Herbertz (16) — Messer, Multitool,
Taschenlampen, Feuerzeug

Shopify hat beim Umstellen die bisherige Reihenfolge übernommen
(neueste Produkte zuerst). Die Messer-Produkte sind die ältesten und
standen dadurch ohnehin am Ende, eine Verschiebung war nicht nötig.

Taschenlampen und Feuerzeug von Herbertz stehen mit im Messerblock,
weil sie zur selben Linie gehören („Männerscharf") und sonst einzeln
zwischen Sonnenleder und Sonett stehen würden.

## Zurücknehmen

    collectionUpdate(collection: { id: "gid://shopify/Collection/727787536757",
                                   sortOrder: MOST_RELEVANT })

## Offen

Bei manueller Sortierung ist nicht belegt, wo künftig neu
hinzukommende Produkte landen. Beim nächsten Neuzugang in dieser
Kategorie nachsehen: Steht ein neues Messer an erster Stelle, muss es
von Hand ans Ende.

Nebenwirkung der manuellen Sortierung: Die Kategorie ordnet sich nicht
mehr selbst nach Beliebtheit.

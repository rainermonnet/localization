"""
warenkorb-mails-vorbereiten.py — Anschreiben samt Wiederherstellungslink
=========================================================================

Holt die offenen Warenkorbabbrüche inklusive `abandonedCheckoutUrl` —
dem Link, der den Warenkorb beim Kunden wiederherstellt — und schreibt
daraus fertige Anschreiben.

Ohne diesen Link ist jede Erinnerungsmail wertlos: Der Kunde müsste alles
neu suchen. Deshalb steht er hier an erster Stelle.

WOFÜR DAS GEDACHT IST
---------------------
Für den Rückstand an alten Abbrüchen. Künftige erledigt Shopify selbst,
sobald unter Einstellungen → Checkout die Erinnerung eingeschaltet ist —
dieses Skript ersetzt das nicht und soll es nicht.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 warenkorb-mails-vorbereiten.py           # letzte 60 Tage
    python3 warenkorb-mails-vorbereiten.py 90        # weiter zurück

Ergebnis: warenkorb-mails.txt mit je Abbruch einem fertigen Anschreiben.
Nur Lesezugriff — es wird nichts verschickt.
"""

import sys
import time
from datetime import datetime, timedelta, timezone

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

# Eigene Stadt — Kunden von hier bekommen das Abholangebot statt Versand
STADT = "freiburg"
LADEN = "Schwimmbadstraße 36"

ABFRAGE = """
query($cursor: String) {
  abandonedCheckouts(first: 50, after: $cursor, sortKey: CREATED_AT, reverse: true) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        name
        createdAt
        abandonedCheckoutUrl
        totalPriceSet { shopMoney { amount } }
        customer { firstName lastName email }
        shippingAddress { city }
        billingAddress { city }
        lineItems(first: 20) {
          edges {
            node {
              title
              quantity
              variantTitle
              originalUnitPriceSet { shopMoney { amount } }
            }
          }
        }
      }
    }
  }
}
"""


def geld(knoten, schluessel):
    try:
        return float(knoten[schluessel]["shopMoney"]["amount"])
    except (KeyError, TypeError, ValueError):
        return 0.0


def anrede(kunde):
    """Höfliche Anrede, wenn der Nachname bekannt ist — sonst neutral."""
    if not kunde:
        return "Hallo,"
    nach = (kunde.get("lastName") or "").strip()
    vor = (kunde.get("firstName") or "").strip()
    if nach:
        return f"Hallo Frau/Herr {nach},"
    if vor:
        return f"Hallo {vor},"
    return "Hallo,"


def stadt_von(k):
    for feld in ("shippingAddress", "billingAddress"):
        ort = ((k.get(feld) or {}).get("city") or "").strip()
        if ort:
            return ort
    return ""


def main():
    tage = 60
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        tage = int(sys.argv[1])
    grenze = (datetime.now(timezone.utc) - timedelta(days=tage)).isoformat()

    print(f"Lese Abbrüche der letzten {tage} Tage …")
    alle, cursor = [], None
    while True:
        for versuch in range(5):
            antwort = shopify_http.execute(ABFRAGE, {"cursor": cursor})
            fehler = antwort.get("_error", "")
            if not fehler:
                break
            if "THROTTLED" in fehler.upper() and versuch < 4:
                time.sleep(2 ** versuch)
                continue
            sys.exit(f"Fehler: {fehler}")

        block = antwort.get("abandonedCheckouts") or {}
        kanten = block.get("edges", [])
        if not kanten:
            break
        fertig = False
        for k in kanten:
            n = k["node"]
            if (n.get("createdAt") or "") < grenze:
                fertig = True
                break
            alle.append(n)
        if fertig or not block.get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = block["pageInfo"]["endCursor"]
        time.sleep(0.3)

    if not alle:
        print("Keine Abbrüche im Zeitraum.")
        return

    # Ohne Adresse unerreichbar, ohne Link wertlos
    brauchbar = [k for k in alle
                 if (k.get("customer") or {}).get("email")
                 and k.get("abandonedCheckoutUrl")]
    ohne = len(alle) - len(brauchbar)

    brauchbar.sort(key=lambda k: -geld(k, "totalPriceSet"))

    with open("warenkorb-mails.txt", "w", encoding="utf-8") as f:
        for i, k in enumerate(brauchbar, 1):
            kunde = k.get("customer") or {}
            wert = geld(k, "totalPriceSet")
            ort = stadt_von(k)
            vor_ort = STADT in ort.lower()
            wann = (k.get("createdAt") or "")[:10]

            posten = []
            for p in k.get("lineItems", {}).get("edges", []):
                n = p["node"]
                bez = n.get("title", "")
                if n.get("variantTitle") and n["variantTitle"] != "Default Title":
                    bez += f" ({n['variantTitle']})"
                posten.append(f"{n.get('quantity', 1)} × {bez}")

            f.write("=" * 70 + "\n")
            f.write(f"{i}. {kunde.get('firstName','')} {kunde.get('lastName','')}"
                    f"  —  {wert:.2f} €  —  {wann}"
                    f"{'  —  VOR ORT' if vor_ort else ''}\n")
            f.write(f"An: {kunde.get('email')}\n")
            f.write(f"Ort: {ort or 'unbekannt'}\n")
            f.write("=" * 70 + "\n\n")

            haupt = posten[0].split(" × ", 1)[-1] if posten else "Ihre Auswahl"
            f.write(f"Betreff: {haupt[:48]} — noch Fragen dazu?\n\n")
            f.write(f"{anrede(kunde)}\n\n")
            f.write("Sie hatten bei uns etwas im Warenkorb und den Einkauf nicht\n")
            f.write("abgeschlossen. Wir haben Ihre Auswahl aufgehoben:\n\n")
            for p in posten:
                f.write(f"  · {p}\n")
            f.write(f"\n  Gesamt: {wert:.2f} €\n\n")

            if vor_ort:
                f.write(f"Sie wohnen in {ort} — Sie können die Sachen auch bei uns\n")
                f.write(f"im Laden ansehen und mitnehmen, {LADEN}. Dann\n")
                f.write("entfällt der Versand, und Sie sehen alles in echt.\n\n")

            f.write("Hier kommen Sie direkt zu Ihrem Warenkorb zurück:\n")
            f.write(f"{k['abandonedCheckoutUrl']}\n\n")
            f.write("Falls eine Frage offen war — antworten Sie einfach auf diese\n")
            f.write("Mail. Wir führen einen Laden in Freiburg und kennen jedes\n")
            f.write("Stück, das wir anbieten.\n\n")
            f.write("Herzliche Grüße\nRainer Monnet\nZwergenladen\n\n\n")

    summe = sum(geld(k, "totalPriceSet") for k in brauchbar)
    print(f"\n{len(brauchbar)} Anschreiben geschrieben, zusammen {summe:.2f} €")
    if ohne:
        print(f"{ohne} übersprungen (keine Adresse oder kein Wiederherstellungslink)")
    vor_ort = sum(1 for k in brauchbar if STADT in stadt_von(k).lower())
    if vor_ort:
        print(f"{vor_ort} davon wohnen in {STADT.capitalize()} — dort steht das "
              "Abholangebot im Text")
    print("\nDatei: warenkorb-mails.txt")
    print("Inhalt hier in den Chat kopieren — dann lege ich die Entwürfe")
    print("direkt in dein Gmail, du musst nur noch auf Senden klicken.")


if __name__ == "__main__":
    main()

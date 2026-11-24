"""
warenkorb-abbrueche-pruefen.py — wirkt die Erinnerung?
=======================================================

Ob die Erinnerungsmail eingeschaltet ist, verrät Shopify nicht über die
API — Checkout- und Benachrichtigungseinstellungen stehen nur in der
Oberfläche. Messbar ist aber das Ergebnis:

  - wie viele Warenkörbe abgebrochen wurden
  - welcher Umsatz darin liegt
  - wie viele davon später doch bestellt haben

Die letzte Zahl ist der eigentliche Beleg. Werden Abbrecher nie zu
Kunden, läuft die Erinnerung vermutlich nicht.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 warenkorb-abbrueche-pruefen.py           # letzte 90 Tage
    python3 warenkorb-abbrueche-pruefen.py 30        # letzte 30 Tage

Nur Lesezugriff.
"""

import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

ABBRUECHE = """
query($cursor: String) {
  abandonedCheckouts(first: 50, after: $cursor, sortKey: CREATED_AT, reverse: true) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        name
        createdAt
        lineItemsQuantity
        totalPriceSet { shopMoney { amount currencyCode } }
        customer { id email }
      }
    }
  }
}
"""

# Bestellungen derselben Zeitspanne, um Rückkehrer zu erkennen
BESTELLUNGEN = """
query($cursor: String, $q: String!) {
  orders(first: 50, after: $cursor, query: $q, sortKey: CREATED_AT, reverse: true) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        createdAt
        email
        totalPriceSet { shopMoney { amount } }
      }
    }
  }
}
"""


def hole(abfrage, variablen, wurzel, grenze_iso=None, feld="createdAt"):
    """Seitenweise lesen, bis das Datum unterschritten wird."""
    aus, cursor = [], None
    while True:
        for versuch in range(5):
            antwort = shopify_http.execute(abfrage, dict(variablen, cursor=cursor))
            fehler = antwort.get("_error", "")
            if not fehler:
                break
            if "THROTTLED" in fehler.upper() and versuch < 4:
                time.sleep(2 ** versuch)
                continue
            return aus, fehler
        else:
            return aus, "dauerhaft gedrosselt"

        block = antwort.get(wurzel) or {}
        kanten = block.get("edges", [])
        if not kanten:
            break

        fertig = False
        for k in kanten:
            n = k["node"]
            if grenze_iso and (n.get(feld) or "") < grenze_iso:
                fertig = True
                break
            aus.append(n)
        if fertig:
            break

        info = block.get("pageInfo", {})
        if not info.get("hasNextPage"):
            break
        cursor = info.get("endCursor")
        time.sleep(0.3)
    return aus, ""


def betrag(knoten, schluessel="totalPriceSet"):
    try:
        return float(knoten[schluessel]["shopMoney"]["amount"])
    except (KeyError, TypeError, ValueError):
        return 0.0


def main():
    tage = 90
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        tage = int(sys.argv[1])

    seit = datetime.now(timezone.utc) - timedelta(days=tage)
    grenze = seit.isoformat()
    print(f"Zeitraum: letzte {tage} Tage (ab {seit:%d.%m.%Y})\n")

    print("Lese abgebrochene Warenkörbe …")
    abbrueche, fehler = hole(ABBRUECHE, {}, "abandonedCheckouts", grenze)
    if fehler and not abbrueche:
        sys.exit(f"Fehler: {fehler}")
    if fehler:
        print(f"  (Abbruch beim Lesen: {fehler} — werte das Bisherige aus)")

    print(f"Lese Bestellungen …")
    bestellungen, fehler2 = hole(
        BESTELLUNGEN, {"q": f"created_at:>{seit:%Y-%m-%d}"}, "orders", grenze)
    if fehler2 and not bestellungen:
        print(f"  (Bestellungen nicht lesbar: {fehler2})")

    if not abbrueche:
        print("\nKeine abgebrochenen Warenkörbe im Zeitraum.")
        print("Entweder wird selten abgebrochen — oder es kommt kaum jemand")
        print("bis zum Checkout. Das zweite ist bei wenig Traffic das Übliche.")
        return

    summe = sum(betrag(a) for a in abbrueche)
    mit_mail = [a for a in abbrueche if (a.get("customer") or {}).get("email")]

    # Wer hat nach dem Abbruch doch bestellt?
    best_mails = defaultdict(list)
    for b in bestellungen:
        if b.get("email"):
            best_mails[b["email"].lower()].append(b)

    zurueck, zurueck_wert = 0, 0.0
    for a in mit_mail:
        mail = (a["customer"]["email"] or "").lower()
        for b in best_mails.get(mail, []):
            if b.get("createdAt", "") > a.get("createdAt", ""):
                zurueck += 1
                zurueck_wert += betrag(b)
                break

    print("\n" + "=" * 58)
    print(f"  Abgebrochene Warenkörbe      {len(abbrueche):>6}")
    print(f"  Warenwert darin              {summe:>9.2f} €")
    print(f"  davon mit E-Mail-Adresse     {len(mit_mail):>6}"
          "   ← nur diese sind erreichbar")
    print(f"  davon später doch bestellt   {zurueck:>6}")
    if zurueck:
        print(f"  Umsatz dieser Bestellungen   {zurueck_wert:>9.2f} €")
    print("=" * 58)

    if mit_mail:
        quote = 100 * zurueck / len(mit_mail)
        print(f"\n  Rückkehrquote: {quote:.1f} %")
        if quote >= 5:
            print("  Im üblichen Rahmen (5–15 %). Die Erinnerung wirkt offenbar.")
        elif zurueck:
            print("  Unter dem üblichen Rahmen. Entweder ist die Erinnerung aus,")
            print("  oder der Text erreicht die Leute nicht.")
        else:
            print("  Kein einziger Rückkehrer. Das spricht dafür, dass die")
            print("  Erinnerungsmail NICHT eingeschaltet ist.")

    ohne_mail = len(abbrueche) - len(mit_mail)
    if ohne_mail:
        print(f"\n  {ohne_mail} Abbrüche ohne E-Mail-Adresse — dort kann keine")
        print("  Erinnerung ankommen. Das ist normal: Die Adresse wird erst im")
        print("  Checkout erfasst, wer vorher abspringt, bleibt unerreichbar.")

    print("\nLetzte Abbrüche:")
    for a in abbrueche[:10]:
        wann = (a.get("createdAt") or "")[:10]
        mail = (a.get("customer") or {}).get("email") or "— keine Adresse —"
        print(f"  {wann}  {betrag(a):>8.2f} €  "
              f"{a.get('lineItemsQuantity') or 0:>2} Art.  {mail[:34]}")

    print("\n" + "-" * 58)
    print("Die Einstellung selbst steht nur in der Oberfläche:")
    print("  Einstellungen → Checkout → Abgebrochene Checkouts")
    print("  Einstellungen → Benachrichtigungen → Abgebrochener Checkout")


if __name__ == "__main__":
    main()

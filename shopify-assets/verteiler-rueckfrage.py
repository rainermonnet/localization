"""
verteiler-rueckfrage.py — Einwilligung nachholen, in drei Schritten
====================================================================

Für die Adressen, die von Hand in den Verteiler kamen und keine
Bestellung haben. Sie werden einmal gefragt, ob sie den Newsletter
wollen; wer nicht antwortet, wird abgemeldet.

WARUM DREI SCHRITTE
-------------------
Alle Betroffenen stehen in Shopify auf SUBSCRIBED. Füllt einer nach
der Mail das Anmeldeformular aus, ändert sich daran nichts — er war
bereits angemeldet. Ohne vorherige Markierung ließen sich Bestätiger
und Schweiger hinterher nicht trennen, und man müsste entweder alle
behalten (nichts gewonnen) oder alle abmelden (auch die Willigen).

    1. --markieren   Kohorte mit einem Stichtags-Tag versehen
    2.               Mail verschicken (Entwurf in
                     newsletter-einwilligung.md)
    3. --auswerten   zeigen, wer seither den Tag „newsletter" trägt
    4. --abmelden    den Rest auf UNSUBSCRIBED setzen

Schritt 3 erkennt Bestätiger daran, dass das Anmeldeformular auf
/pages/newsletter `contact[tags]=newsletter` mitsendet.

UNGEPRÜFTE ANNAHME
------------------
Ob Shopify diesen Tag auch an BESTEHENDE Kunden anhängt oder nur an
neu angelegte, ist nicht belegt. Bei neuen funktioniert es sicher.
Deshalb vor dem Versand testen: Formular mit einer Adresse ausfüllen,
die bereits Kunde ist, danach `--auswerten` laufen lassen. Erscheint
sie als Bestätiger, trägt das Verfahren. Erscheint sie nicht, müssen
die Klicks aus Klaviyo kommen — Shopify Email zeigt nur Summen, nicht
einzelne Empfänger.

Das ist der Punkt, an dem das Verfahren kippen kann. Erst prüfen,
dann 247 Leute anschreiben.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"

    python3 verteiler-rueckfrage.py --markieren          # Probelauf
    python3 verteiler-rueckfrage.py --markieren --live

    python3 verteiler-rueckfrage.py --auswerten          # nur lesen

    python3 verteiler-rueckfrage.py --abmelden           # Probelauf
    python3 verteiler-rueckfrage.py --abmelden --live

Abmelden heißt NICHT löschen. Der Datensatz bleibt als Beleg dafür,
dass gefragt wurde. Löschen vernichtet genau diesen Nachweis.
"""

import csv
import sys
import time
from datetime import date

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

KOHORTE = "rueckfrage-" + date.today().strftime("%Y-%m")
BESTAETIGT = "newsletter"

KUNDEN = """
query($cursor: String) {
  customers(first: 100, after: $cursor, sortKey: CREATED_AT) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id email firstName lastName createdAt numberOfOrders tags
        emailMarketingConsent { marketingState marketingOptInLevel }
      }
    }
  }
}
"""

TAGGEN = """
mutation($id: ID!, $tags: [String!]!) {
  tagsAdd(id: $id, tags: $tags) { userErrors { field message } }
}
"""

ABMELDEN = """
mutation($input: CustomerEmailMarketingConsentUpdateInput!) {
  customerEmailMarketingConsentUpdate(input: $input) {
    userErrors { field message }
  }
}
"""


def kurz(gid):
    return gid.rsplit("/", 1)[-1] if gid else ""


def alle_kunden():
    kunden, cursor = [], None
    while True:
        for versuch in range(5):
            a = shopify_http.execute(KUNDEN, {"cursor": cursor})
            f = str(a.get("_error", ""))
            if not f:
                break
            if "THROTTLED" in f.upper() and versuch < 4:
                time.sleep(2 ** versuch)
                continue
            sys.exit(f"Nicht lesbar: {f}")
        block = a.get("customers", {})
        kunden += [k["node"] for k in block.get("edges", [])]
        if not block.get("pageInfo", {}).get("hasNextPage"):
            return kunden
        cursor = block["pageInfo"]["endCursor"]
        time.sleep(0.2)


def bestellungen(k):
    try:
        return int(k.get("numberOfOrders") or 0)
    except (TypeError, ValueError):
        return 0


def betroffen(kunden):
    """Im Verteiler, ohne Bestellung, ohne Formular-Tag."""
    return [k for k in kunden
            if (k.get("emailMarketingConsent") or {}).get("marketingState") == "SUBSCRIBED"
            and bestellungen(k) == 0
            and BESTAETIGT not in (k.get("tags") or [])]


def liste_schreiben(name, kunden):
    with open(name, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Kunden-ID", "E-Mail", "Vorname", "Nachname",
                    "Angelegt", "Tags"])
        for k in kunden:
            w.writerow([kurz(k["id"]), k.get("email", ""),
                        k.get("firstName") or "", k.get("lastName") or "",
                        (k.get("createdAt") or "")[:10],
                        " ".join(k.get("tags") or [])])
    print(f"Geschrieben: {name}")


def markieren(live):
    kunden = alle_kunden()
    offen = [k for k in betroffen(kunden) if KOHORTE not in (k.get("tags") or [])]
    schon = [k for k in kunden if KOHORTE in (k.get("tags") or [])]

    print(f"{len(kunden)} Kunden · {len(offen)} zu markieren"
          f" · {len(schon)} tragen „{KOHORTE}“ bereits\n")
    for k in offen[:10]:
        print(f"    {k.get('email','')[:44]}")
    if len(offen) > 10:
        print(f"    … und {len(offen)-10} weitere")
    if not offen:
        print("Nichts zu markieren.")
        return
    liste_schreiben("rueckfrage-kohorte.csv", offen)

    print(f"\nDiese Liste ist der Empfängerkreis für die Mail.")
    if not live:
        print(f"\n{len(offen)} Markierungen bereit. Mit --live setzen.")
        return
    if input(f"\n{len(offen)} Kunden mit „{KOHORTE}“ markieren? (ja/NEIN): "
             ).strip().lower() != "ja":
        print("Abgebrochen.")
        return

    ok = fehler = 0
    for i, k in enumerate(offen, 1):
        e = shopify_http.execute(TAGGEN, {"id": k["id"], "tags": [KOHORTE]})
        meldungen = e.get("_error") or [u.get("message") for u in
                                        (e.get("tagsAdd", {}).get("userErrors") or [])]
        if meldungen:
            fehler += 1
            if fehler <= 5:
                print(f"  ✗ {k.get('email','')}: {meldungen}")
        else:
            ok += 1
        if i % 50 == 0:
            print(f"  … {i}/{len(offen)}")
        time.sleep(0.2)
    print(f"\nFertig: {ok} markiert, {fehler} fehlgeschlagen")
    print("Jetzt die Mail verschicken — Entwurf in newsletter-einwilligung.md")


def auswerten():
    kunden = alle_kunden()
    kohorte = [k for k in kunden if KOHORTE in (k.get("tags") or [])]
    if not kohorte:
        print(f"Niemand trägt „{KOHORTE}“. Erst --markieren laufen lassen.")
        return
    bestaetigt = [k for k in kohorte if BESTAETIGT in (k.get("tags") or [])]
    schweigt = [k for k in kohorte if BESTAETIGT not in (k.get("tags") or [])]

    print(f"Kohorte „{KOHORTE}“: {len(kohorte)} Angeschriebene\n")
    print(f"  {len(bestaetigt):>4}  haben bestätigt "
          f"({len(bestaetigt)/len(kohorte):.0%})")
    print(f"  {len(schweigt):>4}  haben nicht reagiert")
    liste_schreiben("rueckfrage-bestaetigt.csv", bestaetigt)
    liste_schreiben("rueckfrage-ohne-antwort.csv", schweigt)
    print("\nWenn die Frist um ist:  python3 verteiler-rueckfrage.py --abmelden")


def abmelden(live):
    kunden = alle_kunden()
    kohorte = [k for k in kunden if KOHORTE in (k.get("tags") or [])]
    raus = [k for k in kohorte
            if BESTAETIGT not in (k.get("tags") or [])
            and (k.get("emailMarketingConsent") or {}).get("marketingState") == "SUBSCRIBED"]

    print(f"Kohorte: {len(kohorte)} · abzumelden: {len(raus)}\n")
    if not raus:
        print("Nichts abzumelden.")
        return
    for k in raus[:10]:
        print(f"    {k.get('email','')[:44]}")
    if len(raus) > 10:
        print(f"    … und {len(raus)-10} weitere")
    liste_schreiben("rueckfrage-abgemeldet.csv", raus)

    print("\nDie Datensätze bleiben erhalten — nur der Versand endet.")
    print("Das ist der Beleg dafür, dass gefragt wurde. Nicht löschen.")
    if not live:
        print(f"\n{len(raus)} Abmeldungen bereit. Mit --live ausführen.")
        return
    if input(f"\n{len(raus)} Kunden abmelden? (ja/NEIN): ").strip().lower() != "ja":
        print("Abgebrochen.")
        return

    ok = fehler = 0
    for i, k in enumerate(raus, 1):
        e = shopify_http.execute(ABMELDEN, {"input": {
            "customerId": k["id"],
            "emailMarketingConsent": {"marketingState": "UNSUBSCRIBED"}}})
        meldungen = e.get("_error") or [
            u.get("message") for u in
            (e.get("customerEmailMarketingConsentUpdate", {}).get("userErrors") or [])]
        if meldungen:
            fehler += 1
            if fehler <= 5:
                print(f"  ✗ {k.get('email','')}: {meldungen}")
        else:
            ok += 1
        if i % 50 == 0:
            print(f"  … {i}/{len(raus)}")
        time.sleep(0.2)
    print(f"\nFertig: {ok} abgemeldet, {fehler} fehlgeschlagen")


def main():
    live = "--live" in sys.argv
    if not live and ("--markieren" in sys.argv or "--abmelden" in sys.argv):
        print("PROBELAUF — es wird nichts geändert.\n")
    if "--markieren" in sys.argv:
        markieren(live)
    elif "--auswerten" in sys.argv:
        auswerten()
    elif "--abmelden" in sys.argv:
        abmelden(live)
    else:
        print(__doc__.split("AUSFÜHREN")[1].strip())


if __name__ == "__main__":
    main()

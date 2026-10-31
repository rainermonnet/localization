"""
newsletter-rechtslage.py — Verteiler nach Rechtsgrundlage trennen
===================================================================

Wer im Verteiler steht, steht dort aus einem von zwei Gründen — und die
sind rechtlich sehr verschieden:

  A) Er hat ausdrücklich eingewilligt (Formular, Double Opt-in)
     → § 7 Abs. 2 UWG, unproblematisch

  B) Er wurde von Hand aufgenommen, weil er gekauft hat
     → nur über § 7 Abs. 3 UWG zulässig, und nur wenn ALLE vier
       Bedingungen erfüllt sind:
         1. Adresse stammt aus einem Verkauf
         2. Werbung für eigene ähnliche Waren
         3. kein Widerspruch
         4. Hinweis auf das Widerspruchsrecht bei Erhebung UND in
            jeder einzelnen Mail

  C) Er wurde von Hand aufgenommen, ohne je gekauft zu haben
     → dafür gibt es keine Grundlage. Bekanntschaft genügt nicht.

Bedingung 1 ist das einzige, was sich aus den Daten ablesen lässt: Hat
der Kunde eine Bestellung oder nicht. Dieses Skript trennt danach.

WAS DAS SKRIPT NICHT KANN
--------------------------
Es weiß nicht, wer sich selbst eingetragen hat und wer von Hand
hinzugefügt wurde. Shopify hält das nicht fest. Anhaltspunkte:

  • Tag „newsletter"  → kam über das Anmeldeformular
  • Einwilligung Minuten nach Anlage → eher Selbstanmeldung
  • Einwilligung Monate nach Anlage  → eher nachträglich gesetzt

Beides steht in der Ausgabe, ist aber ein Indiz und kein Beweis.

ZUR OPT-IN-STUFE
----------------
Shopify führt je Kunde `CONFIRMED_OPT_IN` oder `SINGLE_OPT_IN`.
`CONFIRMED_OPT_IN` behauptet: Dieser Mensch hat einen
Bestätigungslink angeklickt. Steht das bei jemandem, der von Hand
eingetragen wurde, dokumentiert deine Datenbank etwas, das nie
passiert ist. Im Streitfall ist eine falsche Bestätigung schlechter
als gar keine — deshalb zählt die Auswertung das getrennt.

AUSFÜHREN
---------
    cd "/Users/rainermonnet/Streamlit App/zwergenladen-import-app"
    python3 newsletter-rechtslage.py

Nur Lesezugriff. Schreibt `verteiler-nach-grundlage.csv`.
"""

import csv
import sys
import time
from collections import Counter

try:
    import shopify_http
except ImportError:
    sys.exit("shopify_http.py nicht gefunden — bitte im App-Ordner ausführen.")

ABFRAGE = """
query($cursor: String) {
  customers(first: 100, after: $cursor, sortKey: CREATED_AT) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        email
        firstName
        lastName
        createdAt
        numberOfOrders
        tags
        emailMarketingConsent {
          marketingState
          marketingOptInLevel
          consentUpdatedAt
        }
      }
    }
  }
}
"""


def kurz(gid):
    return gid.rsplit("/", 1)[-1] if gid else ""


def main():
    print("Lese Kundenstamm …")
    kunden, cursor = [], None
    while True:
        for versuch in range(5):
            a = shopify_http.execute(ABFRAGE, {"cursor": cursor})
            f = str(a.get("_error", ""))
            if not f:
                break
            if "THROTTLED" in f.upper() and versuch < 4:
                time.sleep(2 ** versuch)
                continue
            sys.exit(f"Nicht lesbar: {f}")
        block = a.get("customers", {})
        for k in block.get("edges", []):
            kunden.append(k["node"])
        if not block.get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = block["pageInfo"]["endCursor"]
        time.sleep(0.2)

    print(f"{len(kunden)} Kunden gelesen\n")

    im_verteiler = [k for k in kunden
                    if ((k.get("emailMarketingConsent") or {})
                        .get("marketingState") == "SUBSCRIBED")]
    print(f"{len(im_verteiler)} davon im Verteiler (SUBSCRIBED)\n")
    if not im_verteiler:
        print("Niemand im Verteiler. Nichts zu trennen.")
        return

    def bestellungen(k):
        try:
            return int(k.get("numberOfOrders") or 0)
        except (TypeError, ValueError):
            return 0

    mit_kauf = [k for k in im_verteiler if bestellungen(k) > 0]
    ohne_kauf = [k for k in im_verteiler if bestellungen(k) == 0]

    print("=" * 70)
    print("NACH RECHTSGRUNDLAGE")
    print("=" * 70)
    print(f"{len(mit_kauf):>5}  mit Bestellung — § 7 Abs. 3 UWG denkbar,")
    print( "       wenn Hinweis auf Widerspruchsrecht gegeben wurde")
    print(f"{len(ohne_kauf):>5}  OHNE Bestellung — hier trägt die")
    print( "       Bestandskundenausnahme nicht. Ohne ausdrückliche")
    print( "       Einwilligung fehlt die Grundlage.")

    # Indizien für Selbstanmeldung
    mit_tag = [k for k in im_verteiler if "newsletter" in (k.get("tags") or [])]
    print(f"\n{len(mit_tag)} tragen den Tag „newsletter“ — kamen über das Formular")

    def nachtraeglich(k):
        """Einwilligung deutlich später als Anlage = eher von Hand gesetzt."""
        e = (k.get("emailMarketingConsent") or {}).get("consentUpdatedAt") or ""
        return bool(e) and bool(k.get("createdAt")) and e[:10] > k["createdAt"][:10]

    spaet = [k for k in im_verteiler if nachtraeglich(k)]
    print(f"{len(spaet)} haben die Einwilligung an einem SPÄTEREN Tag als die")
    print( "   Anlage — Indiz für nachträgliches Eintragen von Hand")

    stufen = Counter((k.get("emailMarketingConsent") or {}).get("marketingOptInLevel")
                     for k in im_verteiler)
    print("\nOPT-IN-STUFE LAUT SHOPIFY")
    for stufe, n in stufen.most_common():
        print(f"  {n:>5}  {stufe}")

    falsch = [k for k in ohne_kauf
              if (k.get("emailMarketingConsent") or {}).get("marketingOptInLevel")
              == "CONFIRMED_OPT_IN" and "newsletter" not in (k.get("tags") or [])]
    if falsch:
        print(f"\n{len(falsch)} Datensätze behaupten CONFIRMED_OPT_IN, obwohl weder")
        print("eine Bestellung noch der Formular-Tag vorliegt. Falls die nie")
        print("einen Bestätigungslink geklickt haben, dokumentiert deine")
        print("Datenbank etwas, das nicht stattgefunden hat.")

    with open("verteiler-nach-grundlage.csv", "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Gruppe", "Kunden-ID", "E-Mail", "Vorname", "Nachname",
                    "Angelegt", "Bestellungen", "Tags", "Opt-in-Stufe",
                    "Einwilligung am"])
        for gruppe, liste in (("mit Bestellung", mit_kauf),
                              ("ohne Bestellung", ohne_kauf)):
            for k in sorted(liste, key=lambda x: x.get("createdAt") or ""):
                e = k.get("emailMarketingConsent") or {}
                w.writerow([gruppe, kurz(k["id"]), k.get("email", ""),
                            k.get("firstName") or "", k.get("lastName") or "",
                            (k.get("createdAt") or "")[:10],
                            k.get("numberOfOrders", 0),
                            " ".join(k.get("tags") or []),
                            e.get("marketingOptInLevel", ""),
                            (e.get("consentUpdatedAt") or "")[:10]])
    print("\nGeschrieben: verteiler-nach-grundlage.csv")
    print("\nDie Gruppe „ohne Bestellung“ ist die, bei der eine")
    print("Rückholaktion sinnvoll ist — siehe newsletter-einwilligung.md.")


if __name__ == "__main__":
    main()

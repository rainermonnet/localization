import json, html
FAQ = [
 ("Welches Holzspielzeug eignet sich für ein 2-jähriges Kind?",
  "Am besten robustes Holzspielzeug ohne Kleinteile, das sich schieben, ziehen, stapeln und einfach ausprobieren lässt: Schiebe- und Ziehtiere, Holzfahrzeuge, große Bausteine, Stapelspiele, einfache Puzzles mit wenigen Teilen sowie schlichte Puppen und Spielfiguren für das erste Nachspielen des Alltags."),
 ("Worauf muss ich bei der Sicherheit von Spielzeug für 2-Jährige achten?",
  "Spielzeug für Kinder unter drei Jahren darf keine Teile enthalten, die sich verschlucken lassen. Achte auf das CE-Zeichen und die Altersangabe des Herstellers, auf glatte, abgerundete Kanten und auf Oberflächen, die sauber verarbeitet sind. Ist ein Spielzeug erst ab drei Jahren empfohlen, ist es für ein 2-jähriges Kind nicht geeignet."),
 ("Warum ist Holzspielzeug für Kleinkinder eine gute Wahl?",
  "Holz ist robust, fühlt sich warm an und hat keine Batterien, Blinklichter oder festgelegten Funktionen. Das Kind entscheidet selbst, was aus einem Holzauto, einem Baustein oder einer Figur wird. Gutes Holzspielzeug hält zudem oft jahrelang und lässt sich weitergeben."),
 ("Wie viel Spielzeug braucht ein 2-jähriges Kind?",
  "Weniger, als man denkt. Eine überschaubare Auswahl, die gut erreichbar liegt, wird meist intensiver bespielt als ein volles Regal. Du kannst Spielzeug regelmäßig austauschen, dann bleibt es spannend."),
 ("Was kostet gutes Holzspielzeug für 2-Jährige?",
  "Das reicht von wenigen Euro bis zu rund 40 Euro. Beispiele aus unserem Sortiment (Stand November 2026): ein großer Holzball ab 6,60 Euro, ein Schiebehelikopter von goki für 19,95 Euro, ein Kranwagen mit Anhänger von goki für 39,50 Euro."),
 ("Kann ich Holzspielzeug für mein Kind in Freiburg ansehen und mich beraten lassen?",
  "Ja. Im Zwergenladen in Freiburg (Schwimmbadstraße 36) kannst du Spielzeug in die Hand nehmen und dich zu Alter und Auswahl beraten lassen. Online bestellte Ware legen wir zur Abholung zurück (Click & Collect) oder schicken sie dir zu."),
]
h = html.escape
def a(href, t): return f'<a href="{href}">{t}</a>'
body = f"""<p><strong>{h(FAQ[0][1])}</strong></p>
<p>Mit zwei Jahren laufen die meisten Kinder sicher, schieben und ziehen gern, stapeln, räumen ein und aus und beginnen, den Alltag nachzuspielen. Dazu passt Spielzeug, das einfach gebaut ist und viel aushält. Hier steht, worauf es ankommt und was sich bewährt.</p>

<h2>{h(FAQ[0][0])}</h2>
<ul>
<li><strong>Schiebe- und Ziehtiere sowie Fahrzeuge:</strong> Sie passen zur Lust am Laufen und Schieben. Zum Beispiel der {a('/products/schiebehelikopter','Schiebehelikopter')} oder der {a('/products/goki-kranwagen-mit-anhanger-robustes-holzspielzeug-fur-kinder','Kranwagen mit Anhänger')} von goki. Mehr findest du bei den {a('/collections/holzautos-fahrzeuge','Holzautos und Fahrzeugen')}.</li>
<li><strong>Bälle:</strong> Ein großer Ball ist einfach und wird fast täglich gebraucht, zum Beispiel der {a('/products/ball-gr','große Ball von Aurich')}.</li>
<li><strong>Stapeln, Bauen, Einlegen:</strong> Große Bausteine, Stapelspiele und {a('/collections/puzzle','einfache Puzzles')} mit wenigen Teilen.</li>
<li><strong>Puppen und Figuren:</strong> Weiche Puppen und schlichte Figuren fürs erste Rollenspiel. Unsere {a('/collections/puppen','Puppen')} stammen unter anderem von Käthe Kruse und Nanchen.</li>
</ul>
<p>Eine größere Auswahl zeigt die Kategorie {a('/collections/2','Spielzeug ab 2 Jahren')}. Unser Beitrag zum {a('/blogs/news/waldorf-spielzeug-fuer-kids-ab-1-jahr-was-wirklich-sinn-ergibt','Spielzeug ab 1 Jahr')} hilft, wenn dein Kind noch jünger ist.</p>

<h2>{h(FAQ[1][0])}</h2>
<p>{h(FAQ[1][1])}</p>

<h2>{h(FAQ[2][0])}</h2>
<p>{h(FAQ[2][1])}</p>

<h2>{h(FAQ[3][0])}</h2>
<p>{h(FAQ[3][1])}</p>

<h2>{h(FAQ[4][0])}</h2>
<p>{h(FAQ[4][1])}</p>

<h2>{h(FAQ[5][0])}</h2>
<p>{h(FAQ[5][1])}</p>
"""
schema = {"@context":"https://schema.org","@type":"FAQPage",
 "mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":t}} for q,t in FAQ]}
ld = '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False, separators=(",",":")) + '</script>'
open("holzspielzeug-2-jahre.body.html","w",encoding="utf-8").write(body + ld)
open("holzspielzeug-2-jahre.faq.json","w",encoding="utf-8").write(json.dumps(schema,ensure_ascii=False,indent=1))
print(len(body+ld), "Zeichen; Antwortlänge erste Antwort:", len(FAQ[0][1].split()), "Wörter")

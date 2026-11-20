import numpy as np, json, textwrap
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
sp=json.load(open('span_tabelle.json')); lo=json.load(open('loch_tabelle.json'))
PLAT=[90,86.97,80.41,79.72,74.76,73.22,72.0,68.12]
spf=lambda x: np.interp(x,[a for a,_ in sp][::-1],[b for _,b in sp][::-1])
BG='#fbf8ef'; INK='#2b2b2b'; ORA='#d8543b'; BLAU='#2f6a9a'
fig=plt.figure(figsize=(14,9.9),dpi=180); fig.patch.set_facecolor(BG)
fig.text(0.04,0.955,"Oloid mit Loch: wann sich die Mitte öffnet",fontsize=22,fontweight='bold',color=ORA)
fig.text(0.04,0.925,"Gelenkring aus sechs gleichen Gliedern, Verwindung ±φ zwischen den Gelenkachsen. Die Diagonale c2–c5 überstreicht den Oloid.",fontsize=11.5,color='#555')
ax=fig.add_axes([0.06,0.56,0.40,0.31]); ax.set_facecolor(BG)
x=np.array([a for a,_ in sp]); y=np.array([b for _,b in sp])
ax.plot(x,y,color=INK,lw=2); ax.plot([30,60],[360,360],color=BLAU,lw=2.5)
ax.axvline(60,color=ORA,ls='--',lw=1.3); ax.text(59.2,372,"60°: Umschlag",color=ORA,ha='right',fontsize=10)
for p in PLAT: ax.plot(p,spf(p),'o',color=ORA,ms=5)
ax.annotate("Platonische Ringe\n68° bis 90°",xy=(72,262),xytext=(76,320),fontsize=10,arrowprops=dict(arrowstyle='-',color='#777'))
ax.text(44,346,"ganze Kreise:\nc2, c5 laufen um",color=BLAU,fontsize=10,ha='center',va='top')
ax.text(76,228,"Bögen: c2, c5 schwingen hin und her",fontsize=10,ha='center',va='bottom')
ax.set_xlim(90,30); ax.set_ylim(220,385); ax.set_xlabel("Verwindungswinkel φ (Grad)"); ax.set_ylabel("Bogen von c2 und c5 (Grad)")
ax.set_title("A  Der Bogen wächst, je kleiner φ wird",loc='left',fontsize=12.5,fontweight='bold')
for s in ('top','right'): ax.spines[s].set_visible(False)
ax=fig.add_axes([0.55,0.56,0.40,0.31]); ax.set_facecolor(BG)
tx=[90,68,61,60]+[d['tw'] for d in lo]; ty=[0,0,0,0]+[2*d['rh'] for d in lo]
o=np.argsort(tx)[::-1]; tx=np.array(tx)[o]; ty=np.array(ty)[o]
ax.plot(tx,ty,color=BLAU,lw=2); ax.axvline(60,color=ORA,ls='--',lw=1.3)
for t,dx,dy in ((58,-1.0,-0.02),(52,-1.0,-0.10),(45,-1.0,-0.10)):
    yv=np.interp(t,tx[::-1],ty[::-1]); ax.plot(t,yv,'o',color=ORA,ms=6); ax.text(t+dx,yv+dy,f"{t}°: {yv*20:.0f} mm",fontsize=9.5,color=ORA,va='top')
ax.set_xlim(90,30); ax.set_ylim(-0.03,1.15); ax.set_xlabel("Verwindungswinkel φ (Grad)"); ax.set_ylabel("Lochdurchmesser in Kreisradien r")
ax.text(80,0.08,"geschlossen (kein Loch)",fontsize=10,ha='center'); ax.text(89,0.95,"mm-Angaben für\nKreisradius r = 20 mm",fontsize=9,color='#666',va='top')
ax.set_title("B  Unter 60° öffnet sich ein Durchgang",loc='left',fontsize=12.5,fontweight='bold')
for s in ('top','right'): ax.spines[s].set_visible(False)
im=Image.open('loch-vergleich.png'); w,h=im.size; top=im.crop((int(w*0.12),int(h*0.08),int(w*0.88),int(h*0.32)))
axc=fig.add_axes([0.03,0.30,0.48,0.22]); axc.imshow(top); axc.axis('off'); axc.set_title("C  Die überstrichene Fläche, Blick entlang der Achse von Kreis c5",loc='left',fontsize=12,fontweight='bold')
im2=Image.open('loch-druck.png'); w2,h2=im2.size; top2=im2.crop((int(w2*0.1),int(h2*0.1),int(w2*0.9),int(h2*0.42)))
axd=fig.add_axes([0.53,0.30,0.44,0.22]); axd.imshow(top2); axd.axis('off'); axd.set_title("D  Druckbare Schalen (r = 20 mm, Wand 2 mm)",loc='left',fontsize=12,fontweight='bold')
def spalte(x,titel,absaetze,breite=48):
    fig.text(x,0.262,titel,fontsize=12.5,fontweight='bold',color=INK)
    fig.text(x,0.238,"\n".join(textwrap.fill(a,breite) for a in absaetze),fontsize=9.5,va='top',linespacing=1.4,color='#222')
spalte(0.04,"Was den Ausschlag gibt",["Bei gleichen Gliedern gibt es nur einen Formparameter: den Verwindungswinkel φ zwischen benachbarten Gelenkachsen. Größe und Gliedlänge skalieren nur.","Je kleiner φ, desto weiter schwingen c2 und c5: 240° beim Würfel, 276° beim Ikosaeder I, 360° bei φ = 60°. Darunter laufen sie ganz um (die Gelenke drehen voll durch)."])
spalte(0.36,"Warum dann ein Loch entsteht",["Solange c2 und c5 auf Bögen hin und her gehen, überstreicht die Diagonale eine geschlossene Hülle (Oloid). Laufen beide ganz um, verbindet die Diagonale zwei volle, ineinander verkettete Kreise: ein in sich verdrehtes Band mit Durchgang in der Mitte.","Zwischen 60° und 68° faltet sich die Fläche schon ein, bleibt aber zu."])
spalte(0.68,"Folgen für den Druck",["Kein Platonischer Ring liegt unter 60°; der Ikosaeder I (68,1°) ist am nächsten, aber zu. Für ein Loch braucht es einen eigenen Ring mit φ < 60°.","Das offene Gebilde ist ein Band ohne Innenraum und wird als Schale gedruckt. Kleines Loch: 58° (≈ 10 mm bei r = 20), großes Loch: ab 50° (≈ 20 mm)."],breite=44)
fig.text(0.04,0.012,"Werte aus der berechneten Bewegung der Gelenkkette (Umschlag zwischen 60,3° und 59° eingegrenzt). Druck nicht erprobt: das Band hat starke Überhänge und braucht Stützen.",fontsize=8.8,color='#777')
fig.savefig('Oloid-mit-Loch-Erklaerung.png',dpi=180,facecolor=BG); print('ok')

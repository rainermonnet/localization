import numpy as np, sys, textwrap
sys.path.insert(0,'../stl')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from ansicht import lade, zeichne
BG='#fbf8ef'
fig=plt.figure(figsize=(14,9.9),dpi=170); fig.patch.set_facecolor(BG)
fig.text(0.04,0.955,"Würfelgürtel zum Umstülpen (nach Paul Schatz)",fontsize=22,fontweight='bold',color='#d8543b')
fig.text(0.04,0.925,"Würfel minus zwei Sterne = Gürtel aus sechs Tetraedern mit Gelenkkanten. Würfelkante 60 mm, Druck mit Bambu Studio.",fontsize=11.5,color='#555')
bilder=[('s-wuerfel.png','1  Würfellage: Gürtel (orange) und die zwei Sterne (durchscheinend)'),('s-b60.png','2  der Gürtel öffnet sich'),('s-b150.png','3  er stülpt sich um'),('s-oloid.png','4  ein Glied fest: die Diagonale überstreicht den Oloid')]
for k,(f,t) in enumerate(bilder):
    im=Image.open('g/'+f).crop((170,70,1030,830)); ax=fig.add_axes([0.02+k*0.245,0.53,0.235,0.36]); ax.imshow(im); ax.axis('off'); ax.set_title(textwrap.fill(t,34),fontsize=10.5,loc='left')
ax=fig.add_axes([0.03,0.10,0.42,0.40]); T=lade('Wuerfelguertel_6_Glieder_Wuerfel60mm.stl'); T=T-T.reshape(-1,3).mean(0)
zeichne(ax,T,np.radians(25),np.radians(40),(0.95,0.62,0.30)); ax.set_aspect('equal'); ax.axis('off'); ax.set_xlim(-85,85); ax.set_ylim(-70,60)
ax.set_title("Druckplatte: sechs Glieder, je auf der langen Kante (143 × 140 mm)",fontsize=11,loc='left',fontweight='bold')
txt=["Gelenke: Knöchel-Scharniere auf den halben Würfelkanten (rot in der Animation). Jedes Glied hat an einer Kante einen Mittelknöchel, an der anderen zwei Außenknöchel; Spiel 0,5 mm radial, 0,4 mm axial.",
"Bolzen: 6 Stücke 1,75-mm-Filament, je ca. 23 mm, durch die 2-mm-Bohrungen stecken; Enden mit einem Tropfen Kleber oder kurz anschmelzen.",
"Reihenfolge: links Typ A (Glieder 1, 3, 5), rechts Typ B (2, 4, 6) - immer abwechselnd A, B, A, B … zum Ring verbinden; Mittelknöchel greift zwischen die Außenknöchel des Nachbarn.",
"Druck: PLA, 0,16 mm Schicht, 3 Wände, 20 % Füllung, Brim 3 mm. Die Glieder stehen auf der langen Kante (Flächen 39° zur Senkrechten), Stützen nur unter den Knöcheln (Baumstützen, nur Druckbett).",
"Nachgerechnet: über alle 1359 berechneten Stellungen der Umstülpung überschneiden sich die Glieder nirgends (Knöchel eingerechnet). Längere Gelenkkanten (über die halbe Würfelkante hinaus) würden zusammenstoßen."]
fig.text(0.50,0.47,"Bau",fontsize=13,fontweight='bold'); fig.text(0.50,0.445,"\n".join("• "+textwrap.fill(t,70,subsequent_indent="  ") for t in txt),fontsize=10,va='top',linespacing=1.45)
fig.text(0.04,0.03,"Nicht gedruckt erprobt. Druckerspiel kann Nacharbeit an den Knöcheln nötig machen (Bohrung mit 2-mm-Bohrer nachziehen).",fontsize=9,color='#777')
fig.savefig('Wuerfelguertel-Uebersicht.png',dpi=170,facecolor=BG); print('ok')

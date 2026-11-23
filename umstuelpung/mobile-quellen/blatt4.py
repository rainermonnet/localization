from PIL import Image, ImageDraw, ImageFont
import numpy as np, math
BG=(0xFB,0xF7,0xF1); INK=(0x2b,0x26,0x20); MUT=(0x6b,0x65,0x5b); MESS=(0xC9,0xA2,0x4A); FAD=(0x4A,0x7E,0xBB)
def laden(n):
    im=Image.open(f"m4/ans-{n}.png").convert("RGB"); d=ImageDraw.Draw(im); d.rectangle((0,0,900,240),fill=BG)
    a=np.array(im).astype(int); m=(np.abs(a-np.array(BG)).sum(2)>30); ys,xs=np.where(m)
    return im.crop((max(xs.min()-30,0),max(ys.min()-30,0),min(xs.max()+30,im.size[0]),min(ys.max()+30,im.size[1])))
V={n:laden(n) for n in ("schraeg","vorn","seite")}
W,H=2480,1754
S=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(S)
F=lambda s,b=False: ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-%s.ttf"%("Bold" if b else "Regular"),s)
d.text((60,36),"Oloid-Mobile 4: eine Drahtbahn, acht Größen",font=F(64,True),fill=(0xD8,0x54,0x3B))
d.text((60,116),"Der Drahtring ist die Bahn des Pentagon-Dodekaeders I (72°). An ihm hängen acht Oloide, groß bis klein nach Winkel, jeder am Silikonfaden im Fadenloch.",font=F(30),fill=MUT)
def einpassen(im,box):
    x0,y0,x1,y1=box; w,h=x1-x0,y1-y0; r=min(w/im.size[0],h/im.size[1]); n=im.resize((int(im.size[0]*r),int(im.size[1]*r)),Image.LANCZOS)
    S.paste(n,(x0+(w-n.size[0])//2,y0+(h-n.size[1])//2))
einpassen(V["schraeg"],(40,190,1340,1260)); d.text((60,196),"Schrägansicht",font=F(30,True),fill=INK)
einpassen(V["vorn"],(1380,220,1900,850)); d.text((1390,196),"Vorne",font=F(28,True),fill=INK)
einpassen(V["seite"],(1920,220,2440,850)); d.text((1930,196),"Von der Seite",font=F(28,True),fill=INK)
# ---- Detailzeichnung: Aufhaengung
bx,by=1380,930
d.text((bx+10,by-34),"Die Verbindungen im Detail",font=F(28,True),fill=INK)
cx=bx+110
# Draht-Querschnitt oben, Knoten, Faden
d.ellipse((cx-14,by+4,cx+14,by+32),outline=MESS,fill=(0xE6,0xCF,0x8A),width=4)
d.ellipse((cx-9,by+28,cx+9,by+46),fill=FAD)
d.line([(cx,by+46),(cx,by+118)],fill=FAD,width=4)
# Oloid (Tropfen), Spitze oben am Fadenloch
tipy=by+120; pts=[(cx,tipy)]
for t in np.linspace(0.12,2*math.pi-0.12,70): pts.append((cx+56*math.sin(t)*(1-0.3*math.cos(t)), tipy+95-95*math.cos(t)))
d.polygon(pts,fill=(0xE9,0x8A,0x3A),outline=INK)
d.ellipse((cx-5,tipy-4,cx+5,tipy+6),fill=(0x40,0x30,0x20))
d.text((cx-110,by+316),"Silikonfaden 0,5–1 mm",font=F(22),fill=FAD)
tx=cx+90
for k,l in enumerate(["Draht 1,5 mm: Faden zweimal","herumgeknotet, ein Tropfen","Sekundenkleber auf den Knoten."]): d.text((tx,by+6+k*27),l,font=F(22),fill=INK)
for k,l in enumerate(["Fadenloch Ø 1,2 mm, 8 mm tief:","Fadenende anrauen oder verknoten,","mit Epoxid oder Sekundenkleber","einkleben."]): d.text((tx,by+112+k*27),l,font=F(22),fill=INK)
d.line([(tx-6,by+126),(cx+8,tipy)],fill=MUT,width=2)
for k,l in enumerate(["Der Oloid hängt an der Spitze","genau über dem Schwerpunkt","(hohl, 5 bis 27 g)."]): d.text((tx,by+232+k*27),l,font=F(22),fill=INK)
# Ring-Aufhaengung
rx=bx+850; ry=by+110
d.line([(rx-130,ry+50),(rx-60,ry+15),(rx+0,ry+50),(rx+60,ry+85),(rx+130,ry+50)],fill=MESS,width=7,joint="curve")
d.line([(rx-75,ry+23),(rx,ry-70)],fill=INK,width=2); d.line([(rx+75,ry+68),(rx,ry-70)],fill=INK,width=2)
d.ellipse((rx-9,ry-80,rx+9,ry-62),fill=INK)
for k,l in enumerate(["Zwei Fäden zu den höchsten","Punkten, Knoten senkrecht","über dem Schwerpunkt:","Ring hängt waagrecht."]): d.text((rx-125,by+195+k*27),l,font=F(22),fill=INK)
d.line((40,1285,W-40,1285),fill=(0x8a,0x82,0x72),width=2)
def umbruch(text,font,breite):
    zl=[];z=""
    for w in text.split(" "):
        t=(z+" "+w).strip()
        if d.textlength(t,font=font)>breite and z: zl.append(z); z=w
        else: z=t
    zl.append(z); return zl
import json
P=json.load(open("plan3.json"))
NAMEN=["Würfel","Dodekaeder II","Tetraeder II · Oktaeder · Ikosaeder IV","Ikosaeder II, III","Dodekaeder III","Tetraeder I","Dodekaeder I","Ikosaeder I"]
PHI=[90,87.0,80.4,79.7,74.8,73.2,72.0,68.1]
# Spalte 1: Tabelle
x=60; d.text((x,1305),"Die acht Oloide",font=F(34,True),fill=INK)
d.text((x,1352),"Winkel / Körper",font=F(23,True),fill=MUT); d.text((x+520,1352),"Radius",font=F(23,True),fill=MUT); d.text((x+620,1352),"Länge",font=F(23,True),fill=MUT); d.text((x+710,1352),"Gewicht",font=F(23,True),fill=MUT)
for i in range(8):
    y=1384+i*31
    nm=NAMEN[i] if i!=2 else "Tetraeder II, Oktaeder, Ikosaeder IV"
    d.text((x,y),f"{str(PHI[i]).replace('.',',')}°  {nm}",font=F(23),fill=INK)
    d.text((x+520,y),f"{P['r_mm'][i]} mm",font=F(23),fill=INK); d.text((x+620,y),f"{P['ext'][i][2]/10:.1f} cm".replace('.',','),font=F(23),fill=INK); d.text((x+710,y),f"{P['masse'][i]:.0f} g".replace('.',','),font=F(23),fill=INK)
sp=[("Aufbau und Gleichgewicht",["Ein einziger Ring, Messingdraht 1,5 mm, 1,3 m lang, in die gerechnete Bahn der mittleren Ecke des Dodekaeders I gebogen (39 × 23 cm). Er hängt an zwei Fäden zu den höchsten Punkten; der Knoten sitzt senkrecht über dem gemeinsamen Schwerpunkt (Draht und alle acht Oloide), die Abweichung ist gerechnet und liegt unter 1 mm.","Die Fäden sind unterschiedlich lang (8 bis 26 cm), damit die Oloide auf verschiedenen Höhen hängen und nichts anstößt: Abstand zu Draht und zueinander mindestens 3 cm (nachgerechnet)."]),
    ("Maße und Material",["Höhe vom Haken bis zum tiefsten Oloid etwa 60 cm, Breite etwa 36 cm, Tiefe etwa 32 cm. Draht 1,3 m, Oloide zusammen etwa 112 g (hohl, Wand 2,4 mm), alles etwa 130 g.","Gewichte sind aus der Wandstärke hochgerechnet (etwa mit r²). Nach dem Druck wiegen und die Fadenpunkte am Ring entsprechend verschieben."])]
for k,(t,abs_) in enumerate(sp):
    x=1000+k*735; d.text((x,1305),t,font=F(34,True),fill=INK); y=1360
    for a_ in abs_:
        for l in umbruch(a_,F(25),690): d.text((x,y),l,font=F(25),fill=INK); y+=34
        y+=10
d.text((60,1708),"Zeichnung aus den gerechneten Bahnen. Der Entwurf ist nicht als Modell gebaut; Gewichte und Schwerpunkte vor dem endgültigen Aufhängen am Modell prüfen.",font=F(22),fill=MUT)
S.save("Oloid-Mobile-Entwurf-4.png"); print(S.size)

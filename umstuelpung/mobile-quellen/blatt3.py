from PIL import Image, ImageDraw, ImageFont
import numpy as np, math
BG=(0xFB,0xF7,0xF1); INK=(0x2b,0x26,0x20); MUT=(0x6b,0x65,0x5b); MESS=(0xC9,0xA2,0x4A); FAD=(0x4A,0x7E,0xBB)
def laden(n):
    im=Image.open(f"m3/ans-{n}.png").convert("RGB"); d=ImageDraw.Draw(im); d.rectangle((0,0,900,240),fill=BG)
    a=np.array(im).astype(int); m=(np.abs(a-np.array(BG)).sum(2)>30); ys,xs=np.where(m)
    return im.crop((max(xs.min()-30,0),max(ys.min()-30,0),min(xs.max()+30,im.size[0]),min(ys.max()+30,im.size[1])))
V={n:laden(n) for n in ("schraeg","vorn","seite")}
W,H=2480,1754
S=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(S)
F=lambda s,b=False: ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-%s.ttf"%("Bold" if b else "Regular"),s)
d.text((60,36),"Oloid-Mobile 3: Kaskade aus Draht-Bahnen",font=F(64,True),fill=(0xD8,0x54,0x3B))
d.text((60,116),"Jeder Ring ist die Bahn eines umgestülpten Körpers, aus einem Draht gebogen; an jedem hängt der Oloid seines Körpers am Silikonfaden im Fadenloch.",font=F(30),fill=MUT)
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
for k,l in enumerate(["Der Oloid hängt an der Spitze","genau über dem Schwerpunkt","(hohl, ca. 12 g)."]): d.text((tx,by+232+k*27),l,font=F(22),fill=INK)
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
sp=[("Aufbau (drei Ebenen)",["Wurzel: die Bahn des Pentagon-Dodekaeders I (72°), Glied 110 mm, Ring 39 × 23 cm. Darunter drei Ringe (Glied 68 mm): Tetraeder I (73,2°), Dodekaeder III (74,8°), Ikosaeder I (68,1°). Darunter vier (Glied 42 mm): Tetraeder II / Oktaeder / Ikosaeder IV (80,4°), Ikosaeder II / III (79,7°), Dodekaeder II (87°), Würfel (90°).","An jedem Ring hängt der Oloid seiner Bahn (gleicher Winkel φ) und die Ringe der nächsten Ebene."]),
    ("Gleichgewicht",["Für jeden Ring ist der Schwerpunkt aus Draht, Oloid und allem, was darunter hängt, gerechnet. Die beiden Aufhängepunkte liegen auf einer Sehne durch diesen Punkt, der Knoten senkrecht darüber; die Abweichung beträgt unter 2 mm.","Alle Oloide gelten als gleich schwer (12 g). Die Abstände zwischen Drähten und Oloiden sind nachgerechnet (mindestens 10 cm zwischen den Ringen); beim Aufhängen vermutlich nachjustieren."]),
    ("Maße und Material",["Höhe vom Haken bis zum tiefsten Oloid etwa 1,0 m, Breite 65 cm, Tiefe 40 cm. Draht zusammen etwa 5,7 m Messing 1,5 mm (Wurzel 1,3 m, Ebene 2 je 0,8 m, Ebene 3 je 0,5 m), Gesamtgewicht etwa 180 g.","Bahnform: gerechnete Kurve der mittleren Ecke; als 1:1-Biegeschablone (Ausdruck) liefere ich sie auf Wunsch."])]
for k,(t,abs_) in enumerate(sp):
    x=60+k*810; d.text((x,1305),t,font=F(34,True),fill=INK); y=1360
    for a in abs_:
        for l in umbruch(a,F(25),740): d.text((x,y),l,font=F(25),fill=INK); y+=34
        y+=10
d.text((60,1708),"Zeichnung aus den gerechneten Bahnen. Der Entwurf ist nicht als Modell gebaut; Gewichte und Schwerpunkte vor dem endgültigen Aufhängen am Modell prüfen.",font=F(22),fill=MUT)
S.save("Oloid-Mobile-Entwurf-3.png"); print(S.size)

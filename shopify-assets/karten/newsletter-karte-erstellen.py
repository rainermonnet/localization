from PIL import Image, ImageDraw, ImageFont, ImageFilter
import qrcode, numpy as np, sys, math
W,H=1240,1748
CREAM=(251,246,236); PINK=(246,228,226); RED=(190,52,40); BROWN=(59,42,32); GREY=(110,92,80)
SHIRT=(223,191,130); SKIN=(194,132,82); LINE=(74,46,28)
URL="https://zwergenladen.info/pages/newsletter?utm_source=laden&utm_medium=qr&utm_campaign=newsletter"
SERIF_B="/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf"; SANS="/usr/share/fonts/opentype/inter/Inter-Regular.otf"; SANS_M="/usr/share/fonts/opentype/inter/Inter-Medium.otf"; SANS_SB="/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
F=lambda n,s: ImageFont.truetype(n,s)
card=Image.new("RGBA",(W,H),CREAM+(255,)); d=ImageDraw.Draw(card)
d.rectangle([0,0,W,280],fill=PINK)
def ctext(y,t,font,fill,spacing=0):
    if spacing:
        w=sum(d.textlength(c,font=font) for c in t)+spacing*(len(t)-1); x=(W-w)/2
        for c in t: d.text((x,y),c,font=font,fill=fill); x+=d.textlength(c,font=font)+spacing
    else:
        w=d.textlength(t,font=font); d.text(((W-w)/2,y),t,font=font,fill=fill)
ctext(66,"NEWSLETTER",F(SANS_SB,34),RED,spacing=8)
ctext(118,"Post vom Zwergenladen",F(SERIF_B,92),BROWN)

# --- Zwerg freistellen, obere Hand entfernen ---
g=Image.open(sys.argv[1]).convert("RGB"); a=np.asarray(g).astype(np.int16)
alpha=np.where(a.min(axis=2)>238,0,255).astype(np.uint8)
yy,xx=np.mgrid[0:a.shape[0],0:a.shape[1]]
from PIL import ImageFilter as IF
mn=a.min(axis=2); rb=a[...,0]-a[...,2]
zone=(xx>=630)&(yy>=700)&(yy<=965)
haut=(rb>85)&(mn<150)                      # Hautfarbe der Hand
dunkel=(mn<120)&(xx>=652)                  # Konturlinie der Hand rechts vom Bart
kern=Image.fromarray(((haut|dunkel)&zone).astype(np.uint8)*255)
bereich=np.asarray(kern.filter(IF.MaxFilter(31)))>0          # Hand plus heller Saum
bart=(mn>165)&(mn<=205)&(rb<75)
bartkern=np.asarray(Image.fromarray(bart.astype(np.uint8)*255).filter(IF.MinFilter(9)))>0
alpha[bereich & zone & ~bartkern]=0
alpha[zone & (mn>205) & (xx>=672)]=0          # restlicher heller Saum
g.putalpha(Image.fromarray(alpha).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.2)))
s=980/g.height; g=g.resize((int(g.width*s),980),Image.LANCZOS)
gx,gy=70,H-980-140
P=lambda x,y:(gx+x*s,gy+y*s)

# --- Karte mit QR (leicht geneigt) ---
cw,ch=470,650; qs=400
k=Image.new("RGBA",(cw,ch),(0,0,0,0)); kd=ImageDraw.Draw(k)
kd.rounded_rectangle([0,0,cw-1,ch-1],radius=30,fill=(255,253,248,255),outline=LINE,width=6)
q=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,border=0,box_size=10); q.add_data(URL); q.make(fit=True)
k.paste(q.make_image(fill_color=BROWN,back_color="white").convert("RGB").resize((qs,qs),Image.NEAREST),((cw-qs)//2,36))
fq=F(SERIF_B,44); t1="Scannen & anmelden"; tw=kd.textlength(t1,font=fq)
kd.text(((cw-tw)/2,36+qs+44),t1,font=fq,fill=RED)
ang=-7
kr=k.rotate(ang,expand=True,resample=Image.BICUBIC)
cx,cy=845,700                                       # Kartenmitte
kx,ky=int(cx-kr.width/2),int(cy-kr.height/2)
sh=Image.new("RGBA",kr.size,(0,0,0,0)); sh.putalpha(kr.getchannel("A").point(lambda v:int(v*0.28)))
sh=sh.filter(ImageFilter.GaussianBlur(14))
card.alpha_composite(sh,(kx+14,ky+18)); card.alpha_composite(kr,(kx,ky))
# Ecke unten links der Karte nach Drehung
def rot(px,py):
    r=math.radians(-ang); ox,oy=px-cw/2,py-ch/2
    return (cx+ox*math.cos(r)-oy*math.sin(r), cy+ox*math.sin(r)+oy*math.cos(r))
grip=rot(30,ch-30)                                 # Griffpunkt am linken Kartenrand

# --- Arm: kommt hinter dem Bart hervor, Ellbogen nah am Körper, Unterarm hoch zur Kartenecke ---
start=P(655,845); wrist=(grip[0]-14,grip[1]+40)
elbow=(start[0]+(wrist[0]-start[0])*0.55+28, start[1]-8)
pts=[start,elbow,wrist]
arm=Image.new("RGBA",(W,H),(0,0,0,0)); ad=ImageDraw.Draw(arm)
def strich(width,col):
    ad.line(pts,fill=col,width=width,joint="curve")
    for p in pts: ad.ellipse([p[0]-width/2,p[1]-width/2,p[0]+width/2,p[1]+width/2],fill=col)
ad.ellipse([start[0]-56,start[1]-86,start[0]+50,start[1]+72],fill=LINE)
ad.ellipse([start[0]-50,start[1]-80,start[0]+44,start[1]+66],fill=SHIRT)
strich(92,LINE); strich(80,SHIRT)
ad.ellipse([start[0]-44,start[1]-74,start[0]+38,start[1]+60],fill=SHIRT)
schatten=[(x+10,y+12) for x,y in pts]
ad.line(schatten,fill=(201,166,104),width=30,joint="curve")
strich_in=[(x-6,y-8) for x,y in pts]
ad.line(strich_in,fill=SHIRT,width=44,joint="curve")
for p in strich_in: ad.ellipse([p[0]-22,p[1]-22,p[0]+22,p[1]+22],fill=SHIRT)
# Ärmelsaum am Handgelenk
ad.line([(wrist[0]-40,wrist[1]+10),(wrist[0]+36,wrist[1]+20)],fill=LINE,width=6)
# Hand: rundliche Faust mit Daumen vorn auf der Karte
hx,hy=grip
ad.ellipse([hx-46,hy-40,hx+40,hy+44],fill=SKIN,outline=LINE,width=6)
ad.ellipse([hx-2,hy-30,hx+40,hy+8],fill=(205,146,96),outline=LINE,width=5)   # Daumen
ad.arc([hx-30,hy+2,hx+10,hy+34],start=300,end=60,fill=LINE,width=4)
arm=arm.filter(ImageFilter.GaussianBlur(0.9))
card.alpha_composite(arm)
card.alpha_composite(g,(gx,gy))

# --- Text unter der Karte, tiefer und größer ---
fx=640; fy=1170
for i,line in enumerate(["Neuheiten, Geschenkideen","und Termine aus dem","Laden – direkt in dein","Postfach."]):
    d.text((fx,fy+i*56),line,font=F(SANS,40),fill=BROWN)
for i,line in enumerate(["Du bestätigst die Anmeldung","per E-Mail. Abmelden jederzeit."]):
    d.text((fx,fy+250+i*40),line,font=F(SANS,28),fill=GREY)
d.line([80,H-118,W-80,H-118],fill=(222,207,192),width=2)
ctext(H-92,"Schwimmbadstraße 36 · 79100 Freiburg · zwergenladen.info",F(SANS_M,30),BROWN)
out=card.convert("RGB")
out.save("zwergenladen-newsletter-karte-A6.png",dpi=(300,300)); out.save("zwergenladen-newsletter-karte-A6.pdf",resolution=300)
out.resize((620,874)).save("vorschau.png"); out.crop((330,860,760,1200)).resize((860,680)).save("detail4.png")
print("Griff",[int(v) for v in grip],"Arm",[tuple(int(c) for c in p) for p in pts])

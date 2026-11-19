from PIL import Image, ImageDraw, ImageFont, ImageFilter
import qrcode, numpy as np, sys
W,H=1240,1748
CREAM=(251,246,236); PINK=(246,228,226); RED=(190,52,40); BROWN=(59,42,32); WOOD=(200,156,110); WOOD_D=(150,104,62); GREY=(110,92,80)
URL="https://zwergenladen.info/pages/newsletter?utm_source=laden&utm_medium=qr&utm_campaign=newsletter"
SERIF_B="/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf"; SANS="/usr/share/fonts/opentype/inter/Inter-Regular.otf"; SANS_M="/usr/share/fonts/opentype/inter/Inter-Medium.otf"; SANS_SB="/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
F=lambda n,s: ImageFont.truetype(n,s)
card=Image.new("RGB",(W,H),CREAM); d=ImageDraw.Draw(card)
d.rectangle([0,0,W,280],fill=PINK)
def ctext(y,t,font,fill,spacing=0):
    if spacing:
        w=sum(d.textlength(c,font=font) for c in t)+spacing*(len(t)-1); x=(W-w)/2
        for c in t: d.text((x,y),c,font=font,fill=fill); x+=d.textlength(c,font=font)+spacing
    else:
        w=d.textlength(t,font=font); d.text(((W-w)/2,y),t,font=font,fill=fill)
ctext(66,"NEWSLETTER",F(SANS_SB,34),RED,spacing=8)
ctext(118,"Post vom Zwergenladen",F(SERIF_B,92),BROWN)
# Zwerg
g=Image.open(sys.argv[1]).convert("RGB"); a=np.asarray(g).astype(np.int16)
alpha=np.where(a.min(axis=2)>238,0,255).astype(np.uint8)
g.putalpha(Image.fromarray(alpha).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.2)))
s=980/g.height; g=g.resize((int(g.width*s),980),Image.LANCZOS)
gx,gy=70,H-980-140
h1=(gx+470*s,gy+960*s); h2=(gx+700*s,gy+820*s)
slope=(h2[1]-h1[1])/(h2[0]-h1[0])          # negativ: Stab steigt nach rechts
qs=420; pad=40; bw,bh=qs+2*pad, qs+2*pad+72
sy0=345; contact_y=sy0+bh-24
contact_x=h2[0]+(contact_y-h2[1])/slope
sx0=int(contact_x-bw*0.32)
start=(h1[0]-(h2[0]-h1[0])*0.4, h1[1]-(h2[1]-h1[1])*0.4)
d.line([start,(contact_x,contact_y)],fill=BROWN,width=34); d.line([start,(contact_x,contact_y)],fill=WOOD_D,width=22)
d.rounded_rectangle([sx0,sy0,sx0+bw,sy0+bh],radius=28,fill=WOOD,outline=BROWN,width=7)
for nx,ny in [(sx0+22,sy0+22),(sx0+bw-22,sy0+22),(sx0+22,sy0+bh-22),(sx0+bw-22,sy0+bh-22)]:
    d.ellipse([nx-7,ny-7,nx+7,ny+7],fill=BROWN)
d.rounded_rectangle([sx0+pad-12,sy0+pad-12,sx0+pad+qs+12,sy0+pad+qs+12],radius=14,fill=(255,255,255),outline=BROWN,width=3)
q=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,border=0,box_size=10); q.add_data(URL); q.make(fit=True)
card.paste(q.make_image(fill_color=BROWN,back_color="white").convert("RGB").resize((qs,qs),Image.NEAREST),(sx0+pad,sy0+pad))
f=F(SERIF_B,44); t1="Scannen & anmelden"; w=d.textlength(t1,font=f); d.text((sx0+(bw-w)/2,sy0+pad+qs+20),t1,font=f,fill=BROWN)
card.paste(g,(gx,gy),g)
# Text unter dem Schild, rechts vom Zwerg, unterhalb des Stabs
fx=sx0+10; fy=sy0+bh+90
for i,line in enumerate(["Neuheiten, Geschenkideen","und Termine aus dem Laden –","direkt in dein Postfach."]):
    d.text((fx,fy+i*50),line,font=F(SANS,35),fill=BROWN)
for i,line in enumerate(["Du bestätigst die Anmeldung","per E-Mail. Abmelden jederzeit."]):
    d.text((fx,fy+190+i*38),line,font=F(SANS,26),fill=GREY)
d.line([80,H-118,W-80,H-118],fill=(222,207,192),width=2)
ctext(H-92,"Schwimmbadstraße 36 · 79100 Freiburg · zwergenladen.info",F(SANS_M,30),BROWN)
print("Schild",sx0,sy0,sx0+bw,sy0+bh,"Kontakt",int(contact_x),contact_y,"Zwerg rechts",gx+g.width,"Text ab",fy)
card.save("zwergenladen-newsletter-karte-A6.png",dpi=(300,300)); card.save("zwergenladen-newsletter-karte-A6.pdf",resolution=300)
card.resize((620,874)).save("vorschau.png")

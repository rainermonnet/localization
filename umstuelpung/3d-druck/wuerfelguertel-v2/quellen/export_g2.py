import numpy as np, manifold3d as m3, os
import guertel as G, scharnier as S, waben_bau as WB
lok = G.glieder_lokal(0.5); O = "guertel2/stl"; os.makedirs(O, exist_ok=True)
L = WB.drucklage(*WB.glied_fertig(0, lok)[:3]); R_ = WB.drucklage(*WB.glied_fertig(1, lok)[:3])
H = {s: S.scharnier_druck(s) for s in (0.3, 0.4, 0.5)}
for s, h in H.items(): print("Scharnier", s, "Teile", len(h.decompose()))
WB.schreibe(f"{O}/Glied_A_3x.stl", L, "Wuerfelguertel Glied A")
WB.schreibe(f"{O}/Glied_B_spiegel_3x.stl", R_, "Wuerfelguertel Glied B")
for s, h in H.items(): WB.schreibe(f"{O}/Scharnier_Spiel_{s:.1f}.stl", h, f"Scharnier Spiel {s}")
def zentriert(M, cx=128, cy=128):
    bb = M.bounding_box(); return M.translate([cx - (bb[0] + bb[3])/2, cy - (bb[1] + bb[4])/2, -bb[2]])
# Probedruck: Glied A + Glied B (gegenueber, ineinander verschachtelt) + 3 Scharniere
B2 = R_.rotate([0, 0, 180]); bb = B2.bounding_box(); B2 = B2.translate([-bb[0], -bb[1] + 0, 0])
pl = [L, B2.translate([0, 40, 0])]
x = 75
for s in (0.3, 0.4, 0.5):
    pl.append(H[s].rotate([0, 0, 90]).translate([x + 14, 0, 0])); x += 0
yy = [0, 30, 60]
pl = [L, B2.translate([0, 38, 0])] + [H[s].rotate([0, 0, 90]).translate([88, yy[i], 0]) for i, s in enumerate((0.3, 0.4, 0.5))]
P = zentriert(m3.Manifold.compose(pl)); print("Probedruck bbox", np.round(P.bounding_box(), 1))
WB.schreibe(f"{O}/Probedruck_A1_2Glieder_3Scharniere.stl", P, "Probedruck Wuerfelguertel")
# Vollsatz: 3x A, 3x B, 6 Scharniere (Spiel 0.4)
vs = []
for i in range(3):
    vs.append(L.translate([0, i*80, 0])); vs.append(B2.translate([0, i*80 + 38, 0]))
for i in range(6):
    vs.append(H[0.4].rotate([0, 0, 90]).translate([90 + (i % 2)*34, (i//2)*70 + 5, 0]))
V = zentriert(m3.Manifold.compose(vs)); print("Vollsatz bbox", np.round(V.bounding_box(), 1))
WB.schreibe(f"{O}/Vollsatz_A1_6Glieder_6Scharniere.stl", V, "Wuerfelguertel Vollsatz")
# Kollision der Teile auf der Platte
for nm, parts in (("Probe", pl), ("Voll", vs)):
    w = 0
    for a in range(len(parts)):
        for b in range(a + 1, len(parts)): w = max(w, (parts[a] ^ parts[b]).volume())
    print(nm, "Teile beruehren sich (mm3):", round(w, 3))

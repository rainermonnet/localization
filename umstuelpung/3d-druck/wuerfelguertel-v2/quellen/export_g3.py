"""Alle 6 Glieder (Waben aussen) + 6 Scharniere fuer den Bambu Lab A1."""
import numpy as np, manifold3d as m3, os
import guertel as G, scharnier as S, waben_bau as WB
lok = G.glieder_lokal(0.5); O = "guertel2/stl"; os.makedirs(O, exist_ok=True)
glieder = []
for k in range(6):
    D = WB.drucklage(*WB.glied_fertig(k, lok)[:3]); typ = "A" if k % 2 == 0 else "B"
    WB.schreibe(f"{O}/Glied_{k+1}_{typ}.stl", D, f"Wuerfelguertel Glied {k+1} {typ}"); glieder.append(D)
H = {s: S.scharnier_druck(s) for s in (0.3, 0.4, 0.5)}
for s, h in H.items(): WB.schreibe(f"{O}/Scharnier_Spiel_{s:.1f}.stl", h, f"Scharnier Spiel {s}")
def zentriert(M, cx=128, cy=128):
    bb = M.bounding_box(); return M.translate([cx - (bb[0] + bb[3])/2, cy - (bb[1] + bb[4])/2, -bb[2]])
def platte(teile, fn, name):
    P = zentriert(m3.Manifold.compose(teile)); WB.schreibe(fn, P, name)
    w = max((teile[a] ^ teile[b]).volume() for a in range(len(teile)) for b in range(a + 1, len(teile)))
    print(fn, "bbox", np.round(P.bounding_box(), 1), "Beruehrung", round(w, 4))
def b_lage(M):
    M = M.rotate([0, 0, 180]); bb = M.bounding_box(); return M.translate([-bb[0], -bb[1], 0])
# Platte 1: alle 6 Glieder, Platte 2: 6 Scharniere (Spiel 0,4)
pl = []
for i in range(3):
    pl.append(glieder[2*i].translate([0, i*80, 0])); pl.append(b_lage(glieder[2*i + 1]).translate([0, i*80 + 38, 0]))
platte(pl, f"{O}/Platte1_A1_6_Glieder.stl", "6 Glieder")
sch = [H[0.4].rotate([0, 0, 90]).translate([(i % 3)*36, (i//3)*34, 0]) for i in range(6)]
platte(sch, f"{O}/Platte2_A1_6_Scharniere_Spiel_0.4.stl", "6 Scharniere")
# Bettkontakt
me = glieder[0].to_mesh(); V = np.asarray(me.vert_properties)[:, :3]; T = np.asarray(me.tri_verts); tri = V[T]
n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); a = np.linalg.norm(n, axis=1)/2; nz = n[:, 2]/(2*a + 1e-12)
print("Bettkontakt je Glied mm2:", round(a[(nz < -0.999) & (tri[:, :, 2].mean(1) < 0.01)].sum()))
# Probedruck: Glied 1 + Glied 2 + 3 Scharniere (0,3/0,4/0,5)
pr = [glieder[0], b_lage(glieder[1]).translate([0, 38, 0])] + [H[s].rotate([0, 0, 90]).translate([88, 30*i, 0]) for i, s in enumerate((0.3, 0.4, 0.5))]
platte(pr, f"{O}/Probedruck_A1_2Glieder_3Scharniere.stl", "Probedruck")

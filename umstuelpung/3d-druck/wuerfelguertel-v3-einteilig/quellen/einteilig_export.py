import numpy as np, manifold3d as m3, os, json
import guertel as G, einteilig as E, einteilig_lage as L, waben_bau as WB
D2, D4, ROT = np.radians(12), np.radians(24), 6.0
O = "guertel3"; os.makedirs(O, exist_ok=True)
T, B, PL = E.teile(L.lok)
P = L.P
def schnitt_glied(k):
    """Sperrzone fuer Waben: um beide Gelenkachsen"""
    c = []
    for (a, b) in ((P[k][0], P[k][1]), (P[k][2], P[k][3])):
        ax = E.Achse(a, b); c.append(ax.zyl(-4, 39, E.RF + 1.2))
    return c[0] + c[1]
fertig = []
for k in range(6):
    _, V, pl = E.koerper(P[k])
    bett = 2 if k % 2 == 0 else 0; senk = 0 if k % 2 == 0 else 2
    up = -pl[bett][0]
    cut = schnitt_glied(k); WB.schnitt = lambda taschen, c=cut: c
    W = WB.waben_flaeche(V, senk, up, None) + WB.waben_flaeche(V, bett, up, None, tiefe=WB.TIEFE_BETT, rand=WB.RAND_BETT)
    Mk = T[k] - m3.Manifold.compose(W) if W else T[k]
    print(k, "Waben", sum(len(w.decompose()) for w in W), "Teile", len(Mk.decompose()))
    fertig.append(Mk)
M = L.kette(D2, D4)
druck = [fertig[k].transform(M[k][:3, :]) for k in range(6)]
X = m3.Manifold.compose(druck)
bb = X.bounding_box(); cx, cy = (bb[0] + bb[3])/2, (bb[1] + bb[4])/2
X = X.translate([-cx, -cy, 0]).rotate([0, 0, ROT]); bb = X.bounding_box()
X = X.translate([128 - (bb[0] + bb[3])/2, 128 - (bb[1] + bb[4])/2, -bb[2]])
print("bbox", np.round(X.bounding_box(), 1), "Teile", len(X.decompose()), "Volumen cm3", round(X.volume()/1000, 1))
WB.schreibe(f"{O}/Wuerfelguertel_einteilig_A1_Spiel05.stl", X, "Wuerfelguertel einteilig")
import pickle
pickle.dump([(np.asarray(f.to_mesh().vert_properties)[:, :3], np.asarray(f.to_mesh().tri_verts)) for f in fertig], open(f"{O}/glieder_lokal.pkl", "wb"))
# --- Zweifarbig: Glieder 1,3,5 (Index 0,2,4) weiss, Glieder 2,4,6 (Index 1,3,5) Holz; gleiche Lage wie oben
def lage(parts):
    Y = m3.Manifold.compose(parts).translate([-cx, -cy, 0]).rotate([0, 0, ROT]).translate([128 - (bb[0] + bb[3])/2, 128 - (bb[1] + bb[4])/2, -bb[2]])
    return Y
gruppen = {"weiss": [druck[k] for k in (0, 2, 4)], "holz": [druck[k] for k in (1, 3, 5)]}
for nm, ps in gruppen.items():
    Y = lage(ps); WB.schreibe(f"{O}/Wuerfelguertel_einteilig_A1_Spiel05_Teil_{nm}.stl", Y, f"Wuerfelguertel {nm}")
    print(nm, np.round(Y.bounding_box(), 2))

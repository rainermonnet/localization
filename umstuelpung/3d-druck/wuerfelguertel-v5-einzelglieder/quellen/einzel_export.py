import numpy as np, manifold3d as m3, os
from shapely.geometry import MultiPoint
import guertel as G, einzel as E, waben_bau as WB, ueberhang as U
from einteilig import Achse
O = "guertel5"; os.makedirs(O, exist_ok=True); ABST = 11.0
lok = G.glieder_lokal(0.5); T, _ = E.teile(lok)
fertig = []
for k in range(6):
    P = lok[k]*E.A_MM; _, V, pl = E.koerper(P); up = -pl[2][0]
    cut = Achse(P[0], P[1]).zyl(-9, 40, E.RF + 1.2) + Achse(P[2], P[3]).zyl(-9, 40, E.RF + 1.2)
    WB.schnitt = lambda taschen, c=cut: c
    W = WB.waben_flaeche(V, 0, up, None) + WB.waben_flaeche(V, 2, up, None, tiefe=WB.TIEFE_BETT, rand=WB.RAND_BETT)
    M = T[k] - m3.Manifold.compose(W) if W else T[k]
    D = WB.drucklage(M, V, up); fertig.append(D)
    print(k, "Waben", sum(len(w.decompose()) for w in W), "Teile", len(D.decompose()))
U.pruefe(fertig[0], "Glied 1 mit Waben"); U.pruefe(fertig[1], "Glied 2 mit Waben")
fp = lambda M: MultiPoint(np.asarray(M.to_mesh().vert_properties)[:, :2]).convex_hull
def b_lage(M):
    M = M.rotate([0, 0, 180]); bb = M.bounding_box(); return M.translate([-bb[0], -bb[1], 0])
def stapel(teile):
    out = []
    for t in teile:
        if not out: out.append(t); continue
        lo, hi = out[-1].bounding_box()[1], 400.0
        for _ in range(40):
            mid = (lo + hi)/2; c = t.translate([0, mid, 0])
            if min(fp(c).distance(fp(o)) for o in out) >= ABST: hi = mid
            else: lo = mid
        out.append(t.translate([0, hi, 0]))
    return out
def platte(teile, fn, name):
    P = m3.Manifold.compose(teile); bb = P.bounding_box()
    P = P.translate([128 - (bb[0] + bb[3])/2, 128 - (bb[1] + bb[4])/2, -bb[2]]); WB.schreibe(fn, P, name)
    print(fn, "Ausdehnung", round(bb[3] - bb[0], 1), "x", round(bb[4] - bb[1], 1), "x", round(bb[5] - bb[2], 1), "Teile", len(P.decompose()))
platte(stapel([fertig[0], b_lage(fertig[2]), fertig[4]]), f"{O}/Platte_Glieder_1-3-5_weiss.stl", "Glieder 1 3 5 weiss")
platte(stapel([fertig[1], b_lage(fertig[3]), fertig[5]]), f"{O}/Platte_Glieder_2-4-6_Holz.stl", "Glieder 2 4 6 Holz")
for k in range(6): WB.schreibe(f"{O}/Glied_{k+1}_{'weiss' if k % 2 == 0 else 'Holz'}.stl", fertig[k], f"Glied {k+1}")
platte(stapel([fertig[0], b_lage(fertig[1])]), f"{O}/Probe_Glied_1_und_2.stl", "Probe Glied 1 und 2")
import pickle
lokal = []
for k in range(6):
    P = lok[k]*E.A_MM; _, V, pl = E.koerper(P); up = -pl[2][0]
    cut = Achse(P[0], P[1]).zyl(-9, 40, E.RF + 1.2) + Achse(P[2], P[3]).zyl(-9, 40, E.RF + 1.2)
    WB.schnitt = lambda taschen, c=cut: c
    W = WB.waben_flaeche(V, 0, up, None) + WB.waben_flaeche(V, 2, up, None, tiefe=WB.TIEFE_BETT, rand=WB.RAND_BETT)
    M = T[k] - m3.Manifold.compose(W)
    me = M.to_mesh(); lokal.append((np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts)))
Ts, _ = E.teile(lok, mit_stift=True)
stifte = []
for k in range(6):
    S_ = Ts[k] - T[k]; me = S_.to_mesh(); stifte.append((np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts)))
pickle.dump((lokal, stifte), open(f"{O}/lokal.pkl", "wb"))

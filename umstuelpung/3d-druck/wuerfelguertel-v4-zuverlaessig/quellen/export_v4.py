"""Zuverlaessige Variante: Glieder einzeln liegend (ohne Druckgelenke), Scharniere flach gedruckt (Spiel 0,5), eingeklebt.
Weiss: Glieder 1,3,5 - Holz: Glieder 2,4,6 - jede Platte nur eine Farbe (kein AMS-Wechsel)."""
import numpy as np, manifold3d as m3, os
from shapely.geometry import MultiPoint
import guertel as G, scharnier as S, waben_bau as WB
S.SPIEL = 0.5
O = "guertel4"; os.makedirs(O, exist_ok=True); ABST = 11.0
lok = G.glieder_lokal(0.5)
gl = [WB.drucklage(*WB.glied_fertig(k, lok)[:3]) for k in range(6)]
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
def zentriert(teile, fn, name):
    P = m3.Manifold.compose(teile); bb = P.bounding_box()
    P = P.translate([128 - (bb[0] + bb[3])/2, 128 - (bb[1] + bb[4])/2, -bb[2]]); WB.schreibe(fn, P, name)
    d = min((fp(teile[a]).distance(fp(teile[b])) for a in range(len(teile)) for b in range(a + 1, len(teile))), default=0)
    print(fn, "Ausdehnung", round(bb[3] - bb[0], 1), "x", round(bb[4] - bb[1], 1), "Abstand", round(d, 1), "Teile", len(P.decompose()))
# weiss: 1,3,5 (gleiche Haendigkeit); abwechselnd gedreht verschachtelt
w = [gl[0], b_lage(gl[2]), gl[4]]; h = [gl[1], b_lage(gl[3]), gl[5]]
zentriert(stapel(w), f"{O}/Platte_A_Glieder_1-3-5_weiss.stl", "Glieder 1 3 5 weiss")
zentriert(stapel(h), f"{O}/Platte_B_Glieder_2-4-6_Holz.stl", "Glieder 2 4 6 Holz")
H = S.scharnier_druck(0.5).rotate([0, 0, 90]); bb = H.bounding_box(); H = H.translate([-bb[0], -bb[1], 0])
sch = [H.translate([(i % 3)*(28 + 8), (i//3)*(25 + 8), 0]) for i in range(6)]
zentriert(sch, f"{O}/Platte_C_6_Scharniere_Spiel_0.5_weiss.stl", "6 Scharniere")
zentriert([H], f"{O}/Test_1_Scharnier_Spiel_0.5.stl", "Testscharnier")

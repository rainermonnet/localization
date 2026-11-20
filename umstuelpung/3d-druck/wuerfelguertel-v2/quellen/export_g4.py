"""Alles auf einer Platte: 6 Glieder + 6 Scharniere, Abstand >= 11 mm (Platz fuer 5-mm-Brim)."""
import numpy as np, manifold3d as m3
from shapely.geometry import MultiPoint
import guertel as G, scharnier as S, waben_bau as WB
ABST = 11.0
lok = G.glieder_lokal(0.5)
gl = [WB.drucklage(*WB.glied_fertig(k, lok)[:3]) for k in range(6)]
def b_lage(M):
    M = M.rotate([0, 0, 180]); bb = M.bounding_box(); return M.translate([-bb[0], -bb[1], 0])
gl = [g if k % 2 == 0 else b_lage(g) for k, g in enumerate(gl)]
H = S.scharnier_druck(0.4).rotate([0, 0, 90]); bb = H.bounding_box(); H = H.translate([-bb[0], -bb[1], 0])
fp = lambda M: MultiPoint(np.asarray(M.to_mesh().vert_properties)[:, :2]).convex_hull
def stapel(teile, x0):
    """Teile in einer Spalte von unten nach oben, jeweils so dicht wie moeglich mit Abstand ABST"""
    out = []; y = 0.0
    for t in teile:
        y = 0.0 if not out else y
        lo, hi = (out[-1].bounding_box()[1] if out else 0.0), 400.0
        if out:
            lo = out[-1].bounding_box()[1]
            for _ in range(40):
                mid = (lo + hi)/2; c = t.translate([x0, mid, 0])
                if min(fp(c).distance(fp(o)) for o in out) >= ABST: hi = mid
                else: lo = mid
            y = hi
        out.append(t.translate([x0, y, 0]))
    return out
best = None
for anordnung in ("2 Spalten", "1 Spalte"):
    if anordnung == "2 Spalten":
        s1 = stapel([gl[0], gl[1], gl[2]], 0); s2 = stapel([gl[3], gl[4], gl[5]], 65 + ABST)
        xh = 2*65 + 2*ABST
    else:
        s1 = stapel(gl, 0); s2 = []; xh = 65 + ABST
    sh = stapel([H]*3, xh) + stapel([H]*3, xh + 28 + ABST)
    alle = s1 + s2 + sh; P = m3.Manifold.compose(alle); bb = P.bounding_box()
    print(anordnung, "Ausdehnung", round(bb[3] - bb[0], 1), "x", round(bb[4] - bb[1], 1), "mm")
    if bb[3] - bb[0] <= 236 and bb[4] - bb[1] <= 236 and best is None: best = (alle, P)
alle, P = best
bb = P.bounding_box(); P = P.translate([128 - (bb[0] + bb[3])/2, 128 - (bb[1] + bb[4])/2, 0])
d = min(fp(alle[a]).distance(fp(alle[b])) for a in range(len(alle)) for b in range(a + 1, len(alle)))
print("kleinster Abstand", round(d, 2), "bbox", np.round(P.bounding_box(), 1))
WB.schreibe("guertel2/stl/Alles_auf_einer_Platte_A1.stl", P, "Wuerfelguertel komplett")

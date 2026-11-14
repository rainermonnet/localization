"""Oloid massiv, aufrecht, Fadenloch an der Spitze, Fuss mit Luftspalt:
nur die unterste Spitze steckt 0,25 mm im Fuss (duenne Klinge trennt sie), Rippen beruehren den Koerper nicht."""
import numpy as np, sys
import manifold3d as m3
sys.path.insert(0, '.')
import aufrecht as A
from aufrecht import to_m, from_m, koerper, z_unten, schreibe

LOCH_D, LOCH_T = 2.0, 10.0         # Fadenloch: Durchmesser, Tiefe (Sackloch)
FUSS_R, FUSS_D = 17.0, 1.0         # Fuss
TIEF = 0.25                        # Spitze taucht so tief in den Fuss
SPALT = 0.35                       # senkrechter Luftspalt zwischen Rippe und Flaeche
RIPPE_D = 0.6                      # Rippendicke (ca. 1,5 Linien)
RIPPE_H = 12.0                     # max. Rippenhoehe ueber Fuss-Unterkante
RIPPE_R = {0: 14.0, 45: 14.0, 90: 17.0, 135: 14.0}

def baue():
    Q, h = koerper()
    tri = h.simplices.copy(); c = Q.mean(0)
    for i, f in enumerate(tri):
        a, b, d = Q[f]
        if np.dot(np.cross(b-a, d-a), a-c) < 0: tri[i] = f[[0, 2, 1]]
    body = to_m(Q, tri)
    zt, zb = Q[:, 2].max(), Q[:, 2].min()
    n = 48; a = np.linspace(0, 2*np.pi, n, endpoint=False)
    loch = m3.CrossSection([np.c_[LOCH_D/2*np.cos(a), LOCH_D/2*np.sin(a)]]).extrude(LOCH_T + 2).translate([0, 0, zt - LOCH_T])
    body = body - loch
    top = zb + TIEF
    fuss = m3.Manifold.cylinder(FUSS_D, FUSS_R, FUSS_R, 128).translate([0, 0, top - FUSS_D])
    zf = top - FUSS_D
    ribs = None
    for ph in (0, 45, 90, 135):
        ca, sa = np.cos(np.radians(ph)), np.sin(np.radians(ph))
        s = np.linspace(-RIPPE_R[ph], RIPPE_R[ph], 241)
        zl = z_unten(h, s*ca, s*sa)
        t = np.where(np.isnan(zl), zf + 2.0, np.minimum(zl - SPALT, zf + RIPPE_H))
        t = np.maximum(t, zf + 0.9)
        poly = np.vstack([[[s[0], zf+0.5], [s[-1], zf+0.5]], np.c_[s, t][::-1]])
        r = m3.CrossSection([poly]).extrude(RIPPE_D).rotate([90, 0, 0]).translate([0, RIPPE_D/2, 0]).rotate([0, 0, ph])
        ribs = r if ribs is None else ribs + r
    return body, fuss, ribs

if __name__ == '__main__':
    body, fuss, ribs = baue()
    # Pruefungen
    kontakt = (ribs ^ body).volume()
    print("Rippen/Koerper Ueberschneidung (mm3):", round(kontakt, 5), "(soll 0)")
    # kleinster Abstand Rippe-Koerper: Koerper um d aufblasen -> Beruehrung?
    for d in (0.05, 0.10, 0.15):
        Q, h = koerper()
        E2 = h.equations.copy(); E2[:, 3] -= d
        from scipy.spatial import HalfspaceIntersection, ConvexHull
        V = HalfspaceIntersection(E2, np.zeros(3)).intersections
        V = np.unique(np.round(V[np.isfinite(V).all(1)], 6), axis=0)
        hh = ConvexHull(V); tri = hh.simplices.copy(); c = V.mean(0)
        for i, f in enumerate(tri):
            a, b, e = V[f]
            if np.dot(np.cross(b-a, e-a), a-c) < 0: tri[i] = f[[0, 2, 1]]
        big = to_m(V, tri)
        print(f"  Koerper um {d} mm vergroessert, Ueberschneidung mit Rippen: {(ribs ^ big).volume():.4f} mm3")
    alles = body + fuss + ribs
    schreibe('Oloid_massiv_Fadenloch_Luftspaltfuss.stl', alles, 'oloid_massiv_luftspaltfuss')
    print("Teile (zusammenhaengend):", len(alles.decompose()), "-> Rippen haengen am Fuss, Koerper nur ueber die Spitze")

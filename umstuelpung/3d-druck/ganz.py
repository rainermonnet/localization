"""Ganzer Oloid (massiv) mit kleinem Fadenloch (Sackloch an der Spitze).
 (a) aufrecht: Spitze unten um CUT abgeflacht -> steht direkt auf dem Bett (keine Spitze unter der Duesenbreite);
     loses Stuetzgestell (Platte + Rippen) mit Luftspalt GAP rundherum, nirgends mit dem Koerper verbunden
 (b) liegend: Lage mit der kleinsten Ueberhangflaeche; Tree-Stuetzen im Slicer
R = 20 mm -> 60 mm lang."""
import numpy as np, sys, struct
import manifold3d as m3
from scipy.spatial import ConvexHull, HalfspaceIntersection
sys.path.insert(0, '.')
from oloid_stl import oloid_mesh, facets, rot_to_down, overhang

R = 20.0
LOCH_D, LOCH_T = 1.2, 8.0        # Fadenloch (Sackloch)
CUT = 2.0                        # Abflachung der unteren Spitze (aufrecht)
GAP = 0.25                       # Luftspalt Gestell <-> Koerper (senkrecht zur Flaeche)
PLATTE_R, PLATTE_D = 17.0, 1.0
RIPPE_D, RIPPE_H = 0.6, 14.0
RIPPE_R = {0: 14.0, 45: 14.0, 90: 17.0, 135: 14.0}

def to_m(P, tri): return m3.Manifold(m3.Mesh(P.astype(np.float32), tri.astype(np.uint32)))
def from_m(M):
    me = M.to_mesh(); return np.asarray(me.vert_properties)[:, :3].astype(float), np.asarray(me.tri_verts).astype(int)
def hull_m(P):
    h = ConvexHull(P); tri = h.simplices.copy(); c = P.mean(0)
    for i, f in enumerate(tri):
        a, b, d = P[f]
        if np.dot(np.cross(b-a, d-a), a-c) < 0: tri[i] = f[[0, 2, 1]]
    return to_m(P, tri)

def oloid_old():
    P, tri = oloid_mesh(1.0, 1440); return P*R, tri       # Original-Koordinaten (Spitze bei x=-30)

def oloid_up(grow=0.0):
    """aufrecht: x',y',z' = (y,z,-x); optional um grow mm nach aussen aufgeblasen"""
    P, tri = oloid_mesh(1.0, 1440)
    Q = np.c_[P[:, 1], P[:, 2], -P[:, 0]]*R
    if grow == 0: return hull_m(Q), Q
    E = ConvexHull(Q).equations.copy(); E[:, 3] -= grow
    V = HalfspaceIntersection(E, np.zeros(3)).intersections
    V = np.unique(np.round(V[np.isfinite(V).all(1)], 6), axis=0)
    return hull_m(V), Q

def box(x0, x1, y0, y1, z0, z1): return m3.Manifold.cube([x1-x0, y1-y0, z1-z0]).translate([x0, y0, z0])
def zyl(r, h, n=48):
    a = np.linspace(0, 2*np.pi, n, endpoint=False)
    return m3.CrossSection([np.c_[r*np.cos(a), r*np.sin(a)]]).extrude(h)

def aufrecht():
    body, Q = oloid_up(0.0)
    zt, zb = Q[:, 2].max(), Q[:, 2].min()
    loch = zyl(LOCH_D/2, LOCH_T+2).translate([0, 0, zt-LOCH_T])
    kopf = (body - loch) ^ box(-60, 60, -60, 60, zb+CUT, 80)            # unten abgeflacht
    kopf = kopf.translate([0, 0, -(zb+CUT)])                              # Standflaeche bei z=0
    grown, _ = oloid_up(GAP); grown = grown.translate([0, 0, -(zb+CUT)])
    gestell = zyl(PLATTE_R, PLATTE_D)
    for ph in (0, 45, 90, 135):
        s = RIPPE_R[ph]
        rip = box(-s, s, -RIPPE_D/2, RIPPE_D/2, 0, RIPPE_H).rotate([0, 0, ph])
        gestell = gestell + rip
    gestell = gestell - grown
    return kopf, gestell

def liegend():
    P, tri = oloid_mesh(1.0, 1440)
    nn, ar = facets(P, tri)
    cand = np.unique(np.round(nn, 2), axis=0)
    best = sorted((overhang(P, tri, rot_to_down(n)), tuple(n)) for n in cand)[0][1]
    Rm = rot_to_down(np.array(best))
    Pr = P*R
    body = hull_m(Pr)
    # Loch an der Spitze (x=-30), Richtung +x, im Originalsystem
    loch = zyl(LOCH_D/2, LOCH_T+2).rotate([0, 90, 0]).translate([-1.5*R-1, 0, 0])   # Zylinder entlang +x ab Spitze
    body = body - loch
    V, T = from_m(body); V = V @ Rm.T
    return V, T, Rm

def weld(V, T):
    """Eckpunkte auf 0,1 µm runden, gleiche zusammenfassen, entartete Dreiecke entfernen"""
    V = np.round(V, 4); u, inv = np.unique(V, axis=0, return_inverse=True)
    T = inv[T]; ok = (T[:, 0] != T[:, 1]) & (T[:, 1] != T[:, 2]) & (T[:, 0] != T[:, 2])
    return u, T[ok]

def schreibe(path, V, T, name, schiebe=True):
    V, T = weld(V, T)
    if schiebe:
        V = V - np.array([(V[:, 0].min()+V[:, 0].max())/2, (V[:, 1].min()+V[:, 1].max())/2, V[:, 2].min()])
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    vol = np.einsum('ij,ij->i', a, np.cross(b, c)).sum()/6
    if vol < 0: T = T[:, [0, 2, 1]]; a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]; vol = -vol
    nr = np.cross(b-a, c-a); ln = np.linalg.norm(nr, axis=1); ok = ln > 1e-12; nr[ok] /= ln[ok][:, None]
    with open(path, 'wb') as f:
        f.write(name.encode().ljust(80, b' ')); f.write(struct.pack('<I', len(T)))
        for i in range(len(T)): f.write(struct.pack('<12fH', *nr[i], *a[i], *b[i], *c[i], 0))
    ang = np.degrees(np.arcsin(np.clip(-nr[:, 2], 0, 1)))
    cz = V[T].mean(1)[:, 2]
    m = (nr[:, 2] < -0.01) & (cz > 0.3)
    print(f"{name}: Dreiecke {len(T)}, Mass {np.round(V.max(0)-V.min(0),1)}, Volumen {vol/1000:.2f} cm3, steilster Ueberhang (Flaeche gegen die Senkrechte) {ang[m].max() if m.any() else 0:.1f} Grad")
    return V, T

if __name__ == '__main__':
    kopf, gestell = aufrecht()
    print("Koerper/Gestell Ueberschneidung (mm3):", round((kopf ^ gestell).volume(), 5), "(soll 0)")
    bb = kopf.bounding_box(); print("Standflaeche unten: Koerper z von", round(bb[2], 2), " Hoehe", round(bb[5], 2))
    sl = kopf.slice(0.05); print("Standflaeche bei z=0.05: Flaeche %.1f mm2" % sl.area(), " Bounding", np.round(sl.bounds(), 2))
    alles = kopf + gestell
    V, T = from_m(alles); print("Teile (getrennt):", len(alles.decompose()))
    schreibe('Oloid_ganz_aufrecht_loses-Gestell.stl', V, T, 'oloid_ganz_aufrecht', schiebe=False)
    V2, T2, Rm = liegend()
    schreibe('Oloid_ganz_liegend_Tree-Stuetzen.stl', V2, T2, 'oloid_ganz_liegend')
    # Neigung der Lochachse im liegenden Modell (Richtung +x im Originalsystem)
    ax = Rm @ np.array([1, 0, 0]); print("Lochachse liegend: Neigung gegen die Senkrechte %.1f Grad (Lochachse %s)" % (np.degrees(np.arccos(abs(ax[2]))), np.round(ax, 2)))

"""Hohler Oloid in zwei Haelften (Aequatorschnitt) + einteilige Variante.
Koordinaten x',y',z' = (y,z,-x) des Oloid-Modells, Spitze oben (z'=+30), R = 20 mm.
Waende: W mm. Aufhaengung: Langloch an der oberen Spitze, Querstift (Streichholz/Stahldraht) innen."""
import numpy as np, struct, sys
import manifold3d as m3
from scipy.spatial import ConvexHull, HalfspaceIntersection
sys.path.insert(0, '.')
from oloid_stl import oloid_mesh

R = 20.0
W = 2.4                      # Wandstaerke (normal zur Flaeche)
SCHLITZ_B, SCHLITZ_L = 3.6, 6.0     # Langloch an der Spitze: Breite (y'), Laenge (x')
ZAPFEN_B, ZAPFEN_H = 1.0, 1.5       # Feder (Zapfenring): Breite, Hoehe
NUT_SPIEL = 0.15                    # Spiel je Seite in der Nut
FADENLOCH_D = 1.8                   # rundes Fadenloch (Variante: Faden vor dem Verkleben von innen)
KEY_L = 4.0                         # Passmarke (Luecke im Zapfenring) Breite

def to_m(P, tri): return m3.Manifold(m3.Mesh(P.astype(np.float32), tri.astype(np.uint32)))
def from_m(M):
    me = M.to_mesh(); return np.asarray(me.vert_properties)[:, :3].astype(float), np.asarray(me.tri_verts).astype(int)

def hull_mesh(P):
    h = ConvexHull(P); tri = h.simplices.copy(); c = P.mean(0)
    for i, f in enumerate(tri):
        a, b, d = P[f]
        if np.dot(np.cross(b-a, d-a), a-c) < 0: tri[i] = f[[0, 2, 1]]
    return to_m(P, tri)

_Q = None; _E = None
def basis():
    global _Q, _E
    if _Q is None:
        P, tri = oloid_mesh(1.0, 1440)
        _Q = np.c_[P[:, 1], P[:, 2], -P[:, 0]] * R
        _E = ConvexHull(_Q).equations
    return _Q, _E

def koerper(t=0.0):
    """Oloid, um t mm nach innen versetzt (t>=0)"""
    Q, E = basis()
    if t == 0: return hull_mesh(Q)
    E2 = E.copy(); E2[:, 3] += t
    V = HalfspaceIntersection(E2, np.zeros(3)).intersections
    V = np.unique(np.round(V[np.isfinite(V).all(1)], 6), axis=0)
    return hull_mesh(V)

def box(x0, x1, y0, y1, z0, z1):
    return m3.Manifold.cube([x1-x0, y1-y0, z1-z0]).translate([x0, y0, z0])

def stadium(b, l, n=48):
    r = b/2; a = np.linspace(-np.pi/2, np.pi/2, n)
    right = np.c_[l/2 - r + r*np.cos(a), r*np.sin(a)]; left = right[::-1]*[-1, -1]
    return m3.CrossSection([np.vstack([right, left])])

def baue(rund=False):
    out = {}
    body = koerper(0)
    cav = koerper(W)
    hohl = body - cav
    # Langloch (senkrecht, durch die obere Spitze)
    ctop = np.array(cav.bounding_box()[3:6])[2]
    if rund:
        a = np.linspace(0, 2*np.pi, 48, endpoint=False)
        slot = m3.CrossSection([np.c_[FADENLOCH_D/2*np.cos(a), FADENLOCH_D/2*np.sin(a)]]).extrude(40).translate([0, 0, ctop - 3.0])
    else:
        slot = stadium(SCHLITZ_B, SCHLITZ_L).extrude(40).translate([0, 0, ctop - 3.0])
    einteilig = hohl - slot
    out['einteilig'] = einteilig
    # ---- Haelften
    big = 80
    upper = einteilig ^ box(-big, big, -big, big, 0, big)
    lower = einteilig ^ box(-big, big, -big, big, -big, 0)
    ring = lambda a, b: koerper(a) - koerper(b)        # Ring zwischen Versatz a und b (nach innen)
    slab = box(-big, big, -big, big, -ZAPFEN_H, 0)
    wa, wb = (W - ZAPFEN_B)/2, (W + ZAPFEN_B)/2
    zapfen = ring(wa, wb) ^ slab
    luecke = box(10, 30, -KEY_L/2, KEY_L/2, -5, 5)                # Passmarke bei +x'
    zapfen = zapfen - luecke
    nut = ring(wa - NUT_SPIEL, wb + NUT_SPIEL) ^ box(-big, big, -big, big, -ZAPFEN_H - 0.3, 0)
    block = box(10, 30, -(KEY_L/2 - 0.2), (KEY_L/2 - 0.2), -5, 5)  # bleibt in der Nut stehen
    nut = nut - block
    upper = upper + zapfen
    lower = lower - nut
    out['oben'] = upper; out['unten'] = lower
    return out, cav

def schreibe(path, M, name, trafo=None):
    V, T = from_m(M)
    if trafo is not None: V = trafo(V)
    V = V - np.array([(V[:, 0].min()+V[:, 0].max())/2, (V[:, 1].min()+V[:, 1].max())/2, V[:, 2].min()])
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    nr = np.cross(b-a, c-a); ln = np.linalg.norm(nr, axis=1); ok = ln > 1e-12; nr[ok] /= ln[ok][:, None]
    # nach Spiegelung/Drehung muss die Orientierung stimmen
    vol = np.einsum('ij,ij->i', a, np.cross(b, c)).sum()/6
    if vol < 0:
        T = T[:, [0, 2, 1]]; a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]; nr = -nr; vol = -vol
    with open(path, 'wb') as f:
        f.write(name.encode().ljust(80, b' ')); f.write(struct.pack('<I', len(T)))
        for i in range(len(T)): f.write(struct.pack('<12fH', *nr[i], *a[i], *b[i], *c[i], 0))
    # Ueberhang gegen Bett (ohne Bettflaeche)
    cz = (V[T].mean(1))[:, 2]; nz = nr[:, 2]
    ang = np.degrees(np.arccos(np.clip(-nz, -1, 1)))      # 0 = Flaeche zeigt nach unten (waagrecht)
    m = (nz < 0) & (cz > 0.05)
    ueb = 90 - ang[m].min() if m.any() else 0              # groesster Ueberhangwinkel von der Senkrechten
    gewicht = vol/1000*1.24*0.5                              # g bei ~50 % effektiver Dichte? nein: Volumen*1.24 g/cm3
    print(f"{name}: Dreiecke {len(T)}, Mass {np.round(V.max(0)-V.min(0),1)}, Volumen {vol/1000:.2f} cm3 (~{vol/1000*1.24:.1f} g PLA massiv), "
          f"max Ueberhang von der Senkrechten {ueb:.1f} Grad, status {M.status()}, Teile {len(M.decompose())}")
    return V, T

if __name__ == '__main__':
    teile, cav = baue(False)
    bb = np.array(cav.bounding_box())
    print("Hohlraum innen: Mass", np.round(bb[3:]-bb[:3], 1))
    schreibe('Oloid_hohl_einteilig_Langloch.stl', teile['einteilig'], 'oloid_hohl_einteilig')
    schreibe('Oloid_hohl_Oberhaelfte_Langloch.stl', teile['oben'], 'oloid_oberhaelfte_langloch')
    schreibe('Oloid_hohl_Unterhaelfte.stl', teile['unten'], 'oloid_unterhaelfte', trafo=lambda V: np.c_[V[:, 1], V[:, 0], -V[:, 2]])
    t2, _ = baue(True)
    schreibe('Oloid_hohl_Oberhaelfte_Fadenloch.stl', t2['oben'], 'oloid_oberhaelfte_fadenloch')

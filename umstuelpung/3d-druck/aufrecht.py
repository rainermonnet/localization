"""Oloid aufrecht (Spitze oben) mit Oese und Stabilisatoren (Fuss + Rippen)
Koordinaten: x', y', z' = (y, z, -x) des Oloid-Modells; r = Kreisradius in mm."""
import numpy as np, struct, sys
import manifold3d as m3
from scipy.spatial import ConvexHull
sys.path.insert(0, '.')
from oloid_stl import oloid_mesh

R = 20.0                 # Kreisradius -> Laenge 3R = 60 mm
# Oese
OE_DICKE = 2.4           # Dicke in y'
OE_AUSSEN = 4.6          # Aussenradius
OE_LOCH = 1.5            # Lochradius (3 mm Loch, Tropfenform, Spitze oben)
OE_HOEHE = 4.2           # Lochmitte ueber der Spitze
OE_EINTIEFE = 4.0        # Wurzel der Oese reicht so tief in den Koerper
# Stabilisatoren
FUSS_R, FUSS_D = 20.0, 1.0      # runder Fuss
UEBERLAPP_FUSS = 0.4            # Spitze taucht so tief in den Fuss
RIPPE_D = 0.8                   # Rippendicke
RIPPE_R = {0: 15.0, 45: 15.0, 90: 19.0, 135: 15.0}   # Reichweite je Rippenebene (Grad -> mm)
RIPPE_H = 15.0                  # max. Hoehe ueber Fuss-Unterkante
RIPPEN_WINKEL = [0, 45, 90, 135]
RIPPE_UEBERLAPP = 0.5           # Rippen ragen so weit (senkrecht) in den Koerper

def to_m(P, tri):
    return m3.Manifold(m3.Mesh(P.astype(np.float32), tri.astype(np.uint32)))
def from_m(M):
    me = M.to_mesh(); return np.asarray(me.vert_properties)[:, :3].astype(float), np.asarray(me.tri_verts).astype(int)

def koerper():
    P, tri = oloid_mesh(1.0, 1440)
    Q = np.c_[P[:, 1], P[:, 2], -P[:, 0]] * R
    h = ConvexHull(Q)
    return Q, h

def z_unten(h, x, y):
    """untere Oberflaeche des (konvexen) Koerpers ueber (x,y); NaN ausserhalb"""
    E = h.equations; nx, ny, nz, off = E.T
    out = np.full(len(x), np.nan)
    dn = nz < -1e-9; up = nz > 1e-9; mid = ~(dn | up)
    for i, (xx, yy) in enumerate(zip(x, y)):
        if np.any(nx[mid]*xx + ny[mid]*yy + off[mid] > 1e-9): continue
        lo = np.max((-off[dn] - nx[dn]*xx - ny[dn]*yy)/nz[dn])
        hi = np.min((-off[up] - nx[up]*xx - ny[up]*yy)/nz[up])
        if lo <= hi: out[i] = lo
    return out

def baue(mit_stab=True):
    Q, h = koerper()
    tri = h.simplices.copy(); c = Q.mean(0)
    for i, f in enumerate(tri):
        a, b, d = Q[f]
        if np.dot(np.cross(b-a, d-a), a-c) < 0: tri[i] = f[[0, 2, 1]]
    body = to_m(Q, tri)
    zt = Q[:, 2].max(); zb = Q[:, 2].min()          # +30 / -30
    # ---- Oese
    n = 96
    kreis = lambda r, cx, cy: np.c_[cx + r*np.cos(np.linspace(0, 2*np.pi, n, endpoint=False)), cy + r*np.sin(np.linspace(0, 2*np.pi, n, endpoint=False))]
    zc = zt + OE_HOEHE
    aussen = m3.CrossSection([kreis(OE_AUSSEN, 0, zc)])
    stiel = m3.CrossSection([np.array([[-OE_AUSSEN, zt-OE_EINTIEFE], [OE_AUSSEN, zt-OE_EINTIEFE], [OE_AUSSEN, zc], [-OE_AUSSEN, zc]])])
    loch_pts = kreis(OE_LOCH, 0, zc)
    tip = np.array([[0, zc + OE_LOCH*np.sqrt(2)]])
    # Tropfen: Winkel von -225..45 (Kreis), Spitze bei 90 -> Reihenfolge nach Winkel
    teil = np.vstack([loch_pts, tip])
    a2 = np.degrees(np.arctan2(teil[:, 1]-zc, teil[:, 0]))
    keep = ~((a2 > 45) & (a2 < 135) & (np.arange(len(teil)) < n))
    teil = teil[keep]; a2 = a2[keep]
    a2 = np.where(a2 < -90, a2 + 360, a2)
    teil = teil[np.argsort(a2)]
    loch = m3.CrossSection([teil])
    prisma = lambda cs: cs.extrude(OE_DICKE).rotate([90, 0, 0]).translate([0, OE_DICKE/2, 0])
    oese = prisma(aussen) + prisma(stiel)
    oese = oese - prisma(loch).scale([1, 2.0, 1])
    teile = body + oese
    if not mit_stab: return teile
    # ---- Fuss + Rippen
    fuss_oben = zb + UEBERLAPP_FUSS
    fuss = m3.Manifold.cylinder(FUSS_D, FUSS_R, FUSS_R, 128).translate([0, 0, fuss_oben - FUSS_D])
    teile = teile + fuss
    zf = fuss_oben - FUSS_D                              # Unterkante Fuss
    for ph in RIPPEN_WINKEL:
        s = np.linspace(-RIPPE_R[ph], RIPPE_R[ph], 241)
        ca, sa = np.cos(np.radians(ph)), np.sin(np.radians(ph))
        zl = z_unten(h, s*ca, s*sa)
        top = np.where(np.isnan(zl), zf + 2.0, np.minimum(zl + RIPPE_UEBERLAPP, zf + RIPPE_H))
        top = np.maximum(top, zf + 0.9)
        poly = np.vstack([[[s[0], zf+0.5], [s[-1], zf+0.5]], np.c_[s, top][::-1]])  # gegen den Uhrzeigersinn
        cs = m3.CrossSection([poly])
        rip = cs.extrude(RIPPE_D).rotate([90, 0, 0]).translate([0, RIPPE_D/2, 0]).rotate([0, 0, ph])
        teile = teile + rip
    return teile

def schreibe(path, M, name):
    V, T = from_m(M)
    V = V - np.array([(V[:, 0].min()+V[:, 0].max())/2, (V[:, 1].min()+V[:, 1].max())/2, V[:, 2].min()])
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    nr = np.cross(b-a, c-a); ln = np.linalg.norm(nr, axis=1); ok = ln > 1e-12
    nr[ok] /= ln[ok][:, None]
    with open(path, 'wb') as f:
        f.write(name.encode().ljust(80, b' ')); f.write(struct.pack('<I', len(T)))
        for i in range(len(T)): f.write(struct.pack('<12fH', *nr[i], *a[i], *b[i], *c[i], 0))
    vol = np.einsum('ij,ij->i', a, np.cross(b, c)).sum()/6
    print(name, "Dreiecke", len(T), "Ausdehnung", np.round(V.max(0)-V.min(0), 2), "Volumen %.2f cm3" % (vol/1000), "manifold:", M.status(), "Teile:", M.num_vert() and len(M.decompose()))
    return V, T

if __name__ == '__main__':
    schreibe('Oloid_aufrecht_Oese_Stabilisatoren.stl', baue(True), 'Oloid_aufrecht_Oese_Stabilisatoren')
    schreibe('Oloid_aufrecht_Oese_ohne-Stabilisatoren.stl', baue(False), 'Oloid_aufrecht_Oese')

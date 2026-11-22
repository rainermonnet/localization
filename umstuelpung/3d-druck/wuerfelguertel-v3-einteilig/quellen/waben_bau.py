"""Wuerfelguertel v2: Bienenwaben-Struktur, Drucklage auf F3, Export der STL-Dateien fuer den Bambu Lab A1."""
import numpy as np, manifold3d as m3, struct, os, sys
import guertel as G, scharnier as S

WABE = 5.2        # Mittenabstand der Waben (quer)
STEG = 0.8        # Stegbreite zwischen den Waben
TIEFE = 0.7       # Wabentiefe
RAND = 1.3        # Abstand zu den Kanten der Flaeche
TIEFE_BETT = 0.6  # Waben auf der Bettseite: 3 Schichten tief, werden ueberbrueckt
RAND_BETT = 3.0   # breiter glatter Rand auf dem Bett fuer die Haftung
FLEISCH = 1.0     # Restwand hinter jeder Wabe

def ebenen(V):
    cen = V.mean(0); out = []
    for f in G.FACES:
        a, b, c = V[list(f)]; n = np.cross(b - a, c - a); n /= np.linalg.norm(n)
        if n @ (a - cen) < 0: n = -n
        out.append((n, n @ a))
    return out

def innen(p, pl, m):
    return all(n @ p <= d - m for n, d in pl)

_cache = {}
def schnitt(taschen):
    key = tuple(id(r) for r in taschen)
    if key not in _cache:
        C = None
        for r in taschen:
            c = r.box(S.U0 - S.TASCHE - 0.8, S.U1 + S.TASCHE + 0.8, -1.0, S.D + S.TASCHE + 0.8, -S.R - 0.9, 2.0) + r.zyl(S.U0 - S.SPIEL - 1.3, S.U1 + S.SPIEL + 1.3, S.FREI + 0.8)
            C = c if C is None else C + c
        _cache[key] = C
    return _cache[key]

def waben_flaeche(V, fi, up, taschen, tiefe=None, rand=None):
    """Wabenmuster auf Flaeche fi, am Rand abgeschnitten (wie eine echte Wabe). Gibt Liste von Manifolds zurueck."""
    from shapely.geometry import Polygon, box as sbox
    from shapely import affinity
    tiefe = TIEFE if tiefe is None else tiefe; rand = RAND if rand is None else rand
    pl = ebenen(V); n, d = pl[fi]; f = list(G.FACES[fi])
    eu = up - (up @ n)*n
    if np.linalg.norm(eu) < 1e-6: eu = V[f[1]] - V[f[0]]
    eu /= np.linalg.norm(eu); es = np.cross(n, eu); o = V[f].mean(0)
    to2 = lambda p: ((p - o) @ es, (p - o) @ eu)
    # erlaubtes Gebiet: Dreieck, je Kante um max(Rand, Restwand-Bedingung) eingerueckt
    big = 200.0; reg = sbox(-big, -big, big, big)
    for j in range(4):
        if j == fi: continue
        nn, dd = pl[j]
        a2 = np.array([nn @ es, nn @ eu]); off = dd - nn @ o           # nn.x <= dd  ->  a2.(x2) <= off
        lim = min(off - rand*np.linalg.norm(a2), off + (tiefe + FLEISCH)*(nn @ n))
        # Halbebene a2.x <= lim als grosses Polygon
        t = a2/np.linalg.norm(a2); q = np.array([-t[1], t[0]]); p0 = t*lim/np.linalg.norm(a2)
        reg = reg.intersection(Polygon([p0 + q*big, p0 - q*big, p0 - q*big - t*big, p0 + q*big - t*big]))
    if reg.is_empty: return []
    rc = WABE/np.sqrt(3); rd = (WABE/2 - STEG/2)*2/np.sqrt(3)
    ang = np.radians(90 + 60*np.arange(6)); hexd = np.c_[np.cos(ang), np.sin(ang)]*rd
    voll = Polygon(hexd).area; out = []
    for j in range(-40, 41):
        for i in range(-25, 26):
            cx = i*WABE + (WABE/2 if j % 2 else 0); cy = j*1.5*rc
            h = Polygon(hexd + [cx, cy]).intersection(reg)
            if h.is_empty or h.area < 0.35*voll or h.geom_type != "Polygon": continue
            h = h.buffer(-0.05).buffer(0.05)
            if h.is_empty or h.geom_type != "Polygon": continue
            pts = np.array(h.exterior.coords)[:-1]
            P = [o + x*es + y*eu for x, y in pts]
            out.append(m3.Manifold.hull_points(np.array([p + n*1.0 for p in P] + [p - n*tiefe for p in P])))
    if not out: return []
    W = m3.Manifold.compose(out) - schnitt(taschen)
    return [W]

def glied_fertig(k, lok):
    P, rA, rB = S.rahmen_glied(k, lok)
    _, V = S.tetra_inset(P)
    body = S.glied(k, lok)
    pl = ebenen(V); up = -pl[2][0]               # Druckflaeche F3 (Index 2) liegt unten
    taschen = [rA, rB]
    W = []
    # Waben nur AUSSEN (in der Wuerfellage liegen F1 und F3 auf der Wuerfeloberflaeche; F2/F4 innen mit den Taschen)
    W += waben_flaeche(V, 0, up, taschen)                                   # F1, senkrecht im Druck
    W += waben_flaeche(V, 2, up, taschen, tiefe=TIEFE_BETT, rand=RAND_BETT)  # F3 = Bettflaeche

    if W: body = body - m3.Manifold.compose(W)
    return body, V, up, sum(len(w.decompose()) for w in W)

def rot_to(n, target=np.array([0, 0, -1.0])):
    n = n/np.linalg.norm(n); v = np.cross(n, target); s = np.linalg.norm(v); c = np.dot(n, target)
    if s < 1e-12: return np.eye(3) if c > 0 else np.diag([1, -1, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); return np.eye(3) + vx + vx @ vx*((1 - c)/s**2)

def drucklage(body, V, up):
    """F3 nach unten aufs Bett, laengste Bodenkante entlang x"""
    Rm = rot_to(-up)
    f = list(G.FACES[2]); B = V[f] @ Rm.T
    # Kante c_k -> c_k+1 (Indizes 0,2) entlang x
    e = B[1] - B[0]; a = -np.arctan2(e[1], e[0]); Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    R2 = Rz @ Rm; M = np.zeros((3, 4)); M[:, :3] = R2
    out = body.transform(M); bb = out.bounding_box()
    return out.translate([-bb[0], -bb[1], -bb[2]])

def schreibe(fn, M, name="wuerfelguertel"):
    me = M.to_mesh(); V = np.asarray(me.vert_properties)[:, :3].astype(np.float32); T = np.asarray(me.tri_verts)
    tri = V[T]; n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); ln = np.linalg.norm(n, axis=1); ln[ln == 0] = 1; n = (n/ln[:, None]).astype(np.float32)
    with open(fn, 'wb') as fh:
        fh.write(name.encode()[:80].ljust(80, b' ')); fh.write(struct.pack('<I', len(T)))
        rec = np.zeros(len(T), dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))
        rec['n'] = n; rec['v'] = tri.reshape(-1, 9); fh.write(rec.tobytes())
    return len(T)

if __name__ == "__main__":
    lok = G.glieder_lokal(0.5)
    os.makedirs("guertel2", exist_ok=True)
    teile = []
    for k in range(6):
        body, V, up, nw = glied_fertig(k, lok)
        D = drucklage(body, V, up); bb = D.bounding_box()
        print(f"Glied {k}: Waben {nw}, Volumen {D.volume()/1000:.2f} cm3, Teile {len(D.decompose())}, Masse {bb[3]-bb[0]:.1f} x {bb[4]-bb[1]:.1f} x {bb[5]-bb[2]:.1f} mm")
        teile.append(D)
    H = S.scharnier_druck()
    print("Scharnier", H.volume()/1000, H.bounding_box(), "Teile", len(H.decompose()))
    import pickle
    pickle.dump([ (np.asarray(t.to_mesh().vert_properties)[:, :3], np.asarray(t.to_mesh().tri_verts)) for t in teile + [H]], open("guertel2/teile.pkl", "wb"))

"""Wuerfelguertel v2: Bienenwaben-Struktur, Drucklage auf F3, Export der STL-Dateien fuer den Bambu Lab A1."""
import numpy as np, manifold3d as m3, struct, os, sys
import guertel as G, scharnier as S

WABE = 5.2        # Mittenabstand der Waben (quer)
STEG = 0.8        # Stegbreite zwischen den Waben
TIEFE = 0.7       # Wabentiefe
RAND = 1.3        # Abstand zu den Kanten der Flaeche
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

def waben_flaeche(V, fi, up, taschen):
    """Waben auf Flaeche fi des Tetraeders mit Ecken V (bereits eingerueckt). taschen: Liste (Rahmen) zum Aussparen"""
    pl = ebenen(V); n, d = pl[fi]; f = list(G.FACES[fi])
    eu = up - (up @ n)*n
    if np.linalg.norm(eu) < 1e-6: eu = V[f[1]] - V[f[0]]
    eu /= np.linalg.norm(eu); es = np.cross(n, eu)
    o = V[f].mean(0)
    rc = WABE/np.sqrt(3)                        # Umkreisradius der Zelle (Spitze nach oben)
    rd = (WABE/2 - STEG/2)*2/np.sqrt(3)          # Umkreisradius der Vertiefung
    ang = np.radians(90 + 60*np.arange(6))        # Spitze zeigt nach eu
    hexd = np.c_[np.cos(ang), np.sin(ang)]*rd
    others = [pl[j] for j in range(4) if j != fi]
    out = []
    span = 90
    for j in range(-int(span/(1.5*rc)), int(span/(1.5*rc)) + 1):
        for i in range(-int(span/WABE), int(span/WABE) + 1):
            cx = i*WABE + (WABE/2 if j % 2 else 0); cy = j*1.5*rc
            pts2 = hexd + [cx, cy]
            P = [o + x*es + y*eu for x, y in pts2]
            # in der Flaeche mit Rand (gegen die anderen drei Ebenen)
            if not all(all(nn @ p <= dd - RAND for nn, dd in others) for p in P): continue
            # Restwand: Boden der Wabe + FLEISCH muss innen liegen
            if not all(innen(p - n*(TIEFE + FLEISCH), pl, 0) for p in P): continue
            # Taschen der Scharnierlaschen + Freistich aussparen
            bad = False
            for r in taschen:
                for p in P:
                    q = p - r.c; u, y = q @ r.ex, q @ r.ey
                    if S.U0 - 1.6 <= u <= S.U1 + 1.6 and y <= S.D + 1.6: bad = True; break
                    if np.hypot(y, q @ r.ez) <= S.FREI + 1.2 and -1 <= u <= 36: bad = True; break
                if bad: break
            if bad: continue
            prism = [p + n*1.0 for p in P] + [p - n*TIEFE for p in P]
            out.append(m3.Manifold.hull_points(np.array(prism)))
    return out

def glied_fertig(k, lok):
    P, rA, rB = S.rahmen_glied(k, lok)
    _, V = S.tetra_inset(P)
    body = S.glied(k, lok)
    pl = ebenen(V); up = -pl[2][0]               # Druckflaeche F3 (Index 2) liegt unten
    taschen = [rA, rB]
    W = []
    for fi in (0, 1, 3):                          # F1, F2, F4
        W += waben_flaeche(V, fi, up, taschen)
    if W: body = body - m3.Manifold.compose(W)
    return body, V, up, len(W)

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

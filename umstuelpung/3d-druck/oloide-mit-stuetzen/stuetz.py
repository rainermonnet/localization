"""Oloide fuer alle Winkel phi, aufrecht (Spitze oben), mit Stuetzen nach der Vorlage OLOID_Rainer_2:
 Scheibe (Dm = 2 (r+2,4), 0,8 mm dick), Koerper schwebt 0,8 mm darueber (Spitze bei z = 1,6),
 zwei gekreuzte Stuetzwaende (1,6 mm dick) in den beiden Kreisebenen, die zur Koerperflaeche hin spitz zulaufen
 (Halbdicke = min(0,8; Abstand zur Flaeche)). Fadenloch Dm 0,5 mm an der oberen Spitze."""
import json, struct, sys, numpy as np
import manifold3d as m3
from scipy.spatial import ConvexHull, HalfspaceIntersection
D = json.load(open("bahnen_daten.json"))
c0 = np.zeros(3); c1 = np.array([1.0, 0, 0])
SCHEIBE_D, ZB = 0.8, 1.6          # Scheibendicke, Hoehe der unteren Koerperspitze
WAND_T, RAND = 1.6, 2.4           # Wanddicke, Rand ueber den Koerper hinaus
LOCH_D, LOCH_T = 0.5, 8.0
SCHRITT = 0.05

def fit_normale(arc, c):
    P = np.array(arc) - c; return np.linalg.svd(P)[2][2]
def vollkreis(n, c, k=1440):
    t = np.linspace(0, 2*np.pi, k, endpoint=False); a = np.cross(n, [1, 0, 0])
    if np.linalg.norm(a) < 1e-6: a = np.cross(n, [0, 1, 0])
    a /= np.linalg.norm(a); b = np.cross(n, a); return c + np.outer(np.cos(t), a) + np.outer(np.sin(t), b)
def to_m(P, tri): return m3.Manifold(m3.Mesh(P.astype(np.float32), tri.astype(np.uint32)))
def from_m(M):
    me = M.to_mesh(); return np.asarray(me.vert_properties)[:, :3].astype(float), np.asarray(me.tri_verts).astype(int)
def hull_m(P):
    h = ConvexHull(P); tri = h.simplices.copy(); c = P.mean(0)
    for i, f in enumerate(tri):
        a, b, d = P[f]
        if np.dot(np.cross(b-a, d-a), a-c) < 0: tri[i] = f[[0, 2, 1]]
    return to_m(P, tri), h
def box(x0, x1, y0, y1, z0, z1): return m3.Manifold.cube([x1-x0, y1-y0, z1-z0]).translate([x0, y0, z0])
def zyl(r, h, n=96):
    a = np.linspace(0, 2*np.pi, n, endpoint=False); return m3.CrossSection([np.c_[r*np.cos(a), r*np.sin(a)]]).extrude(h)

def zlow(E, X, Y):
    """untere Flaeche des konvexen Polyeders {n.p + off <= 0} ueber (X,Y); +inf ausserhalb des Grundrisses"""
    nx, ny, nz, off = E.T; out = np.full(len(X), np.inf)
    mid = np.abs(nz) < 1e-9; dn = nz < -1e-9; up = nz > 1e-9
    ok = np.ones(len(X), bool)
    if mid.any(): ok &= ((np.outer(X, nx[mid]) + np.outer(Y, ny[mid]) + off[mid]) <= 1e-9).all(1)
    lo = np.full(len(X), -np.inf); hi = np.full(len(X), np.inf)
    for k in range(0, len(X), 400):
        sl = slice(k, k + 400)
        lo[sl] = ((-off[dn] - np.outer(X[sl], nx[dn]) - np.outer(Y[sl], ny[dn]))/nz[dn]).max(1)
        hi[sl] = ((-off[up] - np.outer(X[sl], nx[up]) - np.outer(Y[sl], ny[up]))/nz[up]).min(1)
    f = ok & (lo <= hi); out[f] = lo[f]; return out

def wand(E, nrm, cap, L, ns=None, nt=17):
    ns = ns or int(2*L/0.3) + 1
    """Stuetzwand als Hoehenfeld: Halbdicke = min(0,8; Abstand zur Koerperflaeche), Dach folgt der Flaeche"""
    u = np.array([-nrm[1], nrm[0]]); s = np.linspace(-L, L, ns); t = np.linspace(-WAND_T/2, WAND_T/2, nt)
    Z = np.zeros((ns, nt))
    for j, tj in enumerate(t):
        X = s*u[0] + tj*nrm[0]; Y = s*u[1] + tj*nrm[1]
        E2 = E.copy(); E2[:, 3] -= abs(tj)
        Z[:, j] = np.minimum(cap, zlow(E2, X, Y))
    Z = np.maximum(Z, SCHEIBE_D + 0.05)
    SS, TT = np.meshgrid(s, t, indexing='ij'); Xg = SS*u[0] + TT*nrm[0]; Yg = SS*u[1] + TT*nrm[1]
    top = np.stack([Xg, Yg, Z], -1).reshape(-1, 3); bot = np.stack([Xg, Yg, np.full_like(Z, SCHEIBE_D)], -1).reshape(-1, 3)
    V = np.vstack([top, bot]); N = ns*nt; idx = lambda i, j: i*nt + j; T = []
    for i in range(ns - 1):
        for j in range(nt - 1):
            a_, b_, c_, d_ = idx(i, j), idx(i+1, j), idx(i+1, j+1), idx(i, j+1)
            T += [[a_, b_, c_], [a_, c_, d_]]                            # oben
            T += [[N+a_, N+c_, N+b_], [N+a_, N+d_, N+c_]]                # unten (umgedreht)
    for i in range(ns - 1):                                              # Seiten t = const
        for j, rev in ((0, False), (nt - 1, True)):
            a_, b_ = idx(i, j), idx(i+1, j)
            q = [[a_, N+a_, N+b_], [a_, N+b_, b_]]
            T += [[x[0], x[2], x[1]] for x in q] if rev else q
    for j in range(nt - 1):                                              # Stirnseiten s = const
        for i, rev in ((0, True), (ns - 1, False)):
            a_, b_ = idx(i, j), idx(i, j+1)
            q = [[a_, N+a_, N+b_], [a_, N+b_, b_]]
            T += [[x[0], x[2], x[1]] for x in q] if rev else q
    T = np.array(T)
    # Orientierung global pruefen
    A, B, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    vol = np.einsum('ij,ij->i', A, np.cross(B, C)).sum()/6
    if vol < 0: T = T[:, [0, 2, 1]]
    return to_m(V, T)

def baue(idx, r):
    d = D[idx]; n5 = fit_normale(d["c"][3], c0); n2 = fit_normale(d["c"][0], c1)
    P = np.vstack([vollkreis(n5, c0), vollkreis(n2, c1)])
    Q = np.c_[P[:, 1], P[:, 2], -(P[:, 0] - 0.5)]*r; Q[:, 2] += 1.5*r + ZB
    body, h = hull_m(Q); zt = Q[:, 2].max()
    loch = zyl(LOCH_D/2, LOCH_T + 2, 32).translate([0, 0, zt - LOCH_T])
    body_l = body - loch
    nc5 = np.array([0.0, 1.0]); nc2 = np.array([n2[1], n2[2]])/np.linalg.norm(n2[1:])
    L = r + RAND; scheibe = zyl(L, SCHEIBE_D)
    w5 = wand(h.equations, nc5, ZB + 2*r, L); w2 = wand(h.equations, nc2, ZB + r, L)
    return body_l, scheibe, [w5, w2], Q, zt

def schreibe(path, shells, name, versatz=(128.0, 128.0)):
    Vs = []; Ts = []; off = 0
    for M in shells:
        V, T = from_m(M); Vs.append(V); Ts.append(T + off); off += len(V)
    V = np.vstack(Vs); T = np.vstack(Ts)
    V = np.round(V, 4); u, inv = np.unique(V, axis=0, return_inverse=True); T = inv[T]
    ok = (T[:, 0] != T[:, 1]) & (T[:, 1] != T[:, 2]) & (T[:, 0] != T[:, 2]); T = T[ok]
    V = u + np.array([versatz[0], versatz[1], 0.0])
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    nr = np.cross(b-a, c-a); ln = np.linalg.norm(nr, axis=1); k = ln > 1e-12; nr[k] /= ln[k][:, None]
    with open(path, 'wb') as f:
        f.write(name.encode().ljust(80, b' ')); f.write(struct.pack('<I', len(T)))
        for i in range(len(T)): f.write(struct.pack('<12fH', *nr[i], *a[i], *b[i], *c[i], 0))
    return len(T)

"""Wuerfelguertel (Schatz): Ring aus sechs Tetraedern, Gelenkachsen = Wuerfelkanten an den Enden einer Raumdiagonale."""
import numpy as np, ring
PHI = np.pi/2
X0 = ring.startpunkt(PHI)
def rahmen(t0, t1): return ring.kette(t0, t1, PHI)[:6]
def wuerfel_lage():
    F = rahmen(*X0); c = np.array([m[:3, 3] for m in F]); z = np.array([m[:3, 2] for m in F])
    def schnitt(ids):
        A = np.vstack([np.eye(3) - np.outer(z[i], z[i]) for i in ids]); b = np.concatenate([(np.eye(3) - np.outer(z[i], z[i])) @ c[i] for i in ids])
        return np.linalg.lstsq(A, b, rcond=None)[0]
    return F, c, schnitt([0, 2, 4]), schnitt([1, 3, 5])
def glieder_lokal(f=0.5):
    """Tetraeder k mit Ecken c_k, H_k, c_k+1, H_k+1 in Koordinaten des Rahmens k"""
    F, c, A, B = wuerfel_lage(); out = []
    H = [c[k] + f*((A if k % 2 == 0 else B) - c[k]) for k in range(6)]
    for k in range(6):
        k1 = (k + 1) % 6; W = np.array([c[k], H[k], c[k1], H[k1]]); Minv = np.linalg.inv(F[k1])   # Glied k haengt starr am Rahmen k+1
        out.append((Minv @ np.c_[W, np.ones(4)].T).T[:, :3])
    return out
def welt(lok, t0, t1):
    F = rahmen(t0, t1); return [(F[(k + 1) % 6] @ np.c_[lok[k], np.ones(len(lok[k]))].T).T[:, :3] for k in range(6)]
FACES = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]
EDGES = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
def getrennt(P, Q, eps=1e-7):
    ax = []
    for T in (P, Q):
        for f in FACES: ax.append(np.cross(T[f[1]] - T[f[0]], T[f[2]] - T[f[0]]))
    for e in EDGES:
        for g in EDGES: ax.append(np.cross(P[e[1]] - P[e[0]], Q[g[1]] - Q[g[0]]))
    for a in ax:
        n = np.linalg.norm(a)
        if n < 1e-12: continue
        a = a/n; p = P @ a; q = Q @ a
        if p.max() < q.min() + eps or q.max() < p.min() + eps: return True
    return False
def schrumpf(T, s=0.97): c = T.mean(0); return c + s*(T - c)

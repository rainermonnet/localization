"""Drucklage der einteiligen Kette: alle 6 Glieder flach auf dem Bett, Gelenke 1,3,5 flach, 2,4 senkrecht."""
import numpy as np, manifold3d as m3, itertools
from shapely.geometry import MultiPoint
import guertel as G, einteilig as E

def Rz(t): c, s = np.cos(t), np.sin(t); M = np.eye(4); M[:2, :2] = [[c, -s], [s, c]]; return M
def skal(M): M = M.copy(); M[:3, 3] *= E.A_MM; return M

lok = G.glieder_lokal(0.5)
P = [l*E.A_MM for l in lok]
F0 = G.rahmen(*G.X0)
REL = [skal(np.linalg.inv(F0[(k + 1) % 6]) @ F0[(k + 2) % 6]) for k in range(6)]   # Glied k -> Glied k+1 (Wuerfellage)

def normale(k, fi):
    _, _, pl = E.koerper(P[k]); return pl[fi][0]

def rot_to(n, target=np.array([0, 0, -1.0])):
    n = n/np.linalg.norm(n); v = np.cross(n, target); s = np.linalg.norm(v); c = n @ target
    if s < 1e-12: return np.eye(3) if c > 0 else np.diag([1, -1, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); return np.eye(3) + vx + vx @ vx*((1 - c)/s**2)

def kette(d2, d4, d0=0.0):
    """Drucktransformationen M_k (lokal mm -> Druckraum) fuer die Drehwinkel an den senkrechten Gelenken 2 und 4"""
    M = [None]*6
    M0 = np.eye(4); M0[:3, :3] = rot_to(normale(0, 2)); M0 = Rz(d0) @ M0; M[0] = M0
    for k in range(5):                   # Gelenk k+1 zwischen Glied k und k+1
        j = k + 1
        if j % 2 == 1:                   # flach: Winkel so, dass F1 von Glied j nach unten zeigt, aufgeklappt
            w = REL[k][:3, :3] @ normale(j, 0); q = M[k][:3, :3].T @ np.array([0, 0, -1.0])
            assert abs(w[2] - q[2]) < 1e-6, (w, q)
            t = np.arctan2(q[1], q[0]) - np.arctan2(w[1], w[0])
            M[j] = M[k] @ Rz(t) @ REL[k]
        else:
            M[j] = M[k] @ Rz(d2 if j == 2 else d4) @ REL[k]
    zmin = min((M[k] @ np.r_[v, 1])[2] for k in range(6) for v in E.koerper(P[k])[1])
    for k in range(6): M[k] = M[k].copy(); M[k][2, 3] -= zmin
    return M

def fussabdruck(k, M):
    V = E.koerper(P[k])[1]; W = (M[:3, :3] @ V.T).T + M[:3, 3]
    return MultiPoint(W[:, :2]).convex_hull

if __name__ == "__main__":
    M = kette(0, 0)
    for k in range(6):
        V = E.koerper(P[k])[1]; W = (M[k][:3, :3] @ V.T).T + M[k][:3, 3]
        print(k, "z min/max", round(W[:, 2].min(), 2), round(W[:, 2].max(), 2))

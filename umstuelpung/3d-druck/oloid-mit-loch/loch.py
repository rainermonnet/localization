import numpy as np, ring, warnings
warnings.filterwarnings('ignore')
def fib(n):
    i = np.arange(n)+0.5; z = 1-2*i/n; r = np.sqrt(1-z*z); a = np.pi*(1+5**0.5)*i
    return np.c_[r*np.cos(a), r*np.sin(a), z]
DIRS = fib(6000)
def strip(A, B):
    """Dreiecke des Streifens zwischen Kurven A(t), B(t) (geschlossen in t)"""
    n = len(A); T = []
    for i in range(n):
        j = (i+1) % n; T.append((A[i], B[i], B[j])); T.append((A[i], B[j], A[j]))
    return np.array(T)
def treffer(T, O, D):
    v0, v1, v2 = T[:, 0], T[:, 1], T[:, 2]; e1 = v1-v0; e2 = v2-v0; hit = np.zeros(len(D), bool)
    for k in range(0, len(D), 500):
        d = D[k:k+500][:, None, :]
        p = np.cross(d, e2[None]); det = np.einsum('ijk,jk->ij', p, e1)
        inv = 1/np.where(np.abs(det) < 1e-12, np.nan, det); s = O - v0
        u = np.einsum('ijk,jk->ij', p, s)*inv; q = np.cross(s, e1); v = np.einsum('ik,jk->ij', D[k:k+500], q)*inv
        t = np.einsum('jk,jk->j', e2, q)[None, :]*inv
        h = (u >= 0) & (v >= 0) & (u+v <= 1) & (t > 1e-9); hit[k:k+500] = h.any(1)
    return hit
def analyse(phid, n=720, paar=(2, 5)):
    E, _ = ring.bahnen(np.deg2rad(phid), n); A = E[:, paar[0]]; B = E[:, paar[1]]
    M = np.array([0.5, 0, 0]); T = strip(A, B); h = treffer(T, M, DIRS)
    L = np.linalg.norm(A-B, axis=1)
    return 1-h.mean(), DIRS[~h], L.min(), L.max()
if __name__ == '__main__':
    for phid in (90, 86.9742, 80.4059, 79.7228, 74.7598, 73.2213, 72, 68.1191):
        frei, Dfrei, lmin, lmax = analyse(phid)
        txt = ""
        if len(Dfrei):
            m = Dfrei.mean(0); txt = f" mittlere Richtung der Oeffnung {np.round(m/np.linalg.norm(m),2)}; Streuung {np.round(Dfrei.std(0),2)}"
        print(f"phi {phid:8.4f}: Diagonale c2-c5 {lmin:.3f}..{lmax:.3f}; Anteil der Richtungen ohne Flaeche {frei*100:5.2f} %{txt}")

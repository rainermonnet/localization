"""Oloid mit Loch: Ring mit Verwindung unter 60 Grad -> c2, c5 laufen ganz um; die Diagonale c2-c5 ueberstreicht ein Band
mit Durchgang in der Mitte. Druckbar als Schale (Band mit Wandstaerke), ueber ein Abstandsfeld (Marching Cubes)."""
import numpy as np, ring, warnings, struct, sys
warnings.filterwarnings('ignore')
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
import fast_simplification

def band(tw, n=1440, k=200):
    E, _ = ring.bahnen(np.deg2rad(180 - tw), n); A = E[:, 2]; B = E[:, 5]
    return A, B

def selbstschnitt(A, B, k=80, tol=0.004):
    """grobe Pruefung: kommen sich Bandpunkte mit weit entfernten Parametern naeher als tol?"""
    n = len(A); lam = np.linspace(0, 1, k)
    P = (A[:, None, :]*(1 - lam[None, :, None]) + B[:, None, :]*lam[None, :, None]).reshape(-1, 3)
    ti = np.repeat(np.arange(n), k); li = np.tile(np.arange(k), n)
    tr = cKDTree(P); pairs = tr.query_pairs(tol, output_type='ndarray')
    dt = np.abs(ti[pairs[:, 0]] - ti[pairs[:, 1]]); dt = np.minimum(dt, n - dt)
    far = dt > n//40
    return far.sum(), P[pairs[far][:, 0]] if far.any() else None

def schale(tw, r=20.0, wand=2.0, vox=0.25):
    A, B = band(tw); A = (A - [0.5, 0, 0])*r; B = (B - [0.5, 0, 0])*r
    # dichte Punktwolke auf dem Band
    L = np.linalg.norm(A - B, axis=1).max(); k = int(L/(vox*0.5)) + 2
    lam = np.linspace(0, 1, k)
    # zusaetzlich zwischen den Parameterschritten verdichten
    n = len(A); step = np.linalg.norm(np.diff(np.vstack([A, A[:1]]), axis=0), axis=1).max()
    sub = int(np.ceil(step/(vox*0.5)))
    tt = np.linspace(0, n, n*sub, endpoint=False); i0 = np.floor(tt).astype(int) % n; i1 = (i0 + 1) % n; f = (tt - np.floor(tt))[:, None]
    AA = A[i0]*(1 - f) + A[i1]*f; BB = B[i0]*(1 - f) + B[i1]*f
    P = (AA[:, None, :]*(1 - lam[None, :, None]) + BB[:, None, :]*lam[None, :, None]).reshape(-1, 3)
    rho = wand/2
    lo = P.min(0) - rho - 2*vox; hi = P.max(0) + rho + 2*vox
    gx = np.arange(lo[0], hi[0], vox); gy = np.arange(lo[1], hi[1], vox); gz = np.arange(lo[2], hi[2], vox)
    tr = cKDTree(P); F = np.empty((len(gx), len(gy), len(gz)), np.float32)
    G = np.stack(np.meshgrid(gy, gz, indexing='ij'), -1).reshape(-1, 2)
    for ix, x in enumerate(gx):
        Q = np.c_[np.full(len(G), x), G]; d, _ = tr.query(Q, distance_upper_bound=rho + 3*vox)
        F[ix] = np.minimum(d, rho + 3*vox).reshape(len(gy), len(gz))
    V, Fc, _, _ = marching_cubes(F, level=rho, spacing=(vox, vox, vox))
    V += lo
    return V, Fc, len(P)

def schreibe(path, V, T, name):
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    vol = np.einsum('ij,ij->i', a, np.cross(b, c)).sum()/6
    if vol < 0: T = T[:, [0, 2, 1]]; a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    nr = np.cross(b - a, c - a); ln = np.linalg.norm(nr, axis=1); ok = ln > 1e-12; nr[ok] /= ln[ok][:, None]
    with open(path, 'wb') as f:
        f.write(name.encode().ljust(80, b' ')); f.write(struct.pack('<I', len(T)))
        for i in range(len(T)): f.write(struct.pack('<12fH', *nr[i], *a[i], *b[i], *c[i], 0))
    return abs(vol)

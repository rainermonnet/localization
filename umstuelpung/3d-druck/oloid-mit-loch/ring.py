"""Sechsgliedriger Gelenkring (Zwanglauf) und seine Bahnen. DH: Rz(theta_i) Tx(l) Rx(alpha_i), alpha = +phi, -phi, ...; theta = t0, t1, t0, t1, t0, t1."""
import numpy as np
from scipy.optimize import least_squares


def Rz(t): c, s = np.cos(t), np.sin(t); return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.]])
def Rx(a): c, s = np.cos(a), np.sin(a); return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1.]])
def Tx(l): M = np.eye(4); M[0, 3] = l; return M


def kette(t0, t1, phi, l=1.0):
    M = np.eye(4); out = [M.copy()]
    for i in range(6):
        M = M @ Rz(t0 if i % 2 == 0 else t1) @ Tx(l) @ Rx(phi if i % 2 == 0 else -phi); out.append(M.copy())
    return out


def rest(x, phi): return (kette(x[0], x[1], phi)[-1] - np.eye(4))[:3, :].ravel()


def jac(x, phi, h=1e-6):
    J = np.zeros((12, 2))
    for k in range(2):
        d = np.zeros(2); d[k] = h; J[:, k] = (rest(x + d, phi) - rest(x - d, phi)) / (2 * h)
    return J


def startpunkt(phi):
    best = None
    for t0 in np.linspace(0.3, 6.0, 40):
        r = least_squares(lambda u: rest(np.array([u[0], 2 * np.pi - u[0]]), phi), [t0], xtol=1e-14, ftol=1e-14)
        if r.cost < 1e-20 and (best is None or r.cost < best[0]): best = (r.cost, r.x[0])
        if best and best[0] < 1e-24: break
    assert best, f"kein Startpunkt fuer phi={np.rad2deg(phi)}"
    return np.array([best[1], 2 * np.pi - best[1]])


def kurve(phi, ds=0.01, maxn=20000):
    x = startpunkt(phi); x0 = x.copy(); pts = [x.copy()]; tprev = None
    for n in range(maxn):
        J = jac(x, phi); U, S, Vt = np.linalg.svd(J); t = Vt[-1]
        if tprev is not None and t @ tprev < 0: t = -t
        if tprev is None: t = t if t[0] > 0 else -t
        tprev = t
        xp = x + ds * t
        for _ in range(8):                                   # Korrektor: Gauss-Newton mit Nebenbedingung (x - xp) . t = 0
            r = rest(xp, phi); J2 = jac(xp, phi)
            A = np.vstack([J2, t[None, :]]); b = np.r_[-r, -(xp - (x + ds * t)) @ t]
            dx = np.linalg.lstsq(A, b, rcond=None)[0]; xp = xp + dx
            if np.abs(dx).max() < 1e-13: break
        assert np.abs(rest(xp, phi)).max() < 1e-9, (n, np.abs(rest(xp, phi)).max())
        x = xp; pts.append(x.copy())
        d = (x - x0 + np.pi) % (2 * np.pi) - np.pi
        if n > 20 and np.hypot(*d) < ds * 0.75: break
    return np.array(pts)


def ecken_in_glied0(t0, t1, phi, l=1.0):
    """Ecken c0..c5 im Rahmen des Gliedes c0-c1 (c0 = 0, c1 = (l,0,0), Gelenkachse z0 = z)."""
    M = kette(t0, t1, phi, l); c = np.array([m[:3, 3] for m in M[:6]])
    x = (c[1] - c[0]) / l; z = np.array([0, 0, 1.]); y = np.cross(z, x); K = np.c_[x, y, z]
    return (K.T @ (c - c[0]).T).T


def bahnen(phi, n=360):
    P = kurve(phi); m = len(P) - 1
    # gleichmaessig in der Bogenlaenge ueber den geschlossenen Kurvenzug neu abtasten
    P2 = P.copy(); P2[-1] = P[0] + ((P[-1] - P[0] + np.pi) % (2 * np.pi) - np.pi) if False else P[-1]
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    idx = np.linspace(0, s[-1], n, endpoint=False)
    t0 = np.interp(idx, s, np.unwrap(P[:, 0])); t1 = np.interp(idx, s, np.unwrap(P[:, 1]))
    E = np.array([ecken_in_glied0(a, b, phi) for a, b in zip(t0, t1)])        # (n, 6, 3)
    return E, (t0, t1)


if __name__ == "__main__":
    d = np.deg2rad
    for phid in (90, 86.9742, 80.4059, 79.7228, 74.7598, 73.2213, 72, 68.1191):
        phi = d(phid); E, _ = bahnen(phi, 240)
        c2, c5 = E[:, 2], E[:, 5]
        r2 = np.linalg.norm(c2 - E[:, 1], axis=1); r5 = np.linalg.norm(c5 - E[:, 0], axis=1)
        diag = np.linalg.norm(c2 - c5, axis=1)
        print(f"phi {phid:8.4f}: Bahn-Punkte {len(E)}  |c2-c1| {r2.min():.4f}..{r2.max():.4f}  |c5-c0| {r5.min():.4f}..{r5.max():.4f}  Diagonale c2-c5 {diag.min():.4f}..{diag.max():.4f}")

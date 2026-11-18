"""Eine Drahtbahn (Dodekaeder I, phi 72) mit acht unterschiedlich grossen Oloiden (Groesse nach Winkel phi)."""
import json, numpy as np
rng = np.random.default_rng(5)
D = json.load(open("bahnen_daten.json")); PHI = [d["phi"] for d in D]
RING = 6; S0 = 1.1
R_MM = [30, 27, 24, 22, 19, 17, 15, 13]          # Kreisradius je Winkel-Index (0:90 Grad ... 7:68,1 Grad)
MASSE = [12.0*(r/20.0)**2 for r in R_MM]          # hohle Schale, Wand 2,4 mm: ~ r^2
DRAHT = 0.015                                     # g/mm, Messing 1,5 mm
ORDER = [0, 1, 2, 3, 4, 5, 6, 7]                  # Reihenfolge am Ring: gross -> klein
# Abmessungen je Oloid aus den Daten: groesste Ausdehnung (Einheit r) und Abstand Spitze-Mitte
c0 = np.array([0.5, 0, 0]); EXT = []; QA = []
for d in D:
    A = np.vstack([np.array(d["flaeche"][0]), np.array(d["flaeche"][1])]); Q = A - A.mean(0)
    w, V = np.linalg.eigh(np.cov(Q.T)); P = Q @ V; EXT.append((P.max(0) - P.min(0)).tolist())
    arc = np.array(d["c"][3]); QA.append(float(np.linalg.norm(arc[len(arc)//2] - c0)))
Pc = np.array(D[RING]["c"][1]); Qc = Pc - Pc.mean(0)
w, V = np.linalg.eigh(np.cov(Qc.T)); Rm = np.c_[V[:, 2], V[:, 0], V[:, 1]]
if np.linalg.det(Rm) < 0: Rm[:, 2] *= -1
X0 = (Qc @ Rm)*S0; n = len(X0)
def ringX(psi):
    ca, sa = np.cos(psi), np.sin(psi); Y = X0.copy(); Y[:, 0] = ca*X0[:, 0] + sa*X0[:, 2]; Y[:, 2] = -sa*X0[:, 0] + ca*X0[:, 2]; return Y
m_ring = DRAHT*D[RING]["laenge"]*S0*100

def gestalt(psi, idx):
    X = ringX(psi); lo = np.array([MASSE[i] for i in range(8)])
    com = (m_ring*np.array([X[:, 0].mean(), X[:, 2].mean()]) + sum(lo[i]*X[idx[i]][[0, 2]] for i in range(8)))/(m_ring + lo.sum())
    ymax, ymin = X[:, 1].max(), X[:, 1].min()
    T = np.array([j for j in range(n) if X[j, 1] >= ymax - 0.45*(ymax - ymin)])
    pa = X[T][:, [0, 2]]; ya = X[T][:, 1]
    d = pa[None, :, :] - pa[:, None, :]; Ln = np.linalg.norm(d, axis=2) + 1e-9
    tt = np.einsum('abk,abk->ab', com[None, None, :] - pa[:, None, :], d)/Ln**2
    foot = pa[:, None, :] + tt[:, :, None]*d; dist = np.linalg.norm(foot - com[None, None, :], axis=2)
    cost = 8*dist**2 + (ya[:, None] - ya[None, :])**2*4 + 0.4*(ymax - np.minimum(ya[:, None], ya[None, :]))
    breite = X[:, 0].max() - X[:, 0].min()
    ok = (np.triu(np.ones((len(T), len(T))), 1) > 0) & (Ln >= 0.55*breite) & (tt > 0.2) & (tt < 0.8)
    if not ok.any(): return None
    cost = np.where(ok, cost, 1e9); ia, ib = np.unravel_index(np.argmin(cost), cost.shape)
    a, b = int(T[ia]), int(T[ib])
    hook = np.array([com[0], max(X[a, 1], X[b, 1]) + 2.0*S0, com[1]])
    return X, com, (a, b), float(dist[ia, ib]), hook

def pruefe(p):
    g = gestalt(p["psi"], p["idx"])
    if g is None: return 1e6, 0, None
    X, com, susp, dist, hook = g; W = X - hook; v = dist*50
    ctr = np.array([X[:, 0].mean(), X[:, 2].mean()]); v += 0.5*np.linalg.norm(com - ctr)
    C = []; rho = []
    for i in range(8):
        so = R_MM[i]/100.0; A = W[p["idx"][i]]; ha = QA[i]*so
        C.append(A + np.array([0, -p["L"][i] - ha, 0])); rho.append(1.55*so + 0.05)
    for i in range(8):
        dmin = np.linalg.norm(W - C[i], axis=1).min()
        # eigener Aufhaengepunkt darf nah sein (Faden): ausnehmen -> Draht ausserhalb +-0.6 Index
        mask = np.ones(n, bool)
        for dj in range(-14, 15): mask[(p["idx"][i] + dj) % n] = False
        dmin = np.linalg.norm(W[mask] - C[i], axis=1).min()
        if dmin < rho[i] + 0.40: v += (rho[i] + 0.40 - dmin)*3
        for j in range(i + 1, 8):
            dd = np.linalg.norm(C[i] - C[j])
            if dd < rho[i] + rho[j] + 0.75: v += (rho[i] + rho[j] + 0.75 - dd)*3
    tief = min(c[1] - r for c, r in zip(C, rho))
    return v, tief, (X, W, hook, susp, C, rho, dist, com)

def zufall():
    gaps = rng.dirichlet(np.ones(8)*4)*n; gaps = np.maximum(gaps, 12); gaps *= n/gaps.sum()
    off = rng.integers(0, n); idx = [int((off + gaps[:k].sum()) % n) for k in range(8)]
    return dict(psi=float(rng.uniform(0, 2*np.pi)), idx=idx, L=[float(rng.choice([0.8, 1.2, 1.6, 2.0, 2.4, 2.8])) for _ in range(8)])
best = (1e9, None)
for it in range(3000):
    p = zufall(); v, tf, _ = pruefe(p); sc = v*100 + tf*(-1)*0.2
    if sc < best[0]: best = (sc, p)
p = best[1]; cur = best[0]
for it in range(12000):
    q = dict(psi=p["psi"], idx=list(p["idx"]), L=list(p["L"])); k = rng.integers(0, 3); j = int(rng.integers(0, 8))
    if k == 0: q["psi"] = float(p["psi"] + rng.normal(0, 0.3))
    elif k == 1: q["idx"][j] = int((p["idx"][j] + rng.integers(-12, 13)) % n)
    else: q["L"][j] = float(np.clip(p["L"][j] + rng.choice([-0.2, 0.2, 0.4, -0.4]), 0.7, 3.2))
    v, tf, _ = pruefe(q); sc = v*100 + tf*(-1)*0.2
    if sc < cur: cur = sc; p = q
v, tief, (X, W, hook, susp, C, rho, dist, com) = pruefe(p)
print("Verletzung", round(v, 4), "tiefster Punkt", round(tief, 2), "(100 mm), Abstand Schwerpunkt-Sehne", round(dist, 4), "Schwerpunkt-Abweichung vom Ringzentrum", round(float(np.linalg.norm(com - np.array([X[:, 0].mean(), X[:, 2].mean()]))), 3))
for i in range(8): print(i, PHI[i], "r", R_MM[i], "mm, Masse", round(MASSE[i], 1), "g, Ausdehnung", np.round(np.array(EXT[i])*R_MM[i]).astype(int), "mm, Index", p["idx"][i], "Faden", round(p["L"][i]*100), "mm")
loads = [dict(oi=i, k=int(p["idx"][i]), L=round(p["L"][i], 3), so=R_MM[i]/100.0) for i in range(8)]
xs = np.vstack([W] + [np.array(C)]); 
out = dict(loop=np.round(W, 4).tolist(), susp=list(susp), loads=loads, r_mm=R_MM, masse=[round(m, 1) for m in MASSE], ext=[[round(x*r, 1) for x in e] for e, r in zip(EXT, R_MM)],
           extent=[float(xs[:, 0].min()), float(xs[:, 0].max()), float(min(c[1] - r for c, r in zip(C, rho))), float(xs[:, 2].min()), float(xs[:, 2].max())], ringlen=round(D[RING]["laenge"]*S0*100))
json.dump(out, open("plan3.json", "w"), separators=(",", ":"))
print("Gesamtmasse", round(sum(MASSE) + m_ring), "g; Draht", out["ringlen"], "mm; x", np.round(out["extent"][:2], 2), "z", np.round(out["extent"][3:], 2))

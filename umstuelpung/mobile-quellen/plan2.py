"""Kaskade aus Draht-Bahnen: Wurzel = Bahn Dodekaeder I (phi 72), daran haengen weitere Bahn-Ringe mit ihren Oloiden."""
import json, numpy as np
rng = np.random.default_rng(7)
D = json.load(open("bahnen_daten.json"))
PHI = [d["phi"] for d in D]
SO = 0.20                      # Oloid: Kreisradius 20 mm (Einheit 100 mm)
S0, S1 = 1.1, 0.62             # Gliedlaenge Wurzel 110 mm, je Ebene x0,62
# Baum: ring -> kinder (Index in D)
BAUM = {6: [5, 4, 7], 5: [2], 4: [3], 7: [1, 0], 2: [], 3: [], 1: [], 0: []}
EBENE = {6: 0, 5: 1, 4: 1, 7: 1, 2: 2, 3: 2, 1: 2, 0: 2}
M_OL = 12.0                    # g je Oloid (hohl, PLA)
DRAHT = 0.015                  # g/mm (Messing 1,5 mm)

_PCA = {}
def ring(i, s, psi):
    if i not in _PCA:
        P = np.array(D[i]["c"][1]); c = P.mean(0); Q = P - c
        w, V = np.linalg.eigh(np.cov(Q.T)); R = np.c_[V[:, 2], V[:, 0], V[:, 1]]
        if np.linalg.det(R) < 0: R[:, 2] *= -1
        _PCA[i] = Q @ R
    X = _PCA[i] * s
    ca, sa = np.cos(psi), np.sin(psi)
    Y = X.copy(); Y[:, 0] = ca*X[:, 0] + sa*X[:, 2]; Y[:, 2] = -sa*X[:, 0] + ca*X[:, 2]
    return Y

def subtree_mass(i):
    s = S0*S1**EBENE[i]; m = DRAHT*D[i]["laenge"]*s*100 + M_OL
    return m + sum(subtree_mass(k) for k in BAUM[i])

def gestalt(i, psi, par):
    """Ring i mit Gier psi: Lastpunkte, Aufhaengepunkte, Haken. par: dict mit L (Oloid), Lc (Kinder)"""
    s = S0*S1**EBENE[i]; X = ring(i, s, psi); n = len(X)
    lasten = ['o'] + list(BAUM[i]); K = len(lasten)
    off = par["off"]; idx = [(off + (n*j)//K) % n for j in range(K)]
    m_ring = DRAHT*D[i]["laenge"]*s*100
    masse = [M_OL] + [subtree_mass(k) for k in BAUM[i]]
    com = (m_ring*np.array([X[:, 0].mean(), X[:, 2].mean()]) + sum(m*X[k][[0, 2]] for m, k in zip(masse, idx)))/(m_ring + sum(masse))
    # Aufhaengepunkte: Sehne durch den Schwerpunkt, beide Punkte im oberen Drittel, gleich hoch
    ymax, ymin = X[:, 1].max(), X[:, 1].min()
    T = np.array([j for j in range(n) if X[j, 1] >= ymax - 0.45*(ymax - ymin)])
    pa = X[T][:, [0, 2]]; ya = X[T][:, 1]
    d = pa[None, :, :] - pa[:, None, :]                       # [a,b] = pb - pa
    Ln = np.linalg.norm(d, axis=2) + 1e-9
    tt = np.einsum('abk,abk->ab', com[None, None, :] - pa[:, None, :], d)/Ln**2
    foot = pa[:, None, :] + tt[:, :, None]*d
    dist = np.linalg.norm(foot - com[None, None, :], axis=2)
    cost = 8*dist**2 + (ya[:, None] - ya[None, :])**2*4 + 0.4*(ymax - np.minimum(ya[:, None], ya[None, :]))
    breite = (X[:, 0].max() - X[:, 0].min())*(1 if i == 6 else 0.9)
    ok = (np.triu(np.ones((len(T), len(T))), 1) > 0) & (Ln >= 0.55*breite) & (tt > 0.2) & (tt < 0.8)
    if not ok.any(): ok = np.triu(np.ones((len(T), len(T))), 1) > 0
    cost = np.where(ok, cost, 1e9); ia, ib = np.unravel_index(np.argmin(cost), cost.shape)
    a, b, dist, t = int(T[ia]), int(T[ib]), float(dist[ia, ib]), float(tt[ia, ib])
    hook = np.array([com[0], max(X[a, 1], X[b, 1]) + 2.0*s, com[1]])
    return dict(i=i, s=s, X=X, idx=idx, lasten=lasten, susp=[a, b], hook=hook, com=com, dist=dist, m_ring=m_ring)

def bauen(par):
    """rekursiv: Weltkoordinaten von Draehten, Oloid-Mittelpunkten; liefert Knoten-Liste"""
    knoten = {}; wire = []; olo = []
    def rec(i, hook_world):
        g = gestalt(i, par[i]["psi"], par[i]); knoten[i] = g
        W = g["X"] - g["hook"] + hook_world; g["W"] = W; wire.append(W)
        for lst, k in zip(g["lasten"], g["idx"]):
            A = W[k]
            if lst == 'o':
                H = A + np.array([0, -par[i]["L"], 0]); olo.append((i, H + np.array([0, -0.30*SO/0.2, 0]))); g["oh"] = H
            else:
                rec(lst, A + np.array([0, -par[i]["Lc"], 0]))
    rec(6, np.zeros(3)); return knoten, wire, olo

def pruefe(par):
    knoten, wire, olo = bauen(par)
    rho = 1.5*SO + 0.05; gap = 0.35; v = 0.0
    allw = [(i, w) for i, w in zip(knoten.keys(), wire)]
    for (i, c) in olo:
        for (j, w) in allw:
            d = np.linalg.norm(w - c, axis=1).min()
            if d < rho + gap: v += (rho + gap - d)
    for a in range(len(olo)):
        for b in range(a + 1, len(olo)):
            d = np.linalg.norm(olo[a][1] - olo[b][1])
            if d < 2*rho + 0.5: v += (2*rho + 0.5 - d)
    ks = list(knoten.keys())
    for a in range(len(ks)):
        for b in range(a + 1, len(ks)):
            d = np.min(np.linalg.norm(wire[a][::6, None, :] - wire[b][None, ::6, :], axis=2))
            if d < 0.75: v += (0.75 - d)*2
    ytief = min(w[:, 1].min() for w in wire); ytief = min(ytief, min(c[1] - rho for _, c in olo))
    return v, ytief, knoten, wire, olo

par = {i: dict(psi=0.0, off=21, L=1.2, Lc=0.8) for i in BAUM}
for i in par:
    pass
best = (1e9, None)
for it in range(900):
    cand = {i: dict(psi=float(rng.uniform(0, 2*np.pi)), off=int(rng.integers(0, 240)), L=float(rng.choice([0.9, 1.2, 1.5, 1.8, 2.1])), Lc=float(rng.choice([0.5, 0.8, 1.1, 1.4]))) for i in BAUM}
    v, yt, *_ = pruefe(cand)
    sc = v*100 - yt
    if sc < best[0]: best = (sc, cand, v, yt)
print("Zufallssuche:", round(best[2], 3), round(best[3], 2))
par = best[1]
# lokale Verbesserung
cur = best[0]
for it in range(3000):
    c2 = {i: dict(p) for i, p in par.items()}; i = int(rng.choice(list(par.keys()))); k = rng.choice(['psi', 'off', 'L', 'Lc'])
    if k == 'psi': c2[i]['psi'] = float(par[i]['psi'] + rng.normal(0, 0.4))
    elif k == 'off': c2[i]['off'] = int((par[i]['off'] + rng.integers(-20, 21)) % 240)
    elif k == 'L': c2[i]['L'] = float(np.clip(par[i]['L'] + rng.choice([-0.1, 0.1, 0.2, -0.2]), 0.8, 2.2))
    else: c2[i]['Lc'] = float(np.clip(par[i]['Lc'] + rng.choice([-0.1, 0.1, 0.2, -0.2]), 0.4, 2.0))
    v, yt, *_ = pruefe(c2); sc = v*100 - yt
    if sc < cur: cur = sc; par = c2
v, yt, knoten, wire, olo = pruefe(par)
print("Verletzung", round(v, 4), "tiefster Punkt (100 mm)", round(yt, 2))
for i, g in knoten.items():
    print("Ring", i, "phi", PHI[i], "s", round(g["s"], 3), "Schwerpunkt-Abstand von der Sehne", round(g["dist"], 3), "Fadenlaengen",
          [round(float(np.linalg.norm(g["hook"] - g["X"][a])*100)) for a in g["susp"]], "mm", par[i])
# Ausgabe
nodes = {}
for i, g in knoten.items():
    X = g["X"] - g["hook"]
    nodes[i] = dict(i=i, phi=PHI[i], s=round(g["s"], 4), loop=np.round(X, 4).tolist(), susp=g["susp"], loads=[
        dict(t=('o' if l == 'o' else 'c'), k=int(k), L=round(par[i]["L"] if l == 'o' else par[i]["Lc"], 3), child=(None if l == 'o' else int(l))) for l, k in zip(g["lasten"], g["idx"])],
        draht_mm=round(D[i]["laenge"]*g["s"]*100))
hoehe = float(-yt) + 2.0*S0
json.dump(dict(nodes=nodes, root=6, hoehe=round(hoehe, 3), so=SO), open("plan2.json", "w"), separators=(",", ":"))
print("Gesamthoehe etwa", round(hoehe*100), "mm; Draht gesamt", sum(n["draht_mm"] for n in nodes.values()), "mm; Masse etwa", round(subtree_mass(6)), "g")
xs = np.concatenate(wire); print("Breite x", xs[:,0].min().round(2), xs[:,0].max().round(2), "z", xs[:,2].min().round(2), xs[:,2].max().round(2))

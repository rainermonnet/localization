import numpy as np, json, ring, manifold3d as m3
import guertel as G, guertel_bau as B
a = B.A_MM; lok = G.glieder_lokal(0.5)
P = ring.kurve(G.PHI); u = np.c_[np.unwrap(P[:, 0]), np.unwrap(P[:, 1])]
s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(u, axis=0), axis=1))]; N = 480
ss = np.linspace(0, s[-1], N, endpoint=False); T0 = np.interp(ss, s, u[:, 0]); T1 = np.interp(ss, s, u[:, 1])
F0 = G.rahmen(*G.X0); MITTE = np.array([-0.5, 0.5, -0.5])*a
def skal(M): M = M.copy(); M[:3, 3] *= a; return M
def verschiebe(M): M = M.copy(); M[:3, 3] -= MITTE; return M
c_ref = np.array([f[:3, 3] for f in F0])
modus_a = []; modus_b = []; oloid = []
for t0, t1 in zip(T0, T1):
    F = G.rahmen(t0, t1)
    inv1 = np.linalg.inv(F[1])
    A_ = [verschiebe(skal(F0[1] @ inv1 @ F[(k + 1) % 6])) for k in range(6)]
    c = np.array([f[:3, 3] for f in F]); cm = c.mean(0); rm = c_ref.mean(0)
    H = (c - cm).T @ (c_ref - rm); U, S, Vt = np.linalg.svd(H); d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1, 1, d]) @ U.T; K = np.eye(4); K[:3, :3] = R; K[:3, 3] = rm - R @ cm
    B_ = [verschiebe(skal(K @ F[(k + 1) % 6])) for k in range(6)]
    modus_a.append([np.round(m[:3, :].ravel(), 4).tolist() for m in A_]); modus_b.append([np.round(m[:3, :].ravel(), 4).tolist() for m in B_])
    p2 = inv1 @ np.r_[F[2][:3, 3], 1]; p5 = inv1 @ np.r_[F[5][:3, 3], 1]
    oloid.append([np.round(p2[:3]*a, 3).tolist(), np.round(p5[:3]*a, 3).tolist()])
glieder = []
for k in range(6):
    V, Tr = B.from_m(B.glied(k, lok)); glieder.append(dict(v=np.round(V, 3).ravel().tolist(), f=Tr.ravel().tolist(),
        achsen=[np.round(lok[k][[0, 1]]*a, 3).tolist(), np.round(lok[k][[2, 3]]*a, 3).tolist()]))
# Sterne: Wuerfel minus Guertel-Tetraeder (Wuerfellage), in Anzeigekoordinaten
Wt = G.welt(lok, *G.X0); U_ = None
for T in Wt:
    m = B.tetra(T*a); U_ = m if U_ is None else U_ + m
cube = m3.Manifold.cube([a, a, a]).translate([-a, 0, -a])
F0c = G.rahmen(*G.X0); cz = np.array([f[:3, 3] for f in F0c])
def schnittpunkt(ids):
    z = np.array([f[:3, 2] for f in F0c]); A_ = np.vstack([np.eye(3) - np.outer(z[i], z[i]) for i in ids]); b_ = np.concatenate([(np.eye(3) - np.outer(z[i], z[i])) @ cz[i] for i in ids])
    return np.linalg.lstsq(A_, b_, rcond=None)[0]
PA = schnittpunkt([0, 2, 4])*a; PB = schnittpunkt([1, 3, 5])*a; ctr = (PA + PB)/2; nAB = (PA - PB)/np.linalg.norm(PA - PB)
rest = cube
for T in Wt: rest = rest - B.tetra(T*a)
sterne = []
for sgn in (1, -1):
    halb = rest.trim_by_plane((sgn*nAB).tolist(), float(np.dot(sgn*nAB, ctr)))
    teile = [p for p in halb.decompose() if p.volume() > 100]
    for p in teile:
        V, Tr = B.from_m(p.translate((-MITTE).tolist())); sterne.append(dict(v=np.round(V, 3).ravel().tolist(), f=Tr.ravel().tolist(), vol=round(p.volume()/1000, 2)))
json.dump(dict(a=a, n=N, A=modus_a, B=modus_b, oloid=oloid, glieder=glieder, sterne=sterne), open('guertel_daten.json', 'w'), separators=(',', ':'))
print("Sterne:", [s_['vol'] for s_ in sterne], "cm3; Guertel", round(U_.volume()/1000, 2), "cm3; Wuerfel", a**3/1000)
import os; print("Datei", os.path.getsize('guertel_daten.json')//1024, "KB")
d = np.linalg.norm(np.array([o[0] for o in oloid]) - np.array([o[1] for o in oloid]), axis=1); print("Diagonale c2-c5 (mm):", d.min().round(2), d.max().round(2), " soll", round(a*3**0.5, 2))

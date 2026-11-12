import numpy as np
from scipy.spatial import ConvexHull, HalfspaceIntersection
from oloid_stl import *

def best_down(P, tri):
    nn, ar = facets(P, tri)
    cand = np.unique(np.round(nn, 2), axis=0)
    res = sorted((overhang(P, tri, rot_to_down(n)), tuple(n)) for n in cand)
    return np.array(res[0][1])

def prepare(r, cut=None, n=1440):
    P, tri = oloid_mesh(1.0, n)
    n_down = best_down(P, tri)
    R = rot_to_down(n_down)
    Q = P @ R.T
    h = ConvexHull(Q)
    if cut:
        z0 = Q[:,2].min()
        hs = np.vstack([h.equations, [0, 0, -1, z0 + cut]])   # z >= z0+cut  ->  -z + (z0+cut) <= 0
        # innerer Punkt
        ip = Q.mean(0)
        V = HalfspaceIntersection(hs, ip).intersections
        V = V[np.isfinite(V).all(1)]
        V = np.unique(np.round(V, 7), axis=0)
        h = ConvexHull(V); Q = V
    tri = h.simplices.copy(); c = Q.mean(0)
    for i, f in enumerate(tri):
        a, b, d = Q[f]
        if np.dot(np.cross(b-a, d-a), a-c) < 0: tri[i] = f[[0,2,1]]
    Q = Q*r
    Q[:,0] -= (Q[:,0].min()+Q[:,0].max())/2; Q[:,1] -= (Q[:,1].min()+Q[:,1].max())/2
    Q[:,2] -= Q[:,2].min()
    return Q, tri

for name, r, cut in [("Oloid_r22mm_66mm_mit-Standflaeche", 22, 0.03), ("Oloid_r30mm_90mm_mit-Standflaeche", 30, 0.03), ("Oloid_r22mm_66mm_exakt", 22, None)]:
    Q, tri = prepare(r, cut)
    write_stl(f"{name}.stl", Q, tri, name)
    ext = Q.max(0)-Q.min(0)
    z = Q[:,2]; patch = Q[z < 1e-6]
    pe = (patch.max(0)-patch.min(0)) if len(patch) else None
    print(name, "Ausdehnung mm", np.round(ext,2), "V=%.2f cm³"%(abs(volume(Q,tri))/1000), "Dreiecke", len(tri), "Standflaeche mm", None if pe is None else np.round(pe[:2],2))

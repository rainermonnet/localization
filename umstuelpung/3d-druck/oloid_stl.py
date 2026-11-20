import numpy as np, struct, sys
from scipy.spatial import ConvexHull

def oloid_mesh(r=1.0, n=1440):
    t = np.linspace(0, 2*np.pi, n, endpoint=False)
    c1 = np.c_[-r/2 + r*np.cos(t), r*np.sin(t), 0*t]     # Kreis in xy
    c2 = np.c_[ r/2 + r*np.cos(t), 0*t, r*np.sin(t)]     # Kreis in xz
    P = np.vstack([c1, c2])
    h = ConvexHull(P)
    tri = h.simplices.copy()
    # nach aussen orientieren
    c = P.mean(0)
    for i, f in enumerate(tri):
        a, b, d = P[f]
        nrm = np.cross(b-a, d-a)
        if np.dot(nrm, a-c) < 0:
            tri[i] = f[[0, 2, 1]]
    return P, tri

def facets(P, tri):
    a, b, c = P[tri[:,0]], P[tri[:,1]], P[tri[:,2]]
    nr = np.cross(b-a, c-a)
    ar = np.linalg.norm(nr, axis=1)/2
    return nr/np.linalg.norm(nr,axis=1)[:,None], ar

def rot_to_down(n):
    # Rotation, die n auf -z abbildet
    z = np.array([0,0,-1.0]); v = np.cross(n, z); s = np.linalg.norm(v); cth = np.dot(n, z)
    if s < 1e-12: return np.eye(3) if cth > 0 else np.diag([1,-1,-1.0])
    vx = np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3) + vx + vx@vx*((1-cth)/s**2)

def overhang(P, tri, R, limit=45):
    Q = P@R.T
    nn, ar = facets(Q, tri)
    # Fläche, die steiler als limit überhängt (Normale zeigt nach unten, aber nicht die Auflagefläche selbst)
    zmin = Q[:,2].min()
    cz = Q[tri].mean(1)[:,2]
    m = (nn[:,2] < -np.cos(np.radians(limit))) & (cz > zmin + 0.3)
    return ar[m].sum()

def write_stl(path, P, tri, name="oloid"):
    a, b, c = P[tri[:,0]], P[tri[:,1]], P[tri[:,2]]
    nr = np.cross(b-a, c-a); nr /= np.linalg.norm(nr, axis=1)[:,None]
    with open(path, 'wb') as f:
        f.write(name.encode().ljust(80, b' '))
        f.write(struct.pack('<I', len(tri)))
        for i in range(len(tri)):
            f.write(struct.pack('<12fH', *nr[i], *a[i], *b[i], *c[i], 0))

def volume(P, tri):
    a, b, c = P[tri[:,0]], P[tri[:,1]], P[tri[:,2]]
    return np.einsum('ij,ij->i', a, np.cross(b, c)).sum()/6
def area(P, tri):
    a, b, c = P[tri[:,0]], P[tri[:,1]], P[tri[:,2]]
    return np.linalg.norm(np.cross(b-a, c-a), axis=1).sum()/2

if __name__ == '__main__':
    P, tri = oloid_mesh(1.0)
    print('V/r^3 =', volume(P, tri), '(exakt ~3.0524185)  A/r^2 =', area(P, tri), '(exakt 4π =', 4*np.pi, ')  Dreiecke:', len(tri))
    nn, ar = facets(P, tri)
    # Kandidaten für Auflage
    best = None
    idx = np.argsort(-ar)[:0]
    cand = np.unique(np.round(nn, 2), axis=0)
    res = []
    for n in cand:
        R = rot_to_down(n)
        res.append((overhang(P, tri, R), tuple(n)))
    res.sort()
    print('beste 3 Auflagen (Überhangfläche/r²):', res[:3], ' schlechteste:', res[-1][0])

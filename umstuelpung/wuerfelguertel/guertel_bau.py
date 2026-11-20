"""Druckbarer Wuerfelguertel: sechs Tetraeder-Glieder mit Knoechel-Scharnieren auf den Gelenkkanten.
Bolzen: Stueck 1,75-mm-Filament (Bohrung 2,0 mm). Masse a = Kantenlaenge des Wuerfels."""
import numpy as np, manifold3d as m3
import guertel as G
A_MM = 60.0          # Wuerfelkante
R_K = 3.2            # Knoechelradius
SPALT_R = 0.5        # radiales Spiel um fremde Knoechel
SPALT_A = 0.4        # axiales Spiel je Seite
BOHR = 1.0           # Bohrungsradius (Filament 1,75 mm)
def to_m(V, T): return m3.Manifold(m3.Mesh(np.asarray(V, np.float32), np.asarray(T, np.uint32)))
def from_m(M):
    me = M.to_mesh(); return np.asarray(me.vert_properties)[:, :3].astype(float), np.asarray(me.tri_verts).astype(int)
def tetra(P):
    T = np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]]); c = P.mean(0)
    for i, f in enumerate(T):
        a, b, d = P[f]
        if np.dot(np.cross(b - a, d - a), a - c) < 0: T[i] = f[[0, 2, 1]]
    return to_m(P, T)
def zylinder(p, q, r, u0, u1, n=48):
    """Zylinder um die Achse p->q (Einheitslaenge |q-p|), von Parameter u0 bis u1 (in mm entlang der Achse)"""
    d = (q - p)/np.linalg.norm(q - p); L = u1 - u0
    Z = m3.Manifold.cylinder(L, r, r, n)                  # entlang +z, 0..L
    zax = np.array([0, 0, 1.0]); v = np.cross(zax, d); s = np.linalg.norm(v); c = np.dot(zax, d)
    if s < 1e-12: Rm = np.eye(3) if c > 0 else np.diag([1, -1, -1.0])
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); Rm = np.eye(3) + vx + vx @ vx*((1 - c)/s**2)
    M4 = np.eye(4)[:3]; M4[:, :3] = Rm; M4[:, 3] = p + d*u0
    return Z.transform(M4)
ZONE = 0.72          # Knoechel nur auf dem Teil der Gelenkkante nahe der Wuerfelecke (0 .. ZONE*L)
def glied(k, lok):
    """Glied k im Rahmen F[k+1] (mm): Ecken c_k, H_k (Startachse), c_k+1, H_k+1 (Endachse)"""
    P = lok[k]*A_MM; ck, hk, ck1, hk1 = P
    L = np.linalg.norm(hk - ck); z = ZONE*L; s3 = z/3.0; ga = SPALT_A; rr = R_K + SPALT_R
    body = tetra(P)
    # Startachse c_k -> H_k: eigener Mittel-Knoechel; Platz fuer die beiden Aussen-Knoechel des Vorgaengers
    body = body + zylinder(ck, hk, R_K, s3 + ga, 2*s3 - ga)
    body = body - zylinder(ck, hk, rr, -2.0, s3) - zylinder(ck, hk, rr, 2*s3, z + ga)
    # Endachse c_k+1 -> H_k+1: eigene Aussen-Knoechel; Platz fuer den Mittel-Knoechel des Nachfolgers
    body = body + zylinder(ck1, hk1, R_K, ga, s3 - ga) + zylinder(ck1, hk1, R_K, 2*s3 + ga, z - ga)
    body = body - zylinder(ck1, hk1, rr, s3, 2*s3)
    # Bohrungen fuer den Bolzen (ganze Knoechelzone)
    body = body - zylinder(ck, hk, BOHR, -2.0, z + 2.0, 24) - zylinder(ck1, hk1, BOHR, -2.0, z + 2.0, 24)
    return body

def rot_to(n, target=np.array([0, 0, -1.0])):
    n = n/np.linalg.norm(n); v = np.cross(n, target); s = np.linalg.norm(v); c = np.dot(n, target)
    if s < 1e-12: return np.eye(3) if c > 0 else np.diag([1, -1, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); return np.eye(3) + vx + vx @ vx*((1 - c)/s**2)

def druecklage(k, lok, schnitt=0.6):
    """Glied auf die Kante H_k-H_k+1 stellen (Flaechen 39 Grad zur Senkrechten), unten schnitt mm flach abschneiden"""
    P = lok[k]*A_MM; c = P.mean(0)
    def fn(f):
        a_, b_, d_ = P[list(f)]; n = np.cross(b_ - a_, d_ - a_); n /= np.linalg.norm(n)
        return n if np.dot(n, a_ - c) > 0 else -n
    n = fn((1, 2, 3)) + fn((0, 1, 3)); R = rot_to(n)
    M = glied(k, lok); M4 = np.zeros((3, 4)); M4[:, :3] = R
    M = M.transform(M4)
    zkante = (P[[1, 3]] @ R.T)[:, 2].min()
    M = M.translate([0, 0, -zkante])
    bb = M.bounding_box()
    unter = M ^ m3.Manifold.cube([400, 400, 50]).translate([-200, -200, -50])
    M = M ^ m3.Manifold.cube([400, 400, 200]).translate([-200, -200, schnitt])
    M = M.translate([0, 0, -schnitt])
    return M, unter.volume(), bb

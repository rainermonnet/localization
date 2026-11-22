"""Wuerfelguertel v2: Tetraeder liegend gedruckt + separate Print-in-Place-Scharniere in Taschen (Prinzip aus dem Video).
Alle Masse in mm. Glied k haengt starr am Rahmen F[k+1]; lok[k] = Ecken c_k, H_k, c_k+1, H_k+1.
Endachse von Glied k (c_k+1 -> H_k+1): Lasche A liegt in Flaeche F4 = (H_k, c_k+1, H_k+1)
Startachse von Glied k (c_k -> H_k):   Lasche B liegt in Flaeche F2 = (c_k, H_k, H_k+1)
Druckflaeche F3 = (c_k, c_k+1, H_k+1) liegt auf dem Bett, keine Tasche, keine Waben."""
import numpy as np, manifold3d as m3
import guertel as G

A_MM = 70.0       # Wuerfelkante -> Gelenkkante 35 mm
INSET = 0.6       # jede Tetraederflaeche 0,6 mm nach innen versetzt (Gelenkachse liegt 0,6 mm ueber der Flaeche)
R = 2.8           # Knoechelradius
T = 2.2           # Laschendicke (R - T = INSET -> Lasche buendig in der Tasche)
D = 14.0          # Laschentiefe ab Achse (Klebeflaeche)
PIN = 1.25        # Bolzenradius (fest an Knoechel A)
SPIEL = 0.4       # radiales + axiales Spiel im Scharnier
U0, U1 = 2.0, 27.0  # Scharnierzone entlang der Gelenkkante (0 = Wuerfelecke c, 35 = Kantenmitte H)
TASCHE = 0.15     # Spiel der Lasche in der Tasche (zum Einkleben)
FREI = 3.6        # Freistich um die Achse in beiden Tetraedern
FREI_L = 3.8      # Laschen sind neben fremden Knoecheln bis zu diesem Radius ausgespart

def hull(pts): return m3.Manifold.hull_points(np.asarray(pts, float))

class Rahmen:
    """Gelenk-Koordinaten: x entlang Achse (c->H), y in der Flaeche (in die Flaeche hinein), z = Flaechennormale nach aussen"""
    def __init__(s, c, h, o, cen):
        s.c = c; s.ex = (h - c)/np.linalg.norm(h - c)
        v = o - c; v = v - (v @ s.ex)*s.ex; s.ey = v/np.linalg.norm(v)
        n = np.cross(s.ex, s.ey); s.ez = n if n @ (c - cen) > 0 else -n
    def p(s, u, y, z): return s.c + np.outer(u, s.ex) + np.outer(y, s.ey) + np.outer(z, s.ez) if np.ndim(u) else s.c + u*s.ex + y*s.ey + z*s.ez
    def box(s, u0, u1, y0, y1, z0, z1):
        return hull([s.p(u, y, z) for u in (u0, u1) for y in (y0, y1) for z in (z0, z1)])
    def zyl(s, u0, u1, r, n=48):
        a = np.linspace(0, 2*np.pi, n, endpoint=False); pts = []
        for u in (u0, u1):
            for t in a: pts.append(s.p(u, r*np.cos(t), r*np.sin(t)))
        return hull(pts)

def zonen():
    s = (U1 - U0)/3; g = SPIEL/2
    A = [(U0, U0 + s - g), (U0 + 2*s + g, U1)]
    B = [(U0 + s + g, U0 + 2*s - g)]
    return A, B, s

def haelfte(r, rolle):
    """eine Scharnierhaelfte im Gelenkrahmen r. rolle 'A': Aussenknoechel + Bolzen; 'B': Mittelknoechel + Bohrung"""
    A, B, s = zonen(); g = SPIEL/2
    lasche = r.box(U0, U1, 0.0, D, -R, -R + T)
    if rolle == 'A':
        lasche = lasche - r.zyl(U0 + s - g - 0.01, U0 + 2*s + g + 0.01, FREI_L)
        k = r.zyl(*A[0], R) + r.zyl(*A[1], R)
        return lasche + k + r.zyl(U0 + 0.6, U1 - 0.6, PIN, 32)
    lasche = lasche - r.zyl(U0 - 1, U0 + s + g, FREI_L) - r.zyl(U0 + 2*s - g, U1 + 1, FREI_L)
    k = r.zyl(*B[0], R)
    return lasche + k - r.zyl(B[0][0] - 1, B[0][1] + 1, PIN + SPIEL, 32)

def tetra_inset(P, d=INSET):
    cen = P.mean(0); pl = []
    for f in G.FACES:
        a, b, c = P[list(f)]; n = np.cross(b - a, c - a); n /= np.linalg.norm(n)
        if n @ (a - cen) < 0: n = -n
        pl.append((n, n @ a - d))
    V = []
    for i in range(4):
        idx = [j for j in range(4) if j != i]          # Ecke i liegt NICHT auf Flaeche i? -> Flaechen ohne Ecke
        # Flaeche f enthaelt alle Ecken ausser einer; Ecke v = Schnitt der drei Flaechen, die v enthalten
    for v in range(4):
        fs = [j for j, f in enumerate(G.FACES) if v in f]
        M = np.array([pl[j][0] for j in fs]); b = np.array([pl[j][1] for j in fs])
        V.append(np.linalg.solve(M, b))
    return hull(V), np.array(V)

def rahmen_glied(k, lok):
    P = lok[k]*A_MM; cen = P.mean(0)
    rA = Rahmen(P[2], P[3], P[1], cen)    # Endachse, Flaeche F4
    rB = Rahmen(P[0], P[1], P[3], cen)    # Startachse, Flaeche F2
    return P, rA, rB

def glied(k, lok, mit_haelften=False):
    P, rA, rB = rahmen_glied(k, lok)
    body, V = tetra_inset(P)
    for r in (rA, rB):
        body = body - r.box(U0 - TASCHE, U1 + TASCHE, -1.0, D + TASCHE, -R - 0.1, 2.0)   # Tasche (offen zur Flaeche)
        body = body - r.zyl(U0 - SPIEL - 0.5, U1 + SPIEL + 0.5, FREI)                     # Freistich um die Achse
    if mit_haelften:
        body = body + haelfte(rA, 'A') + haelfte(rB, 'B')
    return body

def scharnier_druck(spiel=None):
    """ganzes Scharnier flach (180 Grad offen), Laschen auf dem Bett, Achse entlang x"""
    global SPIEL
    alt = SPIEL
    if spiel is not None: SPIEL = spiel
    cen = np.array([0, 0, -10.0])
    rA = Rahmen(np.zeros(3), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 1.0, -10]))
    rB = Rahmen(np.zeros(3), np.array([1.0, 0, 0]), np.array([0, -1.0, 0]), np.array([0, -1.0, -10]))
    M = haelfte(rA, 'A') + haelfte(rB, 'B')
    SPIEL = alt
    return M.translate([-U0, 0, R])

if __name__ == "__main__":
    lok = G.glieder_lokal(0.5)
    for k in range(2):
        P, rA, rB = rahmen_glied(k, lok)
        print(k, "rA axes", np.round(rA.ex, 3), np.round(rA.ey, 3), np.round(rA.ez, 3), "det", round(np.linalg.det(np.c_[rA.ex, rA.ey, rA.ez]), 3),
              "| rB det", round(np.linalg.det(np.c_[rB.ex, rB.ey, rB.ez]), 3))
    S = scharnier_druck()
    print("Scharnier: Volumen", round(S.volume(), 1), "Teile", len(S.decompose()), "bbox", S.bounding_box())
    g = glied(0, lok)
    print("Glied 0 Volumen", round(g.volume(), 1), "Teile", len(g.decompose()))

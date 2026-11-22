"""Wuerfelguertel v3 - einteilig gedruckt (Print-in-Place), Machart wie der 'origami transforming cube'.
Glied k haengt am Rahmen F[k+1]; lok[k] = c_k, H_k, c_k+1, H_k+1.  Gelenk j liegt auf der Kante c_j-H_j.
Aussenflaechen F1=(c,H,c1) und F3=(c,c1,H1) werden um AUSSEN nach aussen versetzt (Gelenkachse liegt dann
AUSSEN mm ueber der Bettflaeche), Innenflaechen F2, F4 um INNEN nach innen.
Drucklage: gerade Glieder auf F3, ungerade auf F1 -> Gelenke 1,3,5 liegen flach auf dem Bett, 2,4 stehen senkrecht,
Gelenk 0 (senkrecht) bleibt offen und wird nach dem Druck mit einem Stueck 1,75-mm-Filament geschlossen."""
import numpy as np, manifold3d as m3
import guertel as G

A_MM = 70.0
AUSSEN = 2.4      # Aussenflaechen nach aussen
INNEN = 0.6       # Innenflaechen nach innen
R = 3.0           # Knoechelradius
PIN = 1.0         # Bolzenradius (fest an den Knoecheln von Glied j-1)
SP = 0.4          # Spiel
SPK = 0.6         # axiales Spiel an den Kegelflaechen der senkrechten Gelenke (= 0,42 mm senkrecht zur Flaeche)
RF = 5.4          # Freistich um die Achse neben fremden Knoecheln
U0, U1 = 1.5, 33.5  # Knoechelzone auf der 35-mm-Kante
NK = 5            # Knoechel je Gelenk (A B A B A)
FIL = 1.0         # Bohrungsradius im offenen Gelenk 0 (Filament 1,75 mm)
S2 = np.sqrt(2)

def hull(p): return m3.Manifold.hull_points(np.asarray(p, float))

class Achse:
    def __init__(s, c, h):
        s.c = np.asarray(c, float); s.ex = (h - c)/np.linalg.norm(h - c)
        t = np.array([1.0, 0, 0]) if abs(s.ex[0]) < 0.9 else np.array([0, 1.0, 0])
        s.e1 = np.cross(s.ex, t); s.e1 /= np.linalg.norm(s.e1); s.e2 = np.cross(s.ex, s.e1)
    def ring(s, u, r, n=40):
        a = np.linspace(0, 2*np.pi, n, endpoint=False)
        return [s.c + u*s.ex + r*(np.cos(t)*s.e1 + np.sin(t)*s.e2) for t in a] if r > 1e-9 else [s.c + u*s.ex]
    def zyl(s, a, b, r, n=40): return hull(s.ring(a, r, n) + s.ring(b, r, n))
    def kegel(s, a, r, h, n=40): return hull(s.ring(a, r, n) + s.ring(a + h, 0))     # Spitze in +ex
    def knoechel(s, a, b, r, konisch):
        """konisch: Oberseite Kegel nach oben, Unterseite Kegel-Hohlraum (selbsttragend fuer senkrechte Achse)"""
        K = s.zyl(a, b, r)
        if konisch: K = K + s.kegel(b - 0.02, r, r + 0.02) - s.kegel(a - 0.05, r + 0.05, r + 0.05)
        return K
    def freiraum(s, a, b, r, g, konisch):
        if konisch: return s.knoechel(a - g*(S2 + 1), b + g*(S2 - 1), r + g, True)
        return s.zyl(a - g, b + g, r + g)

def ebenen(P, off):
    """Halbraeume des Tetraeders P mit Versatz je Flaeche (positiv = nach innen)"""
    cen = P.mean(0); out = []
    for fi, f in enumerate(G.FACES):
        a, b, c = P[list(f)]; n = np.cross(b - a, c - a); n /= np.linalg.norm(n)
        if n @ (a - cen) < 0: n = -n
        out.append((n, n @ a - off[fi]))
    return out

def koerper(P):
    off = [-AUSSEN, INNEN, -AUSSEN, INNEN]          # F1 aussen, F2 innen, F3 aussen, F4 innen
    pl = ebenen(P, off); V = []
    for v in range(4):
        fs = [j for j, f in enumerate(G.FACES) if v in f]
        V.append(np.linalg.solve(np.array([pl[j][0] for j in fs]), np.array([pl[j][1] for j in fs])))
    return hull(V), np.array(V), pl

def segmente():
    L = (U1 - U0)/NK; return [(U0 + i*L, U0 + (i + 1)*L) for i in range(NK)]

def gelenk_typ(j):
    return "offen" if j == 0 else ("flach" if j % 2 == 1 else "senkrecht")

def teile(lok):
    """liefert je Glied (lokal, mm) das fertige Manifold"""
    P = [l*A_MM for l in lok]
    body = []; pl = []
    for k in range(6):
        b, V, p = koerper(P[k]); body.append(b); pl.append(p)
    add = [[] for _ in range(6)]; sub = [[] for _ in range(6)]; bohr = [[] for _ in range(6)]
    for j in range(6):
        ka, kb = (j - 1) % 6, j            # A = Glied j-1 (Endachse), B = Glied j (Startachse)
        typ = gelenk_typ(j); kon = typ != "flach"
        ax = Achse(P[ka][2], P[ka][3])     # c_j -> H_j im Rahmen von A
        axb = Achse(P[kb][0], P[kb][1])    # dieselbe Kante im Rahmen von B
        seg = segmente(); g = (SPK if kon else SP)/2
        for i, (a, b) in enumerate(seg):
            a2, b2 = a + g, b - g
            owner, other, axo, axx = (ka, kb, ax, axb) if i % 2 == 0 else (kb, ka, axb, ax)
            K = axo.knoechel(a2, b2, R, kon)
            if typ == "flach":            # auf dem Bett abschneiden (Bettflaeche des Besitzers)
                fi = 2 if owner % 2 == 0 else 0
                n, d = pl[owner][fi]
                K = K ^ halbraum(n, d, P[owner].mean(0))
            add[owner].append(K)
            sub[other].append(axx.freiraum(a2, b2, R, SP, kon))
            top = b2 + (R if kon else 0)
            frei = axx.zyl(a2 - SP, top + SP, RF)
            if kon: frei = frei + axx.kegel(top + SP - 0.02, RF, RF)     # 45-Grad-Decke statt waagrechtem Ueberhang
            sub[other].append(frei)
        # Enden: beide freistellen
        for k_, axk in ((ka, ax), (kb, axb)):
            sub[k_].append(axk.zyl(-3, U0 + g, RF)); sub[k_].append(axk.zyl(U1 - g, 38, RF))
        # Bolzen / Bohrung
        if typ == "offen":
            bohr[ka].append(ax.zyl(-3, 38, FIL, 24)); bohr[kb].append(axb.zyl(-3, 38, FIL, 24))
        else:
            add[ka].append(ax.zyl(U0 + 0.8, U1 - 0.8, PIN, 24))
            bohr[kb].append(axb.zyl(-3, 38, PIN + SP, 24))
    out = []
    for k in range(6):
        M = body[k]
        if sub[k]: M = M - m3.Manifold.batch_boolean(sub[k], m3.OpType.Add)
        if add[k]: M = M + m3.Manifold.batch_boolean(add[k], m3.OpType.Add)
        if bohr[k]: M = M - m3.Manifold.batch_boolean(bohr[k], m3.OpType.Add)
        comps = sorted(M.decompose(), key=lambda c: -c.volume())
        out.append(comps[0])
    return out, body, pl

def halbraum(n, d, innen_pt, gross=400):
    """Halbraum n.x <= d als grosser Quader"""
    t = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(n, t); e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
    o = n*d
    pts = [o + s1*gross*e1 + s2*gross*e2 + s3*gross*n for s1 in (-1, 1) for s2 in (-1, 1) for s3 in (-1, 0)]
    return hull(pts)

if __name__ == "__main__":
    import time
    t = time.time(); lok = G.glieder_lokal(0.5)
    T, B, pl = teile(lok)
    for k, M in enumerate(T): print(k, "Vol", round(M.volume()), "Teile", len(M.decompose()))
    print("Zeit", round(time.time() - t, 1))

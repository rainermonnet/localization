"""Wuerfelguertel v5: sechs Einzelglieder mit angeformten Gelenken, ohne Kleber, Achse = Drahtstift 2 x 35 mm.
Alle Glieder liegen beim Druck auf F3 (Aussenflaeche). Je Gelenk j (Kante c_j -> H_j):
  Glied j-1 (Endkante, liegt flach auf dem Bett): WALZE u in [UB0, UB1], Bohrung fuer Presssitz des Stifts
  Glied j   (Startkante, steht senkrecht):        LAGER-Saeule vom Bett bis u = UE1, Spielbohrung, unten Senkung fuer den Stiftkopf
Keine Ueberhaenge: die Walze liegt auf dem Bett, die Saeule waechst vom Bett nach oben, die Nut ueber der Saeule ist nach oben offen."""
import numpy as np, manifold3d as m3
import guertel as G
from einteilig import Achse, ebenen, hull, halbraum

A_MM = 70.0
AUSSEN = 2.6      # Aussenflaechen F1, F3 nach aussen (Achse der liegenden Walze 2,6 mm ueber dem Bett)
INNEN = 0.6
R = 3.0           # Radius von Walze und Lager-Saeule
RF = 5.8          # Freistich um die Achse im jeweils anderen Glied
SP = 0.5          # axiales Spiel zwischen Saeule und Walze
UE1 = 15.0        # Saeule endet hier
UB0, UB1 = UE1 + SP, 33.5   # Walze
STIFT_PRESS = 1.0   # Bohrungsradius Walze (Stift 2,0 -> Presssitz, waagrecht gedruckte Bohrung faellt etwas kleiner aus)
STIFT_SPIEL = 1.15  # Bohrungsradius Saeule (2,3 mm, senkrecht gedruckt)
KOPF_R, KOPF_T = 2.4, 1.4   # Senkung fuer den Kopf (Drahtstift-Kopf ca. 4,0-4,4 mm)

def koerper(P):
    off = [-AUSSEN, INNEN, -AUSSEN, INNEN]
    pl = ebenen(P, off); V = []
    for v in range(4):
        fs = [j for j, f in enumerate(G.FACES) if v in f]
        V.append(np.linalg.solve(np.array([pl[j][0] for j in fs]), np.array([pl[j][1] for j in fs])))
    return hull(V), np.array(V), pl

def tropfen(ax, a, b, r, n=48):
    """waagrechter Kanal mit 45-Grad-Dach (Tropfenform) - Dachspitze zeigt in Richtung 'oben' (Normale weg vom Bett)"""
    return ax.zyl(a, b, r, n)

def teile(lok, mit_stift=False):
    P = [l*A_MM for l in lok]
    out = []; info = []
    for k in range(6):
        body, V, pl = koerper(P[k]); cen = P[k].mean(0)
        n3, d3 = pl[2]                          # Bettflaeche F3 (aussen, versetzt)
        bett = halbraum(n3, d3, cen)            # Halbraum oberhalb des Betts (innen)
        axE = Achse(P[k][2], P[k][3])           # Endkante: Walze (liegt auf dem Bett)
        axS = Achse(P[k][0], P[k][1])           # Startkante: Lager-Saeule (steht senkrecht)
        sub = []; add = []; bohr = []
        # --- Endkante (Glied k ist 'A'): Walze, Freistich fuer die Saeule des Nachfolgers
        add.append(axE.zyl(UB0, UB1, R) ^ bett)
        sub.append(axE.zyl(-8, UE1 + SP, RF))                    # Kanal fuer die Saeule (liegt am Bett)
        sub.append(axE.zyl(UB1, 40, RF))                         # Spitze H frei
        # Dach des Kanals als 45-Grad-Prisma (statt Halbkreis-Bogen): Huelle aus Kreis und Firstlinie
        up = -n3                                                  # 'oben' im Druck
        w = up - (up @ axE.ex)*axE.ex; w /= np.linalg.norm(w)
        first = [axE.c + u*axE.ex + w*RF*np.sqrt(2) for u in (-8, UE1 + SP)]
        sub.append(hull(axE.ring(-8, RF) + axE.ring(UE1 + SP, RF) + first))
        bohr.append(axE.zyl(UB0 - 1, UB1 + 1, STIFT_PRESS, 24))
        # --- Startkante (Glied k ist 'B'): Saeule vom Bett bis UE1, Nut darueber nach oben offen
        add.append(axS.zyl(-8, UE1, R) ^ bett)
        sub.append(axS.zyl(UE1, 40, RF))
        bohr.append(axS.zyl(-8, UE1 + 1, STIFT_SPIEL, 24))
        bohr.append(axS.zyl(-8, -AUSSEN + KOPF_T, KOPF_R, 32))   # Senkung fuer den Kopf (von der Bettseite)
        M = body - m3.Manifold.batch_boolean(sub, m3.OpType.Add)
        M = M + m3.Manifold.batch_boolean(add, m3.OpType.Add)
        M = M - m3.Manifold.batch_boolean(bohr, m3.OpType.Add)
        comps = sorted(M.decompose(), key=lambda c: -c.volume())
        M = comps[0]
        if mit_stift:   # Stift (sitzt fest in der Walze dieses Glieds) inkl. Kopf - fuer die Kollisionspruefung
            # der Stift laeuft vom Kopf (in der Saeule des NACHFOLGERS) durch die Walze; Lage im eigenen Rahmen
            s = axE.zyl(-AUSSEN + 0.05, UB1 - 0.5, 1.0, 24) + axE.zyl(-AUSSEN + 0.05, -AUSSEN + KOPF_T - 0.3, 2.15, 32)
            M = M + s
        out.append(M); info.append(len(comps))
    return out, info

if __name__ == "__main__":
    lok = G.glieder_lokal(0.5)
    T, info = teile(lok)
    for k, M in enumerate(T): print(k, "Vol", round(M.volume()), "Komponenten vorher", info[k])

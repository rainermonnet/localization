import numpy as np, ring, guertel as G, einteilig as E, einteilig_lage as L
D2, D4 = np.radians(12), np.radians(24)
T, _, _ = E.teile(L.lok); M = L.kette(D2, D4)
W = [T[k].transform(M[k][:3, :]) for k in range(6)]
print("Drucklage: max. Ueberschneidung", max((W[a] ^ W[b]).volume() for a in range(6) for b in range(a + 1, 6)))
K = np.array(ring.kurve(G.PHI))
def winkel(R): return np.degrees(np.arctan2(R[1, 0], R[0, 0])) % 360
for k in range(5):
    j = k + 1
    rp = np.linalg.inv(M[k]) @ M[j]; tp = winkel(rp @ np.linalg.inv(L.REL[k]))
    work = []
    for i in range(0, len(K), 7):
        F = G.rahmen(*K[i]); rel = L.skal(np.linalg.inv(F[(k + 1) % 6]) @ F[(k + 2) % 6]); work.append(winkel(rel @ np.linalg.inv(L.REL[k])))
    frei = []
    for t in np.arange(0, 360, 1.0):
        Mj = L.Rz(np.radians(t)) @ L.REL[k]
        frei.append((T[k] ^ T[j].transform(Mj[:3, :])).volume() < 1e-3)
    frei = np.array(frei)
    # zusammenhaengender freier Bogen um tp
    def bogen(t0):
        i0 = int(round(t0)) % 360
        if not frei[i0]: return None
        lo = i0; hi = i0
        while frei[(lo - 1) % 360] and (i0 - lo) < 360: lo -= 1
        while frei[(hi + 1) % 360] and (hi - i0) < 360: hi += 1
        return lo, hi
    b = bogen(tp)
    inb = lambda w: b is not None and any(b[0] <= w + 360*m <= b[1] for m in (-1, 0, 1))
    print(f"Gelenk {j} ({E.gelenk_typ(j)}): Druckwinkel {tp:.1f}, freier Bogen {b}, Arbeitsbereich {min(work):.0f}..{max(work):.0f}, alle erreichbar: {all(inb(w) for w in work)}, frei gesamt {frei.sum()} Grad")

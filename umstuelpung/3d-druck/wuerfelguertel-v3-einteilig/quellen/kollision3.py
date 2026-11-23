import numpy as np, ring, guertel as G, einteilig as E, sys, time
lok = G.glieder_lokal(0.5); T, _, _ = E.teile(lok)
K = np.array(ring.kurve(G.PHI)); step = int(sys.argv[1]) if len(sys.argv) > 1 else 10
worst = {}; t = time.time()
for i in range(0, len(K), step):
    F = G.rahmen(*K[i]); W = []
    for k in range(6):
        M = F[(k + 1) % 6].copy(); M[:3, 3] *= E.A_MM; W.append(T[k].transform(M[:3, :]))
    for a in range(6):
        for b in range(a + 1, 6):
            v = (W[a] ^ W[b]).volume()
            if v > worst.get((a, b), (0, 0))[0]: worst[(a, b)] = (v, i)
print("Zeit", round(time.time() - t, 1), {k: (round(v[0], 3), v[1]) for k, v in worst.items()} or "keine Ueberschneidung")

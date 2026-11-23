"""Ueberhangpruefung: Dreiecke, deren Normale mehr als 45 Grad nach unten zeigt (oberhalb der ersten Schicht),
und 'Inseln': Material, das in einer Schicht ohne Verbindung zur Schicht darunter beginnt."""
import numpy as np, manifold3d as m3, trimesh
def pruefe(M, name, schicht=0.24):
    me = M.to_mesh(); V = np.asarray(me.vert_properties)[:, :3]; T = np.asarray(me.tri_verts); tri = V[T]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); a = np.linalg.norm(n, axis=1)/2; nz = n[:, 2]/(2*a + 1e-12)
    zc = tri[:, :, 2].mean(1)
    schlecht = (nz < -0.75) & (zc > 0.3)          # steiler als ~41 Grad Ueberhang
    flach = (nz < -0.98) & (zc > 0.3)              # waagrecht nach unten
    # Inseln: Schnitt je Schicht, jede Flaeche muss die Schicht darunter beruehren
    tm = trimesh.Trimesh(V, T, process=False); inseln = []
    zs = np.arange(schicht*0.5, V[:, 2].max(), schicht)
    prev = None
    for z in zs:
        sec = tm.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if sec is None: prev = None; continue
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        loops = [Polygon(l[:, :2]).buffer(0) for l in sec.discrete if len(l) > 3]
        # gerade/ungerade Verschachtelung -> symmetrische Differenz ergibt die Flaechen
        G_ = None
        for L in loops: G_ = L if G_ is None else G_.symmetric_difference(L)
        polys = [] if G_ is None else (list(G_.geoms) if hasattr(G_, 'geoms') else [G_])
        if prev is not None:
            from shapely.ops import unary_union
            U = unary_union(prev).buffer(schicht)          # 45 Grad Reichweite
            for p in polys:
                if p.area > 0.5 and not p.intersects(unary_union(prev)):
                    inseln.append((round(z, 2), round(p.area, 1)))
        prev = polys
    print(f"{name}: Ueberhang >41 Grad {a[schlecht].sum():.1f} mm2 (davon waagrecht {a[flach].sum():.1f} mm2), schwebende Inseln: {inseln[:8]}")
    return a[schlecht].sum(), inseln

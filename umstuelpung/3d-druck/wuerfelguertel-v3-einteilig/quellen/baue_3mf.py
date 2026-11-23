"""Bambu-Studio-Projekt (3MF) fuer den einteiligen Wuerfelguertel mit schnellen Einstellungen."""
import json, zipfile, uuid, sys, struct, numpy as np
from PIL import Image
SRC = "ori3mf"                      # nur Drucker-/Prozess-Konfiguration der Vorlage (Bambu-Systemprofil) wird benutzt
STL, OUT, BILD, FARBE, NAME = sys.argv[1:6]
d = open(STL, 'rb').read(); n = struct.unpack('<I', d[80:84])[0]
tri = np.frombuffer(d[84:], dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]), count=n)['v'].reshape(-1, 3).astype(np.float64)
V, inv = np.unique(np.round(tri, 5), axis=0, return_inverse=True); T = inv.reshape(-1, 3)
lo, hi = V.min(0), V.max(0); c = (lo + hi)/2; V = V - c; h = hi[2] - lo[2]
verts = "\n".join(f'     <vertex x="{x:.5f}" y="{y:.5f}" z="{z:.5f}"/>' for x, y, z in V)
tris = "\n".join(f'     <triangle v1="{a}" v2="{b}" v3="{e}"/>' for a, b, e in T)
U = lambda: str(uuid.uuid4())
obj = f'''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <resources>
  <object id="1" p:UUID="{U()}" type="model">
   <mesh>
    <vertices>
{verts}
    </vertices>
    <triangles>
{tris}
    </triangles>
   </mesh>
  </object>
 </resources>
 <build/>
</model>'''
haupt = f'''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="Application">BambuStudio-02.09.01.70</metadata>
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <metadata name="Title">{NAME}</metadata>
 <metadata name="Description">Umstuelpbarer Wuerfelguertel nach Paul Schatz, einteilig als Print-in-Place gedruckt. Gelenkspiel 0,5 mm.</metadata>
 <resources>
  <object id="2" p:UUID="{U()}" type="model">
   <components>
    <component p:path="/3D/Objects/object_1.model" objectid="1" p:UUID="{U()}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>
   </components>
  </object>
 </resources>
 <build p:UUID="{U()}">
  <item objectid="2" p:UUID="{U()}" transform="1 0 0 0 1 0 0 0 1 128 128 {h/2:.5f}" printable="1"/>
 </build>
</model>'''
ms = f'''<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="2">
    <metadata key="name" value="{NAME}"/>
    <metadata key="extruder" value="1"/>
    <metadata face_count="{len(T)}"/>
    <part id="1" subtype="normal_part">
      <metadata key="name" value="{NAME}"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <mesh_stat face_count="{len(T)}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>
    </part>
  </object>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value=""/>
    <metadata key="locked" value="false"/>
    <metadata key="thumbnail_file" value="Metadata/plate_1.png"/>
    <model_instance>
      <metadata key="object_id" value="2"/>
      <metadata key="instance_id" value="0"/>
      <metadata key="identify_id" value="101"/>
    </model_instance>
  </plate>
  <assemble>
   <assemble_item object_id="2" instance_id="0" transform="1 0 0 0 1 0 0 0 1 128 128 {h/2:.5f}" offset="0 0 0" />
  </assemble>
</config>'''
cfg = json.load(open(f"{SRC}/Metadata/project_settings.config"))
neu = {"layer_height": "0.24", "top_shell_layers": "4", "bottom_shell_layers": "3", "top_shell_thickness": "0.8",
       "wall_loops": "2", "sparse_infill_density": "10%", "sparse_infill_pattern": "lightning",
       "brim_type": "outer_only", "brim_width": "5", "elefant_foot_compensation": "0.15", "enable_support": "0"}
for k, v in neu.items():
    assert k in cfg, k; cfg[k] = v
cfg["filament_colour"] = [FARBE]
cfg["different_settings_to_system"][0] = ";".join(sorted(set(cfg["different_settings_to_system"][0].split(";")) | set(neu)))
img = Image.open(BILD).convert("RGB")
def png(size):
    im = img.copy(); im.thumbnail((size, size)); bg = Image.new("RGB", (size, size), "white"); bg.paste(im, ((size - im.width)//2, (size - im.height)//2))
    import io; b = io.BytesIO(); bg.save(b, "PNG"); return b.getvalue()
rels = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
 <Relationship Target="/Metadata/plate_1.png" Id="rel-4" Type="http://schemas.bambulab.com/package/2021/cover-thumbnail-middle"/>
 <Relationship Target="/Metadata/plate_1_small.png" Id="rel-5" Type="http://schemas.bambulab.com/package/2021/cover-thumbnail-small"/>
</Relationships>'''
mrels = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/Objects/object_1.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>'''
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", open(f"{SRC}/[Content_Types].xml").read())
    z.writestr("_rels/.rels", rels)
    z.writestr("3D/3dmodel.model", haupt)
    z.writestr("3D/_rels/3dmodel.model.rels", mrels)
    z.writestr("3D/Objects/object_1.model", obj)
    z.writestr("Metadata/project_settings.config", json.dumps(cfg, indent=4))
    z.writestr("Metadata/model_settings.config", ms)
    z.writestr("Metadata/slice_info.config", open(f"{SRC}/Metadata/slice_info.config").read())
    z.writestr("Metadata/custom_gcode_per_layer.xml", open(f"{SRC}/Metadata/custom_gcode_per_layer.xml").read())
    z.writestr("Metadata/plate_1.png", png(512)); z.writestr("Metadata/plate_1_small.png", png(128))
print(OUT, "Dreiecke", len(T), "Punkte", len(V), "Hoehe", round(h, 2))

"""Zweifarbiges Bambu-Projekt: ein Objekt aus zwei Teilen (weiss = Filament 1, Holz = Filament 2)."""
import json, zipfile, uuid, sys, struct, io, numpy as np
from PIL import Image
SRC = "ori3mf"
STL1, STL2, OUT, BILD = sys.argv[1:5]
def lese(fn):
    d = open(fn, 'rb').read(); n = struct.unpack('<I', d[80:84])[0]
    tri = np.frombuffer(d[84:], dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]), count=n)['v'].reshape(-1, 3).astype(np.float64)
    V, inv = np.unique(np.round(tri, 5), axis=0, return_inverse=True); return V, inv.reshape(-1, 3)
M = [lese(STL1), lese(STL2)]
allV = np.vstack([m[0] for m in M]); lo, hi = allV.min(0), allV.max(0); c = (lo + hi)/2; h = hi[2] - lo[2]
U = lambda: str(uuid.uuid4())
def mesh_xml(oid, V, T):
    V = V - c
    return (f'  <object id="{oid}" p:UUID="{U()}" type="model">\n   <mesh>\n    <vertices>\n' +
            "\n".join(f'     <vertex x="{x:.5f}" y="{y:.5f}" z="{z:.5f}"/>' for x, y, z in V) +
            '\n    </vertices>\n    <triangles>\n' + "\n".join(f'     <triangle v1="{a}" v2="{b}" v3="{e}"/>' for a, b, e in T) +
            '\n    </triangles>\n   </mesh>\n  </object>')
kopf = '<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">\n'
obj = kopf + ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n' + mesh_xml(1, *M[0]) + "\n" + mesh_xml(2, *M[1]) + '\n </resources>\n <build/>\n</model>'
haupt = kopf + f''' <metadata name="Application">BambuStudio-02.09.01.70</metadata>
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <metadata name="Title">Wuerfelguertel einteilig weiss-Holz</metadata>
 <resources>
  <object id="3" p:UUID="{U()}" type="model">
   <components>
    <component p:path="/3D/Objects/object_1.model" objectid="1" p:UUID="{U()}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>
    <component p:path="/3D/Objects/object_1.model" objectid="2" p:UUID="{U()}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>
   </components>
  </object>
 </resources>
 <build p:UUID="{U()}">
  <item objectid="3" p:UUID="{U()}" transform="1 0 0 0 1 0 0 0 1 128 128 {h/2:.5f}" printable="1"/>
 </build>
</model>'''
ms = f'''<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="3">
    <metadata key="name" value="Wuerfelguertel weiss-Holz"/>
    <metadata key="extruder" value="1"/>
    <part id="1" subtype="normal_part">
      <metadata key="name" value="Glieder 1-3-5 weiss"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="extruder" value="1"/>
    </part>
    <part id="2" subtype="normal_part">
      <metadata key="name" value="Glieder 2-4-6 Holz"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="extruder" value="2"/>
    </part>
  </object>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value=""/>
    <metadata key="locked" value="false"/>
    <metadata key="thumbnail_file" value="Metadata/plate_1.png"/>
    <model_instance>
      <metadata key="object_id" value="3"/>
      <metadata key="instance_id" value="0"/>
      <metadata key="identify_id" value="101"/>
    </model_instance>
  </plate>
  <assemble>
   <assemble_item object_id="3" instance_id="0" transform="1 0 0 0 1 0 0 0 1 128 128 {h/2:.5f}" offset="0 0 0" />
  </assemble>
</config>'''
cfg = json.load(open(f"{SRC}/Metadata/project_settings.config"))
neu = {"layer_height": "0.24", "top_shell_layers": "4", "bottom_shell_layers": "3", "top_shell_thickness": "0.8",
       "wall_loops": "2", "sparse_infill_density": "10%", "sparse_infill_pattern": "lightning",
       "brim_type": "outer_only", "brim_width": "5", "elefant_foot_compensation": "0.15", "enable_support": "0",
       "enable_prime_tower": "1", "flush_into_infill": "1"}
for k, v in neu.items(): assert k in cfg, k; cfg[k] = v
# Filament-Einstellungen auf 2 Filamente erweitern (Wert von Filament 1 uebernehmen)
PRO_FILAMENT = {"activate_air_filtration", "additional_cooling_fan_speed", "chamber_temperatures", "close_fan_the_first_x_layers",
    "complete_print_exhaust_fan_speed", "cool_plate_temp", "cool_plate_temp_initial_layer", "during_print_exhaust_fan_speed",
    "eng_plate_temp", "eng_plate_temp_initial_layer", "fan_cooling_layer_time", "fan_max_speed", "fan_min_speed",
    "full_fan_speed_layer", "hot_plate_temp", "hot_plate_temp_initial_layer", "nozzle_temperature", "nozzle_temperature_initial_layer",
    "nozzle_temperature_range_high", "nozzle_temperature_range_low", "overhang_fan_speed", "overhang_fan_threshold",
    "reduce_fan_stop_start_freq", "required_nozzle_HRC", "slow_down_for_layer_cooling", "slow_down_layer_time", "slow_down_min_speed",
    "supertack_plate_temp", "supertack_plate_temp_initial_layer", "temperature_vitrification", "textured_plate_temp",
    "textured_plate_temp_initial_layer", "default_filament_colour", "enable_pressure_advance", "pressure_advance",
    "dont_slow_down_outer_wall", "impact_strength_z", "volumetric_speed_coefficients", "enable_overhang_bridge_fan",
    "close_additional_fan_first_x_layers", "first_x_layer_fan_speed", "additional_fan_full_speed_layer", "ironing_fan_speed",
    "nozzle_volume_type", "filament_map", "filament_ids"}
erweitert = []
for k, v in cfg.items():
    if isinstance(v, list) and len(v) == 1 and (k.startswith("filament_") or k in PRO_FILAMENT):
        cfg[k] = v*2; erweitert.append(k)
cfg["filament_colour"] = ["#FFFFFF", "#B8875A"]
cfg["filament_map"] = ["1", "1"]
cfg["flush_volumes_matrix"] = ["0", "250", "450", "0"]       # weiss->Holz 250 mm3, Holz->weiss 450 mm3
cfg["flush_volumes_vector"] = ["140", "140", "140", "140"]
cfg["different_settings_to_system"][0] = ";".join(sorted(set(filter(None, cfg["different_settings_to_system"][0].split(";"))) | set(neu)))
img = Image.open(BILD).convert("RGB")
def png(size):
    im = img.copy(); im.thumbnail((size, size)); bg = Image.new("RGB", (size, size), "white"); bg.paste(im, ((size - im.width)//2, (size - im.height)//2))
    b = io.BytesIO(); bg.save(b, "PNG"); return b.getvalue()
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
    z.writestr("_rels/.rels", rels); z.writestr("3D/3dmodel.model", haupt)
    z.writestr("3D/_rels/3dmodel.model.rels", mrels); z.writestr("3D/Objects/object_1.model", obj)
    z.writestr("Metadata/project_settings.config", json.dumps(cfg, indent=4))
    z.writestr("Metadata/model_settings.config", ms)
    z.writestr("Metadata/slice_info.config", open(f"{SRC}/Metadata/slice_info.config").read())
    z.writestr("Metadata/custom_gcode_per_layer.xml", open(f"{SRC}/Metadata/custom_gcode_per_layer.xml").read())
    z.writestr("Metadata/plate_1.png", png(512)); z.writestr("Metadata/plate_1_small.png", png(128))
print(OUT, "erweitert:", len(erweitert), "Schluessel; Hoehe", round(h, 2))

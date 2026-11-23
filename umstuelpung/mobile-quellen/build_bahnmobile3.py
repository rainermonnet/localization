import os
HIER = os.path.dirname(os.path.abspath(__file__))
THREE = open(os.path.join(HIER, "npm/package/build/three.min.js"), encoding="utf-8").read().replace("</script", "<\\/script")
DATEN = open(os.path.join(HIER, "bahnen_daten.json")).read()
PLAN = open(os.path.join(HIER, "plan2.json")).read()
H = open(os.path.join(HIER, "build_bahnmobile3_tmpl.html"), encoding="utf-8").read()
out = os.path.join(HIER, "bahn-mobile-3.html")
open(out, "w", encoding="utf-8").write(H.replace("__THREE__", THREE).replace("__DATEN__", DATEN).replace("__PLAN__", PLAN))
print("bahn-mobile-3.html", os.path.getsize(out)//1024, "KB")

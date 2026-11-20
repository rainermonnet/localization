import os
HIER = os.path.dirname(os.path.abspath(__file__))
THREE = open(os.path.join(HIER, "npm/package/build/three.min.js"), encoding="utf-8").read().replace("</script", "<\\/script")
DATEN = open(os.path.join(HIER, "guertel_daten.json")).read()
HTML = r'''<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<title>Würfelgürtel zum Umstülpen</title>
<style>
:root{--bg:#FBF7F1;--fg:#2b2620;--mut:#6b655b;--line:#8a8272;--acc:#C98A1D;--card:#F4F1EA;--panel:rgba(244,241,234,.94)}
@media (prefers-color-scheme:dark){:root{--bg:#1c1a16;--fg:#ece6d8;--mut:#a79f8e;--line:#6b6455;--acc:#F2B24E;--card:#2a2722;--panel:rgba(28,26,22,.92)}}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%;background:var(--bg);color:var(--fg);font:15px/1.45 Georgia,"Times New Roman",serif;overflow:hidden}
#cv{position:absolute;inset:0;width:100%;height:100%;display:block;touch-action:none}
#titel{position:absolute;left:max(16px,env(safe-area-inset-left));top:12px;right:16px;pointer-events:none}
#titel h1{font-size:20px;margin:0;font-weight:600}
#titel p{margin:3px 0 0;font-size:13px;color:var(--mut);max-width:60ch}
#panel{position:absolute;left:50%;transform:translateX(-50%);bottom:max(10px,env(safe-area-inset-bottom));background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:8px 12px;display:flex;gap:6px;flex-wrap:wrap;justify-content:center;align-items:center;max-width:calc(100vw - 20px)}
#panel button{border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:18px;padding:6px 12px;cursor:pointer;min-height:36px;font:inherit;font-size:14px;touch-action:manipulation}
#panel button[aria-pressed="true"]{border-color:var(--acc);box-shadow:inset 0 0 0 1px var(--acc)}
#phase{width:min(260px,60vw);accent-color:var(--acc)}
#info{position:absolute;right:max(14px,env(safe-area-inset-right));top:70px;width:min(330px,42vw);background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:8px 12px;font-size:12.5px;line-height:1.45;max-height:calc(100vh - 170px);overflow:auto}
#info summary{cursor:pointer;font-weight:600}#info ul{margin:6px 0 0;padding-left:1.1em}
#stand{font-size:12px;color:var(--mut);min-width:9ch;text-align:center}
@media (max-width:760px){#titel p{display:none}#info{top:auto;bottom:118px;right:10px;left:10px;width:auto;max-height:34vh}}
</style></head><body>
<canvas id="cv"></canvas>
<div id="titel"><h1>Würfelgürtel zum Umstülpen</h1><p>Nimmt man aus dem Würfel die beiden Sterne heraus, bleibt ein Gürtel aus sechs Tetraedern, die an Gelenkkanten zusammenhängen. Er lässt sich endlos umstülpen. Hält man ein Glied fest, überstreicht die Diagonale zwischen den beiden Nachbarecken den Oloid.</p></div>
<details id="info" open><summary>Was man sieht, und wie man ihn druckt</summary><ul>
<li><b>Gelenkkanten</b> (rot): die halben Würfelkanten an den Enden einer Raumdiagonale. Jedes Glied ist ein Tetraeder mit zwei solchen Kanten; Nachbarglieder teilen sich eine.</li>
<li><b>Sterne</b>: die beiden weggenommenen Teile, je 3/8 des Würfels. Der Gürtel ist 1/4 des Würfels; mit längeren Gelenkkanten stoßen die Glieder beim Umstülpen zusammen (nachgerechnet).</li>
<li><b>Ein Glied festhalten</b>: dann laufen die beiden Nachbarecken auf zwei Kreisbögen von 240°, und ihre Verbindung (konstant √3 · Kante) überstreicht den Oloid.</li>
<li><b>Druck</b>: sechs Glieder (Würfelkante 60 mm), je auf der langen Kante stehend; Bohrung 2 mm für Bolzen aus 1,75-mm-Filament (6 × 23 mm). Knöchel mit 0,5 mm Spiel; die Glieder durchlaufen die ganze Umstülpung ohne Berührung (nachgerechnet).</li></ul></details>
<div id="panel">
<button type="button" id="spiel" aria-pressed="true">⏸ Pause</button>
<input type="range" id="phase" min="0" max="479" value="0" aria-label="Stellung">
<span id="stand">Würfel</span>
<button type="button" id="mfrei" aria-pressed="true">Gürtel frei</button>
<button type="button" id="mfest" aria-pressed="false">Ein Glied fest</button>
<button type="button" id="toloid" aria-pressed="true">Oloid (bei festem Glied)</button>
<button type="button" id="tkant" aria-pressed="true">Gelenkkanten</button>
<button type="button" id="tstern" aria-pressed="true">Sterne</button>
<button type="button" id="tlang">langsam</button>
</div>
<script>__THREE__</script>
<script>
const D = __DATEN__;
const $ = id => document.getElementById(id);
const cv = $('cv'); let renderer; try { renderer = new THREE.WebGLRenderer({canvas: cv, antialias: true, alpha: true}); renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2)); } catch (e) {}
const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(30, 1, 1, 5000);
scene.add(new THREE.AmbientLight(0xffffff, 1.5)); const L1 = new THREE.DirectionalLight(0xffffff, 1.6); L1.position.set(200, 300, 260); scene.add(L1);
const L2 = new THREE.DirectionalLight(0xeaf2ff, .6); L2.position.set(-250, -120, -200); scene.add(L2);
const FARB = [0xE98A3A, 0xF2C46B, 0xE98A3A, 0xF2C46B, 0xE98A3A, 0xF2C46B];
function geo(v, f) { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(v, 3)); g.setIndex(f); g.computeVertexNormals(); return g; }
const glieder = D.glieder.map((G, k) => {
  const grp = new THREE.Group(); grp.matrixAutoUpdate = false; scene.add(grp);
  const m = new THREE.Mesh(geo(G.v, G.f).toNonIndexed(), new THREE.MeshStandardMaterial({color: FARB[k], roughness: .75, metalness: 0, flatShading: true}));
  m.geometry.computeVertexNormals(); grp.add(m);
  const kanten = new THREE.Group(); grp.add(kanten);
  G.achsen.forEach(([p, q]) => { const a = new THREE.Vector3(...p), b = new THREE.Vector3(...q), len = a.distanceTo(b);
    const c = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 0.9, len, 10), new THREE.MeshStandardMaterial({color: 0xC0392B, roughness: .5}));
    c.position.copy(a).add(b).multiplyScalar(.5); c.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.clone().sub(a).normalize()); kanten.add(c); });
  return {grp, kanten};
});
// Oloid (im Rahmen von Glied 0)
const OL = D.oloid, n = D.n; const pos = []; 
for (let i = 0; i < n; i++) { const j = (i + 1) % n, a = OL[i][0], b = OL[i][1], c = OL[j][1], d = OL[j][0]; pos.push(...a, ...b, ...c, ...a, ...c, ...d); }
const olGeo = new THREE.BufferGeometry(); olGeo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); olGeo.computeVertexNormals();
const olMesh = new THREE.Mesh(olGeo, new THREE.MeshStandardMaterial({color: 0x4A7EBB, roughness: .6, side: THREE.DoubleSide, transparent: true, opacity: .55, depthWrite: false}));
const olGrp = new THREE.Group(); olGrp.matrixAutoUpdate = false; olGrp.add(olMesh); scene.add(olGrp);
const diag = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]), new THREE.LineBasicMaterial({color: 0x1d3f66}));
olGrp.add(diag); const pk = [0, 1].map(() => { const s = new THREE.Mesh(new THREE.SphereGeometry(2.2, 14, 10), new THREE.MeshStandardMaterial({color: 0x1d3f66})); olGrp.add(s); return s; });
let olBis = 0;
// Sterne
const sterne = D.sterne.map((S, i) => { const m = new THREE.Mesh(geo(S.v, S.f), new THREE.MeshStandardMaterial({color: i ? 0x9A5480 : 0x4A7EBB, roughness: .8, transparent: true, opacity: .3, depthWrite: false})); scene.add(m); return m; });
const st = {i: 0, spiel: true, modus: 'B', oloid: true, kant: true, stern: true, tempo: 30, yaw: 0.75, pitch: 0.45, zoom: 1};
const M4 = new THREE.Matrix4();
function setze(i) {
  const MM = D[st.modus][i];
  glieder.forEach((g, k) => { const a = MM[k]; M4.set(a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], a[8], a[9], a[10], a[11], 0, 0, 0, 1); g.grp.matrix.copy(M4); g.grp.matrixWorldNeedsUpdate = true; g.kanten.visible = st.kant; });
  const a = MM[0]; M4.set(a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], a[8], a[9], a[10], a[11], 0, 0, 0, 1); olGrp.matrix.copy(M4); olGrp.matrixWorldNeedsUpdate = true;
  olBis = Math.max(olBis, i); olGeo.setDrawRange(0, 6 * olBis); olGrp.visible = st.oloid && st.modus === 'A';
  const p = OL[i]; diag.geometry.setFromPoints([new THREE.Vector3(...p[0]), new THREE.Vector3(...p[1])]); pk[0].position.set(...p[0]); pk[1].position.set(...p[1]);
  const nah = Math.min(i, n - i); sterne.forEach(s => { s.visible = st.stern && nah < 25; s.material.opacity = 0.32 * Math.max(0, 1 - nah / 25); });
  $('stand').textContent = nah < 3 ? 'Würfel' : Math.round(i / n * 360) + '°'; $('phase').value = i;
}
// Bedienung
const ptr = new Map(); let p0 = 0, z0 = 1; const pd = () => { const v = [...ptr.values()]; return Math.hypot(v[0][0] - v[1][0], v[0][1] - v[1][1]); };
cv.addEventListener('pointerdown', e => { ptr.set(e.pointerId, [e.clientX, e.clientY]); try { cv.setPointerCapture(e.pointerId); } catch (_) {} if (ptr.size === 2) { p0 = pd(); z0 = st.zoom; } });
cv.addEventListener('pointermove', e => { if (!ptr.has(e.pointerId)) return; const o = ptr.get(e.pointerId); ptr.set(e.pointerId, [e.clientX, e.clientY]);
  if (ptr.size === 1) { st.yaw -= (e.clientX - o[0]) * 0.007; st.pitch = Math.min(1.5, Math.max(-1.5, st.pitch + (e.clientY - o[1]) * 0.006)); }
  else if (ptr.size === 2) st.zoom = Math.min(3, Math.max(0.35, z0 * p0 / Math.max(1, pd()))); });
const los = e => ptr.delete(e.pointerId); cv.addEventListener('pointerup', los); cv.addEventListener('pointercancel', los);
cv.addEventListener('wheel', e => { e.preventDefault(); st.zoom = Math.min(3, Math.max(0.35, st.zoom * Math.exp(e.deltaY * .001))); }, {passive: false});
const knopf = (id, f) => $(id).onclick = f; const druck = (id, v) => $(id).setAttribute('aria-pressed', String(v));
knopf('spiel', () => { st.spiel = !st.spiel; $('spiel').textContent = st.spiel ? '⏸ Pause' : '▶ Abspielen'; druck('spiel', st.spiel); });
knopf('mfrei', () => { st.modus = 'B'; druck('mfrei', true); druck('mfest', false); setze(st.i); });
knopf('mfest', () => { st.modus = 'A'; olBis = st.i; druck('mfrei', false); druck('mfest', true); setze(st.i); });
knopf('toloid', () => { st.oloid = !st.oloid; druck('toloid', st.oloid); setze(st.i); });
knopf('tkant', () => { st.kant = !st.kant; druck('tkant', st.kant); setze(st.i); });
knopf('tstern', () => { st.stern = !st.stern; druck('tstern', st.stern); setze(st.i); });
knopf('tlang', () => { st.tempo = st.tempo === 30 ? 10 : 30; $('tlang').textContent = st.tempo === 30 ? 'langsam' : 'schneller'; });
$('phase').oninput = e => { st.i = +e.target.value; st.spiel = false; $('spiel').textContent = '▶ Abspielen'; druck('spiel', false); setze(st.i); };
const DRUCK = location.hash.startsWith('#druck'); if (DRUCK) { $('panel').style.display = 'none'; $('info').style.display = 'none'; $('titel').style.display = 'none'; }
function resize() { const w = innerWidth, h = innerHeight; if (renderer) renderer.setSize(w, h, false); camera.aspect = w / h; camera.setViewOffset(w, h, 0, DRUCK ? 0 : (w < 760 ? 70 : 30), w, h); camera.updateProjectionMatrix(); }
addEventListener('resize', resize); resize();
let last = 0, acc = 0;
function tick(ts) {
  const dt = Math.min(ts - last, 60) / 1000; last = ts;
  if (st.spiel) { acc += dt * st.tempo; while (acc >= 1) { acc -= 1; st.i = (st.i + 1) % n; } setze(st.i); }
  const t = Math.tan(camera.fov * Math.PI / 360), d = Math.max(230 / (2 * t * camera.aspect), 230 / (2 * t)) * st.zoom;
  camera.position.set(d * Math.cos(st.pitch) * Math.sin(st.yaw), d * Math.sin(st.pitch), d * Math.cos(st.pitch) * Math.cos(st.yaw)); camera.lookAt(0, 0, 0);
  if (renderer) renderer.render(scene, camera); requestAnimationFrame(tick);
}
setze(0); requestAnimationFrame(tick);
window.__stelle = (i, modus, oloidBis) => { st.spiel = false; if (modus) st.modus = modus; if (oloidBis !== undefined) olBis = oloidBis; st.i = i; setze(i); };
</script></body></html>'''
out = os.path.join(HIER, "wuerfelguertel.html")
open(out, "w", encoding="utf-8").write(HTML.replace("__THREE__", THREE).replace("__DATEN__", DATEN))
print("wuerfelguertel.html", os.path.getsize(out)//1024, "KB")

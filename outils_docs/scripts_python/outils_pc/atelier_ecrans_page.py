"""Page de l'atelier des ecrans (port 7960), servie par atelier_ecrans_web.py sur GET /.

Disposition : maquette `outils_docs/atelier_ecrans/modele-retenu.png` (spec 2026-11-11-atelier-ecrans-design.md § 5.5).
En-tete (cartes par lieu, ecrans du catalogue, etat de la carte, interface, theme), colonne gauche (pages, objets,
palette), centre (onglets « Ecran » / « Tableau des objets », zoom, grille, annuler, capture ; fichiers generes et leurs
differences), colonne droite (onglets « Proprietes » / « Liaison »). Bascule « Interface | display.ini » de l'en-tete :
l'onglet display.ini est dans atelier_ecrans_page_display.py.
Code : atelier_ecrans_page_js.py (etat, requetes, panneaux) et atelier_ecrans_page_canevas.py (dessin, glisser).
Le `<title>Atelier des écrans</title>` doit rester dans les 4096 premiers octets : build/cible_atelier_ecrans.py::repond
le lit pour savoir si la page tourne.
"""
from atelier_ecrans_page_canevas import JS as JS_CANEVAS
from atelier_ecrans_page_js import JS
from atelier_ecrans_page_remarques import JS as JS_REMARQUES
from atelier_ecrans_page_ecriture import JS as JS_ECRITURE
from atelier_ecrans_page_polices import HTML as HTML_POLICES, JS as JS_POLICES
from atelier_ecrans_page_display import CSS as CSS_DISPLAY, HTML as HTML_DISPLAY, JS as JS_DISPLAY
from atelier_ecrans_page_import import CSS as CSS_IMPORT, HTML as HTML_IMPORT, JS as JS_IMPORT
from atelier_ecrans_page_palier2 import CSS as CSS_PALIER2, JS as JS_PALIER2
from atelier_ecrans_page_icones import CSS as CSS_ICONES, JS as JS_ICONES
from atelier_ecrans_page_navigation import CSS as CSS_NAV, JS as JS_NAV
import lieux

CSS = """
:root{--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--bleu:#2563eb;--vert:#2a7d3f;--orange:#a35f00;
  --rouge:#b3261e;--piste:#e9e9ea;--bleu-fond:#eef3ff;--orange-fond:#fff4e0;--vert-fond:#e3f4e8;--champ:#fff;
  --console:#181818;--console-texte:#cccccc}
:root[data-theme="sombre"]{color-scheme:dark;--fond:#16191d;--carte:#20242a;--bord:#3a3f47;--texte:#e6e6e6;--doux:#a8adb5;
  --bleu:#6ea1ff;--vert:#5fd07e;--orange:#e7a64a;--rouge:#ff7b72;--piste:#2c3138;--bleu-fond:#1d2a44;--orange-fond:#3a2e18;
  --vert-fond:#1c3324;--champ:#2a2f36;--console:#0e0f11}
*{box-sizing:border-box}
body{margin:0;font:14px system-ui,sans-serif;color:var(--texte);background:var(--fond)}
header{display:flex;align-items:center;flex-wrap:wrap;gap:8px 12px;padding:10px 16px}
h1{font-size:20px;margin:0;white-space:nowrap} h2{font-size:15px;margin:0 0 8px}
h3{font-size:12px;margin:12px 0 5px;color:var(--doux);text-transform:uppercase;letter-spacing:.04em}
.doux{color:var(--doux)} .petit{font-size:12px}
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:10px;min-width:0}
.btn,.theme{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border:1px solid var(--bord);border-radius:6px;
  background:var(--champ);color:var(--texte);font:inherit;font-size:13px;white-space:nowrap;cursor:pointer}
.btn:disabled{opacity:.45;cursor:default} .btn.prim{background:var(--bleu);border-color:var(--bleu);color:#fff}
.btn.danger{color:var(--rouge)} .theme{margin-left:auto;border-radius:14px}
button:focus-visible,input:focus-visible,select:focus-visible,.palette div:focus-visible{outline:2px solid var(--bleu);outline-offset:2px}
.pastille{display:inline-block;white-space:nowrap;padding:1px 8px;border-radius:10px;font-size:12px;background:var(--piste);color:var(--doux)}
.pastille.ok{background:var(--vert-fond);color:var(--vert)} .pastille.bleu{background:var(--bleu-fond);color:var(--bleu)}
.pastille.or{background:var(--orange-fond);color:var(--orange)}
.ligne{display:flex;gap:8px;align-items:center;margin:4px 0;flex-wrap:wrap}
.etiq{width:84px;flex:none;color:var(--doux);font-size:12px}
input,select{font:inherit;font-size:13px;padding:3px 6px;border:1px solid var(--bord);border-radius:5px;background:var(--champ);
  color:var(--texte);min-width:0}
.ligne input:not([type=checkbox]):not([type=color]),.ligne select{flex:1}
input[type=color]{width:34px;height:26px;padding:1px;flex:none}
header select{max-width:340px}
.grille3{display:grid;grid-template-columns:240px minmax(0,1fr) 340px;gap:12px;padding:0 16px 16px}
@media (max-width:1100px){.grille3{grid-template-columns:1fr}}
.onglets{display:flex;gap:2px}
.onglets button{padding:4px 11px;border:1px solid var(--bord);border-bottom:none;border-radius:6px 6px 0 0;background:var(--piste);
  color:var(--texte);font:inherit;font-size:12px;cursor:pointer}
.onglets button.actif{background:var(--carte);font-weight:600}
.panneau{border:1px solid var(--bord);padding:8px;border-radius:0 6px 6px 6px}
.arbre div{font-size:13px;padding:2px 6px;border-radius:4px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.arbre div:hover{background:var(--piste)} .arbre .sel{background:var(--bleu-fond);color:var(--bleu);font-weight:600}
.arbre{max-height:300px;overflow:auto}
.palette div{padding:4px 8px;border:1px solid var(--bord);border-radius:6px;margin:3px 0;background:var(--champ);font-size:13px;
  display:flex;justify-content:space-between;cursor:grab}
.avert{background:var(--orange-fond);border-left:3px solid var(--orange);padding:5px 8px;font-size:12px;border-radius:4px;margin:6px 0;
  white-space:pre-wrap}
.code{background:var(--console);color:var(--console-texte);font:12px/1.45 Consolas,monospace;border-radius:6px;padding:8px 10px;
  margin:0;white-space:pre;overflow:auto;max-height:320px}
.code .p{color:#7ee787} .code .m{color:#ff7b72} .code .c{color:#8b9099}
table{border-collapse:collapse;width:100%;font-size:12.5px} th,td{border:1px solid var(--bord);padding:2px 4px;text-align:left}
th{background:var(--piste);font-weight:600} tr.sel td{background:var(--bleu-fond)}
td input{width:100%;border:none;background:transparent;padding:1px 2px} td.num input{width:56px}
#vueTableau{max-height:640px;overflow:auto}
/* ecran de la carte : coordonnees en pixels de l'ecran, mises a l'echelle par transform */
#vueEcran{overflow:auto;padding:8px}
.boite{position:relative;overflow:hidden;border-radius:4px;box-shadow:0 0 0 6px #222,0 0 0 7px #555;margin:6px}
.ecran{position:absolute;left:0;top:0;transform-origin:0 0;background:#000;color:#fff;overflow:hidden;touch-action:none}
.ecran.grille{background-image:linear-gradient(#ffffff14 1px,transparent 1px),linear-gradient(90deg,#ffffff14 1px,transparent 1px);
  background-size:8px 8px}
.ecran .o{position:absolute;white-space:pre;line-height:1.2;overflow:hidden;cursor:move;user-select:none}
.ecran .o.commun{pointer-events:none;opacity:.55}
.ecran .o.sel{outline:2px dashed #ffd84a;outline-offset:1px;overflow:visible;z-index:5}
.ecran .indic{position:absolute;left:0;top:0;bottom:0}
.ecran .poi{position:absolute;width:12px;height:12px;background:#ffd84a;border:2px solid #10161e;z-index:6}
.ecran .ligneDiv{position:absolute;left:0;right:0;height:1px}
.rq{border:1px solid var(--bord);border-radius:7px;padding:7px 9px;margin:6px 0;background:var(--champ);font-size:13px}
.rq .num{display:inline-block;min-width:20px;height:20px;border-radius:10px;background:var(--orange);color:#fff;text-align:center;
  font-size:12px;line-height:20px;margin-right:6px;padding:0 4px}
.rq.proposee .num{background:var(--bleu)} .rq.appliquee,.rq.refusee{opacity:.65} .rq.appliquee .num{background:var(--vert)}
.rq.refusee .num{background:var(--doux)} .rqTexte{margin:4px 0;white-space:pre-wrap} .rq ul{margin:2px 0 4px;padding-left:18px}
textarea{font:inherit;font-size:13px;padding:4px 6px;border:1px solid var(--bord);border-radius:5px;background:var(--champ);color:var(--texte)}
.ecran .epingle{position:absolute;width:30px;height:30px;border-radius:15px;background:#FFA53F;color:#10161e;font:700 16px/30px Arial;
  text-align:center;box-shadow:0 0 0 3px #10161e;pointer-events:none;z-index:7}
.ecran .epingle.proposee{background:#3FA7FF}
.ecran .zoneRq{position:absolute;border:2px dashed #FFA53F;border-radius:6px;pointer-events:none;z-index:7}
.ecran .zoneRq.neuve{border-color:#ffd84a}
#captureBoite img{max-width:100%;border:1px solid var(--bord);image-rendering:pixelated}
details pre{max-height:240px}
.fichiers{margin-top:10px}
"""

HTML = """
<header>
 <h1>Atelier des écrans</h1>
 <div class="onglets" id="modes"><button type="button" data-mode="interface" class="actif">Interface</button><button type="button" data-mode="display">display.ini</button></div>
 <label class="doux" for="carte">carte</label><select id="carte" style="font-weight:600"></select>
 <label class="doux" for="ecran">écran</label><select id="ecran"></select>
 <span id="etat" class="pastille">…</span><span id="interface" class="pastille bleu"></span><span id="pastilleRemarques" class="pastille or" hidden></span>
 <button id="theme" class="theme" type="button"></button>
</header>
<div style="padding:0 16px"><div id="bandeau" class="avert" hidden></div><div id="changement" class="ligne" hidden></div></div>
<div class="grille3" id="vueInterface">
 <div class="carte">
  <h2>Pages</h2><div id="pages" class="arbre"></div>
  <div class="ligne"><button id="ajoutPage" class="btn" type="button">+ page</button></div>""" + HTML_IMPORT + """
  <h3 id="titreObjets">Objets</h3><div id="objets" class="arbre"></div>
  <h3>Palette (catalogue du firmware)</h3>
  <div id="palette" class="palette"></div>
  <p class="doux petit">Glisser un objet sur l'écran, ou cliquer pour l'ajouter en haut à gauche.</p>
""" + HTML_POLICES + """
 </div>
 <div style="min-width:0">
  <div class="carte">
   <div class="ligne">
    <div class="onglets" id="vues"><button type="button" data-vue="ecran" class="actif">Écran</button><button type="button" data-vue="tableau">Tableau des objets</button></div>
    <button id="zoomMoins" class="btn" type="button" aria-label="Réduire">−</button><b id="zoom">100 %</b>
    <button id="zoomPlus" class="btn" type="button" aria-label="Agrandir">+</button><button id="zoom100" class="btn" type="button">100 %</button>
    <label class="btn"><input type="checkbox" id="grille" checked> Grille 8 px</label>
    <button id="annuler" class="btn" type="button" title="Ctrl+Z">Annuler</button><button id="retablir" class="btn" type="button" title="Ctrl+Y">Rétablir</button>
    <span id="coords" class="doux petit" style="margin-left:auto"></span>
   </div>
   <div id="vueEcran"><div id="cadre" class="boite"><div id="ecranCarte" class="ecran grille"></div></div></div>
   <div id="vueTableau" hidden><table id="tableau"></table><div id="refusTableau" class="avert" hidden></div></div>
   <div class="ligne">
    <button id="relire" class="btn" type="button">Relire la carte</button>
    <button id="capture" class="btn" type="button">Capture de la carte</button><span id="captureEtat" class="doux petit"></span>
   </div>
   <p class="doux petit">Le dessin utilise les valeurs d'exemple du modèle de l'écran ; les valeurs lues sur la carte sont
   montrées brutes ci-dessous (leur conversion vers le modèle est faite par le Berry de la carte).</p>
   <details id="sensorBoite" hidden><summary>Valeurs lues sur la carte (JSON SENSOR)</summary><pre id="sensor" class="code"></pre></details>
   <figure id="captureBoite" hidden style="margin:8px 0"><img id="captureImg" alt="Capture de l'écran de la carte"><figcaption class="doux petit" id="captureLegende"></figcaption></figure>
  </div>
  <div class="carte fichiers">
   <div class="ligne"><div class="onglets" id="ongletsFichiers"></div><span id="resumeFichiers" class="doux petit" style="margin-left:auto"></span></div>
   <div id="erreurs" class="avert" hidden></div>
   <pre id="fichier" class="code"></pre>
   <div id="confirmation" class="carte" hidden style="margin-top:8px"></div>
   <div class="ligne" style="margin-top:8px"><span class="doux petit">Écriture : ecran.json, pages.jsonl et ecranLvgl.be
    (l'interface envoyée est celle du cenv)</span><button id="ecrire" class="btn prim" type="button" style="margin-left:auto">Écrire dans le dépôt</button>
    <a id="build" class="btn" target="_blank" rel="noopener" hidden>Envoyer par la page Build ↗</a></div>
   <div id="ecritureMessage" class="avert" hidden></div>
  </div>
 </div>
 <div class="carte">
  <div class="onglets" id="panneaux"><button type="button" data-panneau="proprietes" class="actif">Propriétés</button><button type="button" data-panneau="liaison">Liaison</button><button type="button" data-panneau="remarques" id="ongletRemarques">Remarques</button><button type="button" data-panneau="icones">Icônes</button></div>
  <div class="panneau" id="proprietes"></div><div class="panneau" id="liaison" hidden></div><div class="panneau" id="remarques" hidden></div><div class="panneau" id="icones" hidden></div>
 </div>
</div>
""" + HTML_DISPLAY + """
"""

# Theme pose avant le premier dessin (pas de flash) ; localStorage indisponible : choix du systeme
THEME_TETE = ("<script>(function () { var t = null; try { t = localStorage.getItem('atelier-ecrans-theme'); } catch (e) {}"
              " if (t !== 'sombre' && t !== 'clair') t = window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches"
              " ? 'sombre' : 'clair'; document.documentElement.setAttribute('data-theme', t); })();</script>")

PAGE = ("<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\"><title>Atelier des écrans</title>"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><link rel=\"icon\" href=\"data:,\">"
        + THEME_TETE + "<style>" + CSS + CSS_DISPLAY + CSS_IMPORT + CSS_PALIER2 + CSS_ICONES + CSS_NAV + "</style></head><body>" + HTML
        + "<script src=\"/lib/qr.js\"></script>"     # qr-code-styling (apercu du QR code) ; absente : carre gris
        + "<script>" + lieux.JS + JS + JS_REMARQUES + JS_ECRITURE + JS_POLICES + JS_CANEVAS + JS_IMPORT + JS_DISPLAY + JS_PALIER2 + JS_ICONES + JS_NAV + "</script></body></html>")

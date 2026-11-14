"""Page de l'atelier des visuels d'accueil (disposition A, trois colonnes : outils / canevas / fond et export).

CONTRAT avec atelier_visuels_page_formes.py (CSS_FORMES, HTML_FORMES, JS_FORMES ; JS_FORMES est insere APRES le JS de ce module).
Objet global window.AV, cree par atelier_visuels_page_js.py :
    AV.env (carte), AV.puce, AV.photo (canvas de la photo recadree, AV.larg x AV.haut), AV.mode ('plat'|'photo'),
    AV.carte (= AV.env, nom lu par AV.charge), <div id="av-canevas"> (conteneur central ou les formes creent leur SVG), AV.majPoids(),
    AV.larg / AV.haut (repere), AV.surChangement(fn) (abonnement), AV.change() (a appeler apres toute modification des formes).
Fournis par les formes : AV.formes, AV.dessine(), AV.svg() (SVG du dessin a plat, texte).
Theme : variables CSS --fond --carte --bord --texte --doux --acc --champ --bon --alerte --mauvais ; data-theme="sombre|clair" sur <html>,
comme les autres pages. Aucune couleur d'interface en dur hors du dessin.
"""

import json

import atelier_visuels_description as avd
import atelier_visuels_page_calques as calques
import atelier_visuels_page_elements as elements
import atelier_visuels_page_export as export
import atelier_visuels_page_formes as formes
import atelier_visuels_page_icones as icones
import atelier_visuels_page_points as points
import atelier_visuels_page_js as js
import lieux

CSS = """
:root{--fond:#f4f5f7;--carte:#fff;--bord:#cfd3d9;--texte:#1d2025;--doux:#5c626b;--acc:#1478b8;--ac:var(--acc);--sur-acc:#fff;--voile:rgba(0,0,0,.55);--champ:#eceef1;--bon:#1a7f45;--alerte:#b86b00;--mauvais:#c62828;--bg:var(--champ);--pa:var(--carte);--tx:var(--texte);--mu:var(--doux);--li:var(--bord);color-scheme:light}
:root[data-theme="sombre"]{--fond:#1f1f1f;--carte:#2a2a2a;--bord:#3a3a3a;--texte:#e8e8e8;--doux:#9a9a9a;--acc:#1fa3ec;--ac:var(--acc);--sur-acc:#0d1b26;--voile:rgba(0,0,0,.55);--champ:#333;--bon:#3ddc84;--alerte:#ffb02e;--mauvais:#ff6b6b;--bg:var(--champ);--pa:var(--carte);--tx:var(--texte);--mu:var(--doux);--li:var(--bord);color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--fond);color:var(--texte);font:14px "Segoe UI",sans-serif}
header{display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:10px 16px;background:var(--carte);border-bottom:1px solid var(--bord)}
header h1{font-size:16px;margin:0 8px 0 0}.sp{flex:1}
select,button,input,.btn{background:var(--champ);color:var(--texte);border:1px solid var(--bord);border-radius:6px;padding:6px 10px;font:inherit}
button,.btn{cursor:pointer;display:inline-block;text-align:center}button.on{background:var(--acc);border-color:var(--acc);color:var(--sur-acc)}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
button:disabled{opacity:.5;cursor:not-allowed}input[type=range]{padding:0}
main{display:grid;grid-template-columns:280px minmax(0,1fr) 300px;gap:0;min-height:calc(100vh - 56px)}
main>div{padding:8px;overflow:auto}
.pan{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:10px;margin-bottom:8px}
.pan h2{font-size:13px;margin:0 0 8px;color:var(--doux);text-transform:uppercase;letter-spacing:.04em}
.g{display:grid;gap:6px}.row{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:5px 0}
.doux{color:var(--doux)}.bon{color:var(--bon);font-weight:600}.alerte{color:var(--alerte);font-weight:600}.mauvais{color:var(--mauvais);font-weight:600}
#av-zone{border:2px dashed var(--bord);border-radius:8px;padding:10px;text-align:center}#av-zone.survol{border-color:var(--acc)}
#av-crop{width:100%;touch-action:none;cursor:crosshair;border-radius:6px;margin-top:6px}
.cv{border:1px solid var(--bord);border-radius:8px;overflow:auto;background:var(--carte)}
#av-empreinte{word-break:break-all;font-size:11px}
@media(max-width:900px){main{grid-template-columns:1fr}}
"""

HTML = """
<header><h1>Atelier des visuels</h1>
<select id="av-carte" aria-label="Carte"></select>
<span class="doux">Fond :</span><button id="av-fond-plat" class="on">Dessin à plat</button><button id="av-fond-photo">Photo allégée</button>
<span class="sp"></span>
<span>Poids du fond : <span id="av-poids" class="doux">-</span> <span id="av-type" class="doux"></span></span>
<button id="av-export">Exporter</button><button id="av-ecrire">Écrire dans le dépôt</button>
<button id="av-theme" type="button">Sombre</button></header>
<main><div>
<div class="pan"><h2>1. Photo</h2><div class="g">
<div id="av-zone"><button type="button" id="av-importe">Déposer une photo…</button><input type="file" id="av-fichier" class="vh" accept="image/*" tabindex="-1" aria-label="Photo à importer">
<div class="doux">ou glisser l'image ici</div></div>
<canvas id="av-crop" hidden role="img" aria-label="Recadrage de la photo : glisser le cadre ou ses coins"></canvas>
<div class="row"><button id="av-rot" type="button">Tourner de 90°</button><button id="av-rec0" type="button">Tout garder</button></div>
<div class="row"><label class="doux" for="av-larg">Largeur de travail</label><span id="av-larg-v"></span></div>
<input type="range" id="av-larg" min="320" max="800" step="10" value="480">
</div></div>
""" + formes.HTML_FORMES + elements.HTML_PALETTE + icones.HTML_ICONES + """
</div>
<div><div class="cv" id="av-canevas"></div></div>
<div>
<div class="pan"><h2>Fond</h2><div class="g">
<label id="av-qualite-l" hidden class="row"><span class="doux">Qualité WebP <span id="av-qualite-v"></span></span>
<input type="range" id="av-qualite" min="30" max="95" value="70"></label>
<button id="av-garder" class="on" type="button" disabled>Garder ce fond</button>
<div id="av-msg" class="doux" role="status"></div><div id="av-empreinte" class="doux"></div></div></div>
""" + elements.HTML_PANNEAU + export.HTML_EXPORT + """
</div></main>
"""

THEME_TETE = ("<script>(function () { var t = null; try { t = localStorage.getItem('atelier-visuels-theme'); } catch (e) {}"
              " if (t !== 'sombre' && t !== 'clair') t = window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches"
              " ? 'sombre' : 'clair'; document.documentElement.setAttribute('data-theme', t); })();</script>")

# Colle : le poids suit toute modification des formes (AV.surFormes, cote editeur) ; l'editeur a lu 'defaut' avant le choix de la carte.
COLLE = "if (AV.surFormes) AV.surFormes(function () { AV.invalide(); AV.majPoids(); }); if (AV.env && AV.charge) AV.charge(); AV.majPoids();"

SEUILS = {"avert": avd.SEUIL_AVERT, "esp32": avd.SEUILS_REFUS["esp32"], "autre": avd.SEUILS_REFUS["autre"]}

PAGE = ("<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Atelier des visuels</title><link rel=\"icon\" href=\"data:,\">" + THEME_TETE
        + "<style>" + CSS + formes.CSS_FORMES + export.CSS_EXPORT + icones.CSS_ICONES + elements.CSS_ELEMENTS + "</style></head><body>" + HTML
        + "<script>window.AV_SEUILS = " + json.dumps(SEUILS) + ";" + lieux.JS + js.JS + formes.JS_FORMES + calques.JS_CALQUES + points.JS_POINTS + icones.JS_ICONES + elements.JS_ELEMENTS + export.JS_EXPORT + COLLE + "</script></body></html>")

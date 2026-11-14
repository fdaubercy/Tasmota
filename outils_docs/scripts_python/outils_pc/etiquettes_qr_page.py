"""Page « Etiquettes QR code » (HTML et CSS ; le script est dans etiquettes_qr_page_js.py), plan A4.

Disposition du modele A de outils_docs/etiquettes_qr/ (modele-A.png, modele-A-sombre.png) : cartes par lieu a gauche,
reglages en onglets au centre (Contenu, Style, Gabarit commun), apercu, texte lu et verdict a droite. Theme clair ou
sombre par l'interrupteur, comme l'atelier des graphiques. Le QR code est dessine par qr-code-styling (servi par /lib.js).
"""

from etiquettes_qr_page_impression import CSS_IMPRESSION, JS_IMPRESSION
from etiquettes_qr_page_js import JS
from etiquettes_qr_page_publication import JS_PUBLICATION
import lieux

CSS = """
:root{color-scheme:light;--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--bleu:#2563eb;--vert:#2a9d4a;
  --orange:#c27400;--rouge:#c0392b;--btn:#fff;--btn-bord:#888;--piste:#e9e9ea;--bleu-fond:#eef3ff;--orange-fond:#fff4e0;
  --vert-fond:#e3f4e8;--rouge-fond:#fdecea;--champ:#fff;--diff-fond:#f6f8fa;--diff-texte:#24292f;--diff-p:#116329;
  --diff-m:#a40e26;--diff-c:#6e7781}
:root[data-theme="sombre"]{color-scheme:dark;--fond:#121417;--carte:#1d2025;--bord:#3a3f47;--texte:#e6e6e6;--doux:#a8adb5;
  --bleu:#5b93ff;--vert:#3fbf63;--orange:#f0a020;--rouge:#ff6b5b;--btn:#262a30;--btn-bord:#555b64;--piste:#39393d;
  --bleu-fond:#18233a;--orange-fond:#33270f;--vert-fond:#16301f;--rouge-fond:#3a1d1a;--champ:#15171b;--diff-fond:#0d1117;
  --diff-texte:#c9d1d9;--diff-p:#7ee787;--diff-m:#ff7b72;--diff-c:#8b949e}
*{box-sizing:border-box}
body{margin:0;font:14px system-ui,sans-serif;color:var(--texte);background:var(--fond)}
main{max-width:1400px;margin:0 auto;padding:12px 16px 24px}
header{display:flex;align-items:center;gap:12px;margin-bottom:10px;flex-wrap:wrap}
header select{width:auto;font-weight:600;max-width:100%}
.theme{margin-left:auto;display:flex;align-items:center;gap:8px;font-size:13px;color:var(--doux);cursor:pointer;user-select:none}
.theme input{position:absolute;opacity:0;width:1px;height:1px;margin:0}
.interrupteur{position:relative;flex:none;width:2.6em;height:1.5em;border-radius:.75em;background:var(--piste);transition:background .2s}
.interrupteur::after{content:"";position:absolute;top:.15em;left:.15em;width:1.2em;height:1.2em;border-radius:50%;background:#fff;
  box-shadow:0 1px 3px rgba(0,0,0,.3);transition:transform .2s}
.theme input:checked + .interrupteur{background:#34c759}
.theme input:checked + .interrupteur::after{transform:translateX(1.1em)}
.theme input:focus-visible + .interrupteur{outline:2px solid var(--bleu);outline-offset:2px}
h1{font-size:20px;margin:0;white-space:nowrap} h2{font-size:15px;margin:0 0 8px}
h3{font-size:12px;margin:12px 0 6px;color:var(--doux);text-transform:uppercase;letter-spacing:.04em}
.doux{color:var(--doux)} .petit{font-size:12px} .cache{display:none!important}
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:12px;min-width:0}
.btn{display:inline-block;padding:5px 11px;border:1px solid var(--btn-bord);border-radius:6px;background:var(--btn);font:inherit;
  font-size:13px;color:inherit;cursor:pointer;white-space:nowrap}
.btn.prim{background:var(--bleu);border-color:var(--bleu);color:#fff} .btn:disabled{opacity:.45;cursor:default}
:root[data-theme="sombre"] .btn.prim{background:#2f6fe0;border-color:#2f6fe0}
.btn.mini{padding:1px 7px;font-size:12px}
.btn:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--bleu);outline-offset:1px}
input[type=text],input[type=search],select{font:inherit;font-size:13px;padding:3px 6px;border:1px solid var(--bord);border-radius:5px;
  background:var(--champ);color:var(--texte);min-width:0}
input[type=color]{width:30px;height:24px;padding:0;border:1px solid var(--bord);border-radius:4px;background:var(--champ)}
.pastille{display:inline-block;white-space:nowrap;padding:1px 7px;border-radius:10px;font-size:11px;background:var(--piste);color:var(--doux)}
.pastille.ok{background:var(--vert-fond);color:var(--vert)} .pastille.or{background:var(--orange-fond);color:var(--orange)}
.pastille.bleu{background:var(--bleu-fond);color:var(--bleu)}
.ligne{display:flex;gap:6px;align-items:center;margin:5px 0;flex-wrap:wrap}
.colonnes{display:grid;grid-template-columns:240px minmax(0,1fr) 330px;gap:12px;align-items:start}
@media (max-width:1000px){.colonnes{grid-template-columns:1fr}}
.lieu{font-size:11px;color:var(--doux);text-transform:uppercase;letter-spacing:.05em;padding:8px 4px 2px}
.env{display:flex;gap:6px;align-items:center;width:100%;padding:4px 6px;border:0;border-radius:5px;background:none;color:inherit;
  font:inherit;font-size:13px;text-align:left;cursor:pointer}
.env:hover{background:var(--piste)} .env.sel{background:var(--bleu-fond)}
.env .nom{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.onglets{display:flex;gap:2px;margin-bottom:-1px}
.onglets button{padding:5px 12px;border:1px solid var(--bord);border-bottom:none;border-radius:6px 6px 0 0;background:var(--piste);
  font:13px system-ui,sans-serif;color:var(--texte);cursor:pointer}
.onglets button.actif{background:var(--carte);font-weight:600}
.panneau{border-top:1px solid var(--bord);padding-top:8px}
.lq{display:grid;grid-template-columns:62px 110px minmax(0,1fr) auto;gap:6px;align-items:center;padding:4px 6px;
  border:1px solid var(--bord);border-radius:6px;margin:4px 0;background:var(--champ)}
.lq.introuvable,.lq.refuse{border-color:var(--orange)} .lq input,.lq select{width:100%}
.lq .src{font-size:11px;color:var(--doux)} .lq .val{grid-column:2 / 4;font-size:12px;color:var(--doux);overflow-wrap:anywhere}
.lq .act{display:flex;gap:2px}
.lq .aa{grid-column:2 / 4;display:flex;gap:6px} .lq .aa input{flex:1;min-width:0;font-size:12px}
.persist{max-height:220px;overflow:auto;border:1px solid var(--bord);border-radius:6px;margin-top:4px}
.persist button{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid var(--bord);background:none;color:inherit;
  font:12.5px Consolas,monospace;padding:3px 6px;cursor:pointer;overflow-wrap:anywhere}
.persist button:hover{background:var(--bleu-fond)} .persist .v{color:var(--doux)}
.grille{display:grid;grid-template-columns:120px 1fr;gap:6px 10px;align-items:center}
.qr{display:inline-block;background:#fff;padding:0;border-radius:6px;line-height:0;min-height:40px}
.lu{background:var(--piste);border-radius:6px;padding:8px 10px;font:13px/1.45 Consolas,monospace;white-space:pre-wrap;min-height:40px;overflow-wrap:anywhere}
.verdict{border-radius:6px;padding:6px 9px;font-size:13px;margin-top:6px}
.verdict.lisible{background:var(--vert-fond);color:var(--vert)} .verdict.limite{background:var(--orange-fond);color:var(--orange)}
.verdict.trop_dense,.verdict.trop_long{background:var(--rouge-fond);color:var(--rouge)}
.avert{background:var(--orange-fond);border-left:3px solid var(--orange);padding:6px 8px;font-size:12px;border-radius:4px;margin:6px 0 0}
.avert.rouge{background:var(--rouge-fond);border-left-color:var(--rouge)} .avert.vert{background:var(--vert-fond);border-left-color:var(--vert)}
.diff{background:var(--diff-fond);color:var(--diff-texte);font:12px/1.45 Consolas,monospace;border:1px solid var(--bord);border-radius:6px;
  padding:8px 10px;white-space:pre;overflow:auto;max-height:320px;margin:4px 0}
.diff .p{color:var(--diff-p)} .diff .m{color:var(--diff-m)} .diff .c{color:var(--diff-c)}
#bandeau{margin:0 0 10px}
"""

HTML = """<main>
<header>
  <h1>Étiquettes QR code</h1>
  <label class="doux petit" for="choix-env">carte</label>
  <select id="choix-env" aria-label="Carte"></select>
  <span id="pastilles"></span>
  <label class="theme"><input type="checkbox" id="theme"><span class="interrupteur"></span>Mode sombre</label>
</header>
<div id="bandeau"></div>
<div class="colonnes">
  <div class="carte"><h2>Cartes</h2>
    <label class="petit doux"><input type="checkbox" id="planche-tout"> tout cocher pour la planche</label>
    <div id="liste-cartes"></div>
    <h3>Planche A4</h3>
    <div class="ligne petit">taille <input type="number" id="planche-taille" min="10" max="100" step="1" style="width:58px" aria-label="Taille de la planche en mm"> mm</div>
    <div class="petit doux" id="planche-grille"></div>
    <div class="ligne"><button class="btn" type="button" id="btn-planche" disabled>Planche (0 carte)</button></div>
  </div>
  <div class="carte">
    <div class="onglets" role="tablist">
      <button type="button" class="actif" data-onglet="contenu">Contenu</button>
      <button type="button" data-onglet="style">Style</button>
      <button type="button" data-onglet="gabarit">Gabarit commun</button>
    </div>
    <div class="panneau" id="onglet-contenu">
      <div class="ligne petit">le QR code contient <select id="contenu" aria-label="Contenu du QR code"></select></div>
      <h3>Lignes lues par le téléphone</h3>
      <div id="lignes"></div>
      <div class="ligne">
        <select id="ajout-standard" aria-label="Champ standard"></select><button class="btn" type="button" id="btn-standard">+ Champ standard</button>
        <button class="btn" type="button" id="btn-libre">+ Ligne libre</button>
      </div>
      <div class="ligne petit">séparateur <input type="text" id="separateur" maxlength="5" style="width:52px" aria-label="Séparateur">
        entre les lignes <select id="entre-lignes" aria-label="Entre les lignes"></select></div>
      <h3>Clé du persist de la carte (secrets jamais proposés)</h3>
      <input type="search" id="filtre-persist" placeholder="filtrer : ModBus, id, vitesse…" style="width:100%" aria-label="Filtrer le persist">
      <div class="persist" id="persist"></div>
    </div>
    <div class="panneau cache" id="onglet-style">
      <div class="grille">
        <label for="points">points</label><select id="points"></select>
        <label for="coins">coins</label><select id="coins"></select>
        <label for="couleur">couleur</label><input type="color" id="couleur">
        <label for="fond">fond</label><input type="color" id="fond">
        <label for="image">image au centre</label><select id="image"></select>
        <span>page sur la carte</span><label class="petit"><input type="checkbox" id="page-carte"> <span id="page-note">route /qrcode de la carte</span></label>
      </div>
      <p class="doux petit">Avec une image, la correction passe en H (30 %) : le QR code grossit.
        Images : dossier outils_docs/etiquettes_qr/images/ (PNG, JPEG, SVG ; 8 Ko au plus).</p>
    </div>
    <div class="panneau cache" id="onglet-gabarit">
      <p class="petit">Le gabarit commun vaut pour toutes les cartes ; une carte n'enregistre que ce qui en diffère
        (outils_docs/etiquettes_qr/cartes/&lt;env&gt;.json).</p>
      <div class="ligne"><button class="btn" type="button" id="btn-reprend">Reprendre le gabarit commun pour cette carte</button></div>
      <div class="ligne"><button class="btn" type="button" id="btn-gabarit">Faire du réglage de cette carte le gabarit commun…</button></div>
    </div>
  </div>
  <div class="carte">
    <h2>Aperçu</h2>
    <div style="text-align:center"><div class="qr" id="qr"></div></div>
    <div class="ligne petit">Taille imprimée <input type="range" id="taille" min="10" max="100" step="1" style="flex:1" aria-label="Taille imprimée en mm"><b id="mm"></b></div>
    <h3>Ce que le téléphone affiche</h3><div class="lu" id="lu"></div>
    <div id="verdict" class="verdict"></div>
    <div id="avertissements"></div>
    <div class="ligne" style="margin-top:10px"><button class="btn prim" type="button" id="btn-ecrire">Écrire dans le dépôt…</button>
      <button class="btn" type="button" id="btn-imprimer" disabled>Imprimer</button><button class="btn" type="button" id="btn-png" disabled>PNG</button>
      <button class="btn" type="button" id="btn-svg" disabled>SVG</button>
      <button class="btn" type="button" id="btn-publier" title="Fiches des cartes en mode lien, branche etiquettes (GitHub Pages)">Publier les fiches…</button>
      <button class="btn cache" type="button" id="btn-pages" title="GitHub Pages n'est pas activé sur le dépôt">Activer GitHub Pages…</button></div>
    <div class="ligne petit"><label><input type="checkbox" id="petit-nom"> petit nom sous le code</label>
      <button class="btn mini" type="button" id="btn-essai" disabled title="Carte affichée à 15, 20, 25 et 30 mm, texte court et long">Planche d'essai</button></div>
    <p class="doux petit">Dans la fenêtre d'impression : échelle 100 % (« Taille réelle »), marges par défaut ; la règle de
      50 mm imprimée en bas de la feuille le vérifie.</p>
    <div id="impression-messages"></div>
    <div id="ecriture"></div>
  </div>
</div>
</main>
<div id="impression"></div>"""

THEME_TETE = ("<script>(function () { var t = null; try { t = localStorage.getItem('etiquettes-qr-theme'); } catch (e) {}"
              " if (t !== 'clair' && t !== 'sombre') t = (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches)"
              " ? 'sombre' : 'clair'; document.documentElement.setAttribute('data-theme', t); })();</script>")
THEME_INTERRUPTEUR = ("<script>(function () { var c = document.getElementById('theme');"
                      " c.checked = document.documentElement.getAttribute('data-theme') === 'sombre';"
                      " c.onchange = function () { var t = this.checked ? 'sombre' : 'clair';"
                      " document.documentElement.setAttribute('data-theme', t);"
                      " try { localStorage.setItem('etiquettes-qr-theme', t); } catch (e) {} }; })();</script>")

PAGE = ("<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>Étiquettes QR code</title><link rel=\"icon\" href=\"data:,\">" + THEME_TETE + "<style>" + CSS + CSS_IMPRESSION + "</style>"
        "<script src=\"/lib.js\"></script></head><body>" + HTML + THEME_INTERRUPTEUR
        + "<script>" + lieux.JS + JS + JS_IMPRESSION + JS_PUBLICATION + "</script></body></html>")

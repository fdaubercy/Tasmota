"""Page de l'atelier des graphiques (HTML et CSS ; le script est dans atelier_graphiques_page_js.py), plan A7.

Disposition du modele B de outils_docs/atelier_graphiques/ (trois colonnes : carte et donnees, apercu et styles proposes,
reglages ; onglets du code en bas) ; la bascule « Page » montre la page entiere en grille, comme le modele C. CSS repris
de maquettes_atelier.html. L'apercu charge le VRAI moteur de la carte (data/sd, servi par /moteur/) : ECharts et
liquidfill sont poses avant lui, il ne charge donc rien lui-meme.
"""

from atelier_graphiques_page_js import JS

CSS = """
/* Theme de la PAGE (interrupteur « Mode sombre », comme l'annuaire) ; l'apercu .cadre garde ses couleurs : il simule la carte */
:root{color-scheme:light;--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--bleu:#2563eb;--vert:#2a9d4a;
  --orange:#c27400;--rouge:#c0392b;--btn:#fff;--btn-bord:#888;--piste:#e9e9ea;--bleu-fond:#eef3ff;--orange-fond:#fff4e0;
  --vert-fond:#e3f4e8;--rouge-fond:#fdecea;--champ:#fff;--console:#181818;--console-texte:#cccccc}
:root[data-theme="sombre"]{color-scheme:dark;--fond:#121417;--carte:#1d2025;--bord:#3a3f47;--texte:#e6e6e6;--doux:#a8adb5;
  --bleu:#5b93ff;--vert:#3fbf63;--orange:#f0a020;--rouge:#ff6b5b;--btn:#262a30;--btn-bord:#555b64;--piste:#39393d;
  --bleu-fond:#18233a;--orange-fond:#33270f;--vert-fond:#16301f;--rouge-fond:#3a1d1a;--champ:#15171b;--console:#0b0c0e;
  --console-texte:#d4d4d4}
*{box-sizing:border-box}
body{margin:0;font:14px system-ui,sans-serif;color:var(--texte);background:var(--fond)}
main{max-width:1400px;margin:0 auto;padding:12px 16px 24px}
header{display:flex;align-items:baseline;gap:14px;margin-bottom:10px;flex-wrap:wrap}
.theme{margin-left:auto;align-self:center;display:flex;align-items:center;gap:8px;font-size:13px;color:var(--doux);cursor:pointer;user-select:none}
.theme input{position:absolute;opacity:0;width:1px;height:1px;margin:0}
/* Taille en em : l'interrupteur suit la taille du texte de son libelle (13 px -> ~34 x 20 px), repris de l'annuaire */
.interrupteur{position:relative;flex:none;width:2.6em;height:1.5em;border-radius:.75em;background:var(--piste);transition:background .2s}
.interrupteur::after{content:"";position:absolute;top:.15em;left:.15em;width:1.2em;height:1.2em;border-radius:50%;background:#fff;
  box-shadow:0 1px 3px rgba(0,0,0,.3);transition:transform .2s}
.theme input:checked + .interrupteur{background:#34c759}
.theme input:checked + .interrupteur::after{transform:translateX(1.1em)}
.theme input:focus-visible + .interrupteur{outline:2px solid var(--bleu);outline-offset:2px}
h1{font-size:20px;margin:0} h2{font-size:15px;margin:0 0 8px}
h3{font-size:13px;margin:12px 0 6px;color:var(--doux);text-transform:uppercase;letter-spacing:.04em}
.doux{color:var(--doux)} .petit{font-size:12px} .cache{display:none!important}
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:12px;min-width:0}
.btn{display:inline-block;padding:6px 12px;border:1px solid var(--btn-bord);border-radius:6px;background:var(--btn);font:inherit;
  color:inherit;cursor:pointer;text-decoration:none}
.btn.prim{background:var(--bleu);border-color:var(--bleu);color:#fff} .btn:disabled{opacity:.45;cursor:default}
:root[data-theme="sombre"] .btn.prim{background:#2f6fe0;border-color:#2f6fe0}   /* blanc lisible (~4,6:1) */
.btn.mini{padding:2px 8px;font-size:12px}
.pastille{display:inline-block;padding:1px 7px;border-radius:10px;font-size:11px;background:var(--piste);color:var(--doux);
  margin-right:3px;border:0;font-family:inherit}
.pastille.ok{background:var(--vert-fond);color:var(--vert)} .pastille.non{background:var(--rouge-fond);color:var(--rouge)}
.pastille.bleu{background:var(--bleu-fond);color:var(--bleu)} button.pastille{cursor:pointer}
.ligne{display:flex;gap:8px;align-items:center;margin:5px 0}
label.ch{display:flex;gap:6px;align-items:center;margin:3px 0}
input[type=text],input[type=number],select{font:inherit;padding:4px 6px;border:1px solid var(--bord);border-radius:5px;
  background:var(--champ);color:var(--texte);width:100%;min-width:0}
input:disabled,select:disabled{opacity:.55;cursor:default} ::placeholder{color:var(--doux);opacity:.8}
input[type=color]{width:30px;height:24px;padding:0;border:1px solid var(--bord);border-radius:4px;flex:none;background:var(--champ)}
.etiq{width:92px;flex:none;color:var(--doux);font-size:12px}
.colonnes{display:grid;grid-template-columns:270px minmax(0,1fr) 330px;gap:12px;align-items:start}
.arbre div{padding:1px 0;font-size:13px} .arbre .n2{padding-left:16px;color:var(--doux);font-size:12px}
.arbre .n3{padding-left:28px} .arbre .gr{margin-top:6px}
.arbre a{color:var(--bleu);cursor:pointer;font-size:12px}
.code{background:var(--console);color:var(--console-texte);font:12px/1.45 Consolas,monospace;border-radius:0 6px 6px 6px;
  padding:8px 10px;white-space:pre;overflow:auto;max-height:240px;min-height:90px;margin:0}
.code.complet{max-height:none} .code .p{color:#7ee787} .code .m{color:#ff7b72} .code .c{color:#8b9099}
.onglets{display:flex;gap:2px;flex-wrap:wrap}
.onglets button{padding:5px 12px;border:1px solid var(--bord);border-bottom:none;border-radius:6px 6px 0 0;
  background:var(--piste);font:12px system-ui,sans-serif;cursor:pointer;color:var(--texte)}
.onglets button.actif{background:var(--console);color:#fff;border-color:var(--console)}
.vignettes{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}
.vign{border:1px solid var(--bord);border-radius:7px;padding:8px;background:var(--carte);position:relative;cursor:pointer;min-width:0}
.vign.choisie{border:2px solid var(--bleu);padding:7px;background:var(--bleu-fond)}
.vign .rang{position:absolute;top:6px;left:8px;font-weight:700;color:var(--bleu)}
.vign .nom{font-weight:600;margin-left:18px} .vign .mini{height:70px;margin:4px 0}
.vign .raison{font-size:12px;color:var(--doux);min-height:32px}
.avert{background:var(--orange-fond);border-left:3px solid var(--orange);padding:6px 8px;font-size:12px;border-radius:4px;margin:8px 0 0}
.avert.rouge{background:var(--rouge-fond);border-left-color:var(--rouge)} .avert.vert{background:var(--vert-fond);border-left-color:var(--vert)}
#bandeau{margin:0 0 10px}
.zone{display:flex;gap:6px;align-items:center;margin:4px 0;font-size:12px}
.zone input[type=number]{width:62px}
.serie{margin:4px 0 6px} .serie .ligne{margin:2px 0} .serie input.unite{width:64px;flex:none}
details{font-size:12px;color:var(--doux);margin-top:8px}
/* Apercu : cadre de la page de la carte (theme clair ou sombre de Tasmota, PC ou telephone) */
.cadre{background:#fff;color:#222;border-radius:8px;padding:8px;margin:0 auto;font-family:verdana,sans-serif}
.cadre.sombre{background:#252525;color:#eaeaea}
.cadre.telephone{width:380px}
.cadre.telephone .pg_grille{grid-template-columns:minmax(0,1fr)}
.cadre .tete,.cadre .menu{display:none;text-align:center}
.cadre.page .tete,.cadre.page .menu{display:block}
.cadre .tete div{font-size:13px;opacity:.75} .cadre .tete h4{margin:2px 0 8px;font-size:17px}
.cadre .menu span{display:inline-block;background:#1fa3ec;color:#fff;padding:6px 40px;border-radius:5px;font-size:13px;margin-top:8px}
#apercu #pg_page{width:auto}
.cadre.page .pg_tuile{cursor:grab} .pg_tuile.sel{outline:2px solid #5b93ff;outline-offset:1px}
.pg_tuile.survol{outline:2px dashed #5b93ff}
#destination .code{max-height:160px;border-radius:6px;margin:6px 0}
.bascules button{margin-left:2px}
.bascules button.actif{background:var(--bleu-fond);color:var(--bleu)}
.actions{display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-top:8px;flex-wrap:wrap}
"""

HTML = """<main>
<header><h1>Atelier des graphiques</h1>
<span class="doux">http://127.0.0.1:7950 · carte <b id="nom-carte">…</b>
<button id="relire" class="pastille" title="Relire les séries et les valeurs sur la carte">lecture de la carte…</button>
<span id="pastille-lib" class="pastille bleu"></span></span>
<label class="theme" for="theme" title="Thème de cette page (l'aperçu garde le thème de la carte : « thème sombre » au-dessus de lui)">
  <span>Mode sombre</span><input id="theme" type="checkbox" role="switch"><span class="interrupteur" aria-hidden="true"></span></label></header>
<div id="bandeau" class="avert cache"></div>
<div class="colonnes">
<div class="carte">
  <h2>Carte et données</h2>
  <select id="env" aria-label="Carte"></select>
  <h3>Je veux voir</h3>
  <select id="intention" aria-label="Intention"></select>
  <h3>Séries</h3>
  <div class="arbre" id="arbre"></div>
  <div id="form-calc" class="cache">
    <div class="ligne"><span class="etiq">Nom</span><input type="text" id="calc-nom" placeholder="cuve.manque"></div>
    <div class="ligne"><span class="etiq">Formule</span><input type="text" id="calc-formule" placeholder="6732 - sensorsCuve.niveauCuve.volume"></div>
    <div class="ligne"><span class="etiq">Nature</span><select id="calc-nature"><option value="direct">instantanée</option>
      <option value="historique">historique</option></select></div>
    <div class="ligne"><button class="btn mini" id="calc-ajouter">Ajouter</button><button class="btn mini" id="calc-annuler">Annuler</button></div>
  </div>
</div>
<div>
  <div class="carte">
    <div class="ligne" style="margin:0 0 6px"><h2 style="margin:0" id="titre-apercu">Aperçu</h2>
      <span class="bascules" style="margin-left:auto">
        <button class="pastille" data-mode="graphique">graphique</button><button class="pastille" data-mode="page">page</button>
        <button class="pastille" data-vue="pc">PC</button><button class="pastille" data-vue="telephone">téléphone</button>
        <button class="pastille" id="sombre">thème sombre</button></span></div>
    <div id="cadre" class="cadre"><div class="tete"><div id="tete-carte"></div><h4 id="tete-titre"></h4></div>
      <div id="apercu"></div><div class="menu"><span>Menu principal</span></div></div>
  </div>
  <div class="carte" style="margin-top:10px">
    <h2>Styles proposés <span class="doux petit" id="resume-styles"></span></h2>
    <div class="vignettes" id="vignettes"></div>
    <details id="ecartes"><summary>Styles écartés</summary><div id="liste-ecartes"></div></details>
  </div>
</div>
<div class="carte">
  <h2>Réglages</h2>
  <div class="ligne"><span class="etiq">Titre</span><input type="text" id="r-titre"></div>
  <div class="ligne"><span class="etiq">Bornes</span><input type="number" id="r-min" placeholder="min"> à <input type="number" id="r-max" placeholder="max"></div>
  <h3>Séries</h3>
  <div id="r-series"></div>
  <h3>Seuils</h3>
  <div id="r-zones"></div>
  <a class="petit" href="#" id="r-ajout-zone">+ ajouter un seuil</a>
  <h3>Période et cadence</h3>
  <div class="ligne"><span class="etiq">Période</span><select id="r-periode"><option value="direct">Direct (valeur du moment)</option>
    <option value="jour">Jour (24 h glissantes)</option><option value="mois">Mois</option></select></div>
  <div class="ligne"><span class="etiq">Cadence</span><select id="r-cadence"><option value="">par défaut</option>
    <option>1</option><option>2</option><option>5</option><option>10</option><option>30</option><option>60</option>
    <option>300</option><option>900</option><option>3600</option></select><span class="petit doux">s</span></div>
  <div class="ligne" id="ligne-cumul"><span class="etiq">Cumul</span><select id="r-cumul"><option value="">par jour (défaut)</option>
    <option value="heure">par heure</option><option value="jour">par jour</option><option value="mois">par mois</option></select></div>
  <h3>Taille et destination</h3>
  <div class="ligne"><span class="etiq">Largeur</span><select id="r-largeur"><option value="demi">Demi</option><option value="pleine">Pleine</option></select></div>
  <div class="ligne"><span class="etiq">Hauteur</span><select id="r-hauteur"><option value="">par défaut (260 px)</option>
    <option value="180">180 px</option><option value="240">240 px</option><option value="300">300 px</option>
    <option value="400">400 px</option><option value="500">500 px</option></select></div>
  <div class="ligne"><span class="etiq">Page</span><select id="r-page"></select></div>
  <div class="ligne champ-page"><span class="etiq">Adresse</span><input type="text" id="r-page-id" title="/&lt;adresse&gt; sur la carte : a-z, 0-9, tirets"></div>
  <div class="ligne champ-page"><span class="etiq">Titre page</span><input type="text" id="r-page-titre"></div>
  <div class="ligne champ-page"><span class="etiq">Accès</span><select id="r-acces"><option value="bouton">Bouton sur l'accueil</option>
    <option value="lien">Lien depuis un encadré</option></select></div>
  <label class="ch petit champ-page"><input type="checkbox" id="r-solidifier"> Solidifier le module (firmware à recompiler)</label>
  <div id="destination"></div>
  <div class="ligne" style="flex-wrap:wrap;margin-top:10px"><button class="btn mini" id="ajout-graphique">+ Graphique</button>
    <button class="btn mini" id="suppr-graphique">Retirer le graphique</button>
    <button class="btn mini" id="suppr-page">Retirer la page</button></div>
  <div id="alertes"></div>
  <div id="motifs"></div>
</div>
</div>
<div style="margin-top:12px">
  <div class="onglets" id="onglets"></div>
  <pre class="code" id="code"></pre>
  <div class="actions"><span class="doux petit" id="resume"></span>
    <button class="btn" id="voir-diff">Voir le diff complet</button>
    <button class="btn prim" id="ecrire" disabled>Écrire dans le dépôt</button>
    <a class="btn" id="lien-build" target="_blank" rel="noopener" href="http://127.0.0.1:7700/">Envoyer par la page Build ↗</a></div>
  <div id="message"></div>
</div>
</main>"""

# Theme pose AVANT le rendu (pas d'eclair blanc) : choix memorise, sinon celui du systeme (comme annuaire_page.py)
THEME_TETE = ("<script>(function () { var t = null; try { t = localStorage.getItem('atelier-graphiques-theme'); } catch (e) {}"
              " if (t !== 'clair' && t !== 'sombre') t = (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches)"
              " ? 'sombre' : 'clair'; document.documentElement.setAttribute('data-theme', t); })();</script>")
# Interrupteur : reflete le theme pose, memorise le choix (localStorage indisponible : il vaut pour la page)
THEME_INTERRUPTEUR = ("<script>(function () { var c = document.getElementById('theme');"
                      " c.checked = document.documentElement.getAttribute('data-theme') === 'sombre';"
                      " c.onchange = function () { var t = this.checked ? 'sombre' : 'clair';"
                      " document.documentElement.setAttribute('data-theme', t);"
                      " try { localStorage.setItem('atelier-graphiques-theme', t); } catch (e) {} }; })();</script>")

MOTEUR = "".join(f'<script src="/moteur/{nom}"></script>' for nom in
                 ("echarts.min.js", "echarts-liquidfill.min.js", "pages_graphiques_formule.js", "pages_graphiques.js"))

PAGE = ("<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\"><title>Atelier des graphiques</title><link rel=\"icon\" href=\"data:,\">"
        + THEME_TETE + "<link rel=\"stylesheet\" href=\"/moteur/pages_graphiques.css\"><style>" + CSS + "</style>" + MOTEUR
        + "</head><body>" + HTML + THEME_INTERRUPTEUR + "<script>" + JS + "</script></body></html>")

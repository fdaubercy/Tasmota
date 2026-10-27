"""Page HTML de « Assistant persist » (servie par assistant_persist_web.py), disposition A de la maquette
(docs/superpowers/specs/2026-10-27-assistant-persist-maquette.html) : cinq etapes en pastilles, formulaire a gauche,
apercu du _persist.json a droite (rafraichi par POST /apercu, anti-rebond de 300 ms).

Le script est dans assistant_persist_page_js.py (fichiers de moins de 500 lignes) ; PAGE les assemble.
Textes inseres par textContent uniquement. Sonde Chrome : test_assistant_persist_page_chrome.py.
"""

import assistant_persist_page_js as _js

HTML = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>Assistant persist</title>
<style>
  :root{color-scheme:light dark;--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--discret:#777;--bleu:#2563eb;
    --vert:#2a9d4a;--orange:#c27400;--rouge:#c0392b;--btn:#fff;--btn-bord:#888;--rouge-fond:#fdecea;--orange-fond:#fff4e0;
    --bleu-fond:#eef3ff;--console:#1e1e1e;--console-texte:#d8dee9}
  @media (prefers-color-scheme: dark){:root{--fond:#121417;--carte:#1d2025;--bord:#33373e;--texte:#e6e6e6;--doux:#a8adb5;
    --discret:#8b9099;--bleu:#5b93ff;--vert:#3fbf63;--orange:#f0a020;--rouge:#ff6b5b;--btn:#262a30;--btn-bord:#555b64;
    --rouge-fond:#3a1d1b;--orange-fond:#3a2c12;--bleu-fond:#18233a;--console:#0b0e13}}
  *{box-sizing:border-box}
  body{margin:0;font:14px system-ui,sans-serif;color:var(--texte);background:var(--fond)}
  main{max-width:1200px;margin:0 auto;padding:12px 16px 40px}
  h1{font-size:20px;margin:6px 0 10px} h2{font-size:15px;margin:0 0 8px}
  .carte{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:10px 12px;margin-bottom:12px}
  .discret{color:var(--discret);font-size:12px}
  .btn{padding:6px 12px;border-radius:6px;border:1px solid var(--btn-bord);background:var(--btn);color:var(--texte);font:inherit;font-size:13px;cursor:pointer}
  .btn.p{background:var(--bleu);color:#fff;border-color:var(--bleu);font-weight:600}
  .btn:disabled{opacity:.45;cursor:not-allowed}
  select,input[type=text],input[type=number]{font:inherit;font-size:13px;padding:4px 6px;background:var(--btn);color:var(--texte);border:1px solid var(--btn-bord);border-radius:4px;max-width:100%}
  .grille{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px 12px;margin-bottom:8px}
  .grille label{display:flex;flex-direction:column;font-size:12px;color:var(--doux);gap:2px}
  .cases{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:4px 12px}
  .cases label{cursor:pointer}.cases label.grise{color:var(--discret);cursor:not-allowed}
  .radios label{display:block;margin:3px 0;cursor:pointer}
  .indice{font-size:11.5px;color:var(--vert)}.indice.av{color:var(--orange)}
  .etapes{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:10px}
  .etapes span{padding:4px 10px;border-radius:12px;background:var(--bleu-fond);color:var(--doux);font-size:12.5px;cursor:pointer}
  .etapes span.actif{background:var(--bleu);color:#fff;font-weight:600}
  .etapes span.fait{color:var(--vert)}
  .deux{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:12px}
  @media (max-width:800px){.deux{grid-template-columns:minmax(0,1fr)}}
  .nav{display:flex;justify-content:space-between;margin-top:12px}
  pre{background:var(--console);color:var(--console-texte);padding:8px;border-radius:6px;overflow:auto;max-height:520px;font-size:12px;margin:0}
  .avert{font-size:12.5px;border-left:3px solid var(--orange);padding:2px 0 2px 8px;margin:4px 0;background:var(--orange-fond)}
  .avert.rouge{border-color:var(--rouge);background:var(--rouge-fond)}
  .ok{color:var(--vert);font-weight:600}.erreur{color:var(--rouge)}
  .metier{display:flex;gap:6px;margin:4px 0;align-items:center}.metier input{flex:1}
  .cache{display:none}
  details{border:1px solid var(--bord);border-radius:6px;padding:6px 10px;margin:8px 0;background:var(--carte)}
  summary{cursor:pointer;font-weight:600}
  .liens a{color:var(--bleu);margin-right:14px}
</style>
</head>
<body>
<main>
  <h1>Assistant de création du persist</h1>
  <div id="bandeau-erreur" class="avert rouge cache"></div>
  <div id="bandeau-modele" class="avert cache">
    <span id="texte-modele"></span>
    <button class="btn" id="maj-modele" type="button">Mettre à jour le modèle</button>
    <div class="discret" id="liste-modele"></div>
  </div>
  <div id="panneau-modele" class="carte cache">
    <h2>Mise à jour du modèle</h2>
    <p class="discret">Retire les clés absentes du parc et aligne les défauts divergents. Les clés à compléter ne sont pas touchées.</p>
    <div id="retours-modele"></div>
    <pre id="diff-modele"></pre>
    <p><button class="btn p" id="valide-modele" type="button">Appliquer au modèle</button>
      <button class="btn" id="annule-modele" type="button">Annuler</button></p>
  </div>
  <div id="interrompues"></div>
  <div class="etapes" id="pastilles"></div>
  <div class="deux">
    <div class="carte" id="formulaire">
      <section id="etape-0">
        <h2>1. Carte</h2>
        <div class="grille">
          <label>Puce<select id="f-puce" data-k="puce"></select></label>
          <label>Base (env de départ)<select id="f-base" data-k="base"></select></label>
          <label>Lieu (minuscules, chiffres)<input type="text" id="f-lieu" data-k="lieu" autocomplete="off"></label>
          <label>Nom (minuscules, chiffres, tirets)<input type="text" id="f-nom" data-k="nom" autocomplete="off"></label>
          <label>Réglage de l'heure<select id="f-heure" data-k="heure"><option>NTP</option><option>RTC</option><option>UDP</option></select></label>
        </div>
        <p class="discret" id="env-propose"></p>
        <h2>Identité (préremplie, modifiable)</h2>
        <div class="grille">
          <label>Hostname<input type="text" id="f-hostname" data-k="hostname" data-ident="1"></label>
          <label>Nom lisible<input type="text" id="f-nom_lisible" data-k="nom_lisible" data-ident="1"></label>
          <label>Nom du modèle (template)<input type="text" id="f-nom_template" data-k="nom_template" data-ident="1"></label>
          <label>Client MQTT<input type="text" id="f-client" data-k="client" data-ident="1"></label>
          <label>SSID du point d'accès<input type="text" id="f-ssid_ap" data-k="ssid_ap" data-ident="1"></label>
          <label>Topic MQTT<input type="text" id="f-topic" data-k="topic" data-ident="1"></label>
        </div>
      </section>
      <section id="etape-1" class="cache">
        <h2>2. Réseau</h2>
        <div class="radios">
          <label><input type="radio" name="role" id="role-autonome" value="autonome" checked> Autonome</label>
          <label><input type="radio" name="role" id="role-maitre" value="maitre"> Maître</label>
          <label><input type="radio" name="role" id="role-esclave" value="esclave"> Esclave de</label>
        </div>
        <div id="bloc-esclave" class="grille cache">
          <label>Maître<select id="f-maitre" data-k="maitre"></select></label>
          <label>Id (ModBus, UDP, TCP, Range Extender)<input type="number" min="1" id="f-id" data-k="id">
            <span class="indice" id="id-indice"></span></label>
        </div>
        <div id="bloc-reseaux" class="grille">
          <label>Réseau Wi-Fi principal<select id="f-reseau1" data-k="reseau1"></select></label>
          <label>Réseau Wi-Fi de secours<select id="f-reseau2" data-k="reseau2"></select></label>
        </div>
        <div class="grille"><label>Adresse IP (0.0.0.0 = DHCP)<input type="text" id="f-ip" data-k="ip"></label></div>
        <p class="discret">Mots de passe : recopiés du parc par le serveur, jamais affichés.</p>
      </section>
      <section id="etape-2" class="cache">
        <h2>3. Fonctions</h2>
        <div class="cases" id="cases"></div>
        <p class="discret" id="note-deps"></p>
      </section>
      <section id="etape-3" class="cache">
        <h2>4. Bloc métier</h2>
        <p class="discret">Au moins un nom (camelCase) : il devient <code>modules.&lt;nom&gt;</code>. Le premier est le principal.</p>
        <div id="metiers"></div>
        <button class="btn" id="ajout-metier" type="button">+ Ajouter un bloc métier</button>
        <p><label><input type="checkbox" id="f-squelettes" data-k="squelettes" checked> Créer les squelettes controle&lt;Nom&gt;.be et &lt;nom&gt;Fonctions.be</label></p>
        <p class="avert rouge cache" id="avert-metier">Donnez au moins un nom de bloc métier.</p>
      </section>
      <section id="etape-4" class="cache">
        <h2>5. Vérification</h2>
        <p><b>Fichiers qui seront écrits</b></p>
        <ul id="fichiers"></ul>
        <button class="btn" id="voir-diff" type="button">Voir le diff</button>
        <div id="retours"></div>
        <div id="panneau-diff" class="cache">
          <details open><summary>Diff (mots de passe masqués)</summary><pre id="diff"></pre></details>
          <details><summary>autoexec.be généré</summary><pre id="autoexec"></pre></details>
        </div>
        <p><button class="btn p" id="creer" type="button" disabled>Créer l'env</button>
          <span class="discret" id="creer-aide">Voir le diff d'abord ; toute saisie ensuite le grise.</span></p>
        <div id="resultat"></div>
      </section>
      <div class="nav" id="nav">
        <button class="btn" id="prec" type="button">← Précédent</button>
        <button class="btn p" id="suiv" type="button">Suivant →</button>
      </div>
    </div>
    <div class="carte">
      <h2>Aperçu _persist.json <span class="discret">(mis à jour à chaque saisie)</span></h2>
      <div id="apercu-refus"></div>
      <pre id="apercu"></pre>
    </div>
  </div>
</main>
<script>
/*JS*/
</script>
</body>
</html>
"""

PAGE = HTML.replace("/*JS*/", _js.JS)

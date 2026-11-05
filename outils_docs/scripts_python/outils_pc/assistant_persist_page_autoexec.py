"""Onglet « autoexec.bat » de la page Assistant persist (plan autoexec-bat, A6 ; maquette outils_docs/autoexec_bat/,
modele C retenu, avec l'ajout du A : clic sur un avertissement -> sa ligne, survol du point de marge -> son detail).
CSS et HTML inseres dans assistant_persist_page.PAGE a la place des marques /*CSS_AUTOEXEC*/ et <!--VUE_AUTOEXEC-->,
le script (assistant_persist_page_autoexec_js.JS) a la place de /*JS_AUTOEXEC*/.

En haut la carte, le chemin, les comptes, « Annuler les modifications », « Enregistrer… (diff) » ; a gauche le texte
libre et sa marge (numeros, points colores), dessous la liste des avertissements, puis le diff, « Ecrire dans le
depot » et « Envoyer a la carte (OTA)… » ; a droite l'ajout guide (banque, formulaire, apercu, insertion), « Tes
commandes » et l'editeur de modele. Routes : assistant_persist_autoexec.py. Sonde : test_assistant_persist_autoexec_chrome.py.
"""

CSS = r"""
  .onglets{display:flex;gap:4px;border-bottom:1px solid var(--bord);margin-bottom:12px}
  .onglets button{padding:7px 14px;border:1px solid transparent;border-bottom:0;border-radius:6px 6px 0 0;background:none;
    color:var(--doux);font:inherit;cursor:pointer}
  .onglets button[aria-selected=true]{background:var(--carte);border-color:var(--bord);color:var(--texte);font-weight:600}
  .a-tete{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
  .a-tete .droite{margin-left:auto;display:flex;gap:8px}
  .a-col2{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:12px;align-items:start}
  @media (max-width:860px){.a-col2{grid-template-columns:minmax(0,1fr)}}
  .code{font:12.5px/1.6 ui-monospace,Consolas,monospace}
  .a-ed{display:grid;grid-template-columns:58px minmax(0,1fr);height:440px;border:1px solid var(--bord);border-radius:6px;
    background:var(--fond);font:12.5px/20px ui-monospace,Consolas,monospace;overflow:hidden}
  .a-marge{overflow:hidden;padding:4px 0 40px;user-select:none;border-right:1px solid var(--bord)}
  .a-marge div{display:grid;grid-template-columns:36px 22px;height:20px}
  .a-marge .n{color:var(--discret);text-align:right;padding-right:4px}
  .a-marge .p{text-align:center;cursor:help}.a-marge .p.rouge{color:var(--rouge)}.a-marge .p.orange{color:var(--orange)}
  #a-texte{width:100%;height:100%;margin:0;padding:4px 8px;border:0;resize:none;outline:none;background:transparent;
    color:var(--texte);font:inherit;line-height:20px;white-space:pre;overflow:auto}
  #a-texte:disabled{opacity:.5}
  .a-av{display:flex;gap:8px;padding:6px 8px;border-radius:6px;margin-bottom:6px;font-size:13px;align-items:baseline;cursor:pointer}
  .a-av:focus-visible{outline:2px solid var(--bleu)}
  .a-av.r{background:var(--rouge-fond)}.a-av.r b{color:var(--rouge)}
  .a-av.o{background:var(--orange-fond)}.a-av.o b{color:var(--orange)}
  .a-av > b{white-space:nowrap}
  .btn.s{padding:1px 7px;font-size:12px}
  .a-diff{font:12px/1.5 ui-monospace,Consolas,monospace;background:var(--fond);border:1px solid var(--bord);border-radius:6px;
    padding:6px 8px;max-height:300px;overflow:auto;white-space:pre}
  .a-diff .plus{color:var(--vert)}.a-diff .moins{color:var(--rouge)}
  .a-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}
  .a-ajout input[type=text],.a-ajout input[type=number],.a-ajout input[type=time],.a-ajout select{width:100%}
  .a-cmd{border:1px solid var(--bord);border-radius:6px;padding:6px 8px;margin-top:6px;cursor:pointer}
  .a-cmd.choisie{border-color:var(--bleu);background:var(--bleu-fond)}
  .a-l{display:flex;justify-content:space-between;gap:8px;align-items:center}
  .a-l .code{overflow-wrap:anywhere}
  .etiq{display:inline-block;font-size:11px;padding:0 6px;border-radius:8px;border:1px solid var(--bord);color:var(--doux);white-space:nowrap}
  .etiq.u{border-color:var(--bleu);color:var(--bleu)}
  .a-champ{display:grid;grid-template-columns:110px minmax(0,1fr);gap:6px;align-items:center;margin:5px 0;font-size:13px}
  .a-jours{display:flex;gap:5px}.a-jours label{display:flex;flex-direction:column;align-items:center;font-size:11px}
  .a-apercu{background:var(--fond);border:1px dashed var(--btn-bord);border-radius:6px;padding:6px 8px;margin:8px 0;
    overflow-wrap:anywhere;min-height:2.2em}
  .a-ajout h3{font-size:12px;margin:14px 0 4px;color:var(--doux);text-transform:uppercase;letter-spacing:.04em}
  .a-editeur{border-top:1px solid var(--bord);margin-top:12px;padding-top:6px}
  .m-ch{border:1px solid var(--bord);border-radius:6px;padding:4px 6px;margin:6px 0}
  #a-existe-texte{overflow-wrap:anywhere}
  .a-comparaison{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:8px}
"""

HTML = r"""
  <div id="vue-autoexec" role="tabpanel" aria-labelledby="onglet-autoexec" hidden>
    <div class="carte a-tete">
      <label>Carte <select id="a-env"></select></label>
      <span class="discret" id="a-info"></span>
      <span class="droite"><button class="btn" id="a-annuler" type="button" disabled>Annuler les modifications</button>
        <button class="btn p" id="a-enregistrer" type="button" disabled>Enregistrer… (diff)</button></span>
    </div>
    <div id="a-erreur" class="avert rouge" hidden></div>
    <div class="a-col2">
      <div>
        <div class="carte">
          <h2>autoexec.bat</h2>
          <div class="a-ed"><div class="a-marge" id="a-marge"></div><textarea id="a-texte" wrap="off" spellcheck="false"
            aria-label="Contenu de autoexec.bat" disabled></textarea></div>
          <div class="a-actions"><button class="btn" id="a-supprimer" type="button" disabled>Supprimer la ligne</button>
            <span class="discret">celle du curseur, ou de l'avertissement cliqué</span></div>
        </div>
        <div class="carte">
          <h2 id="a-titre-analyse">Analyse</h2>
          <div id="a-erreur-analyse" class="avert rouge" hidden></div>
          <div id="a-avertissements"></div>
        </div>
        <div class="carte">
          <h2>Avant d'enregistrer</h2>
          <div class="a-diff" id="a-diff"></div>
          <p id="a-ligne-rouges" hidden><label><input type="checkbox" id="a-rouges-lus"> <span id="a-rouges-texte"></span></label></p>
          <div class="a-actions"><button class="btn p" id="a-ecrire" type="button" disabled>Écrire dans le dépôt</button>
            <button class="btn" id="a-envoyer" type="button" disabled>Puis envoyer à la carte (OTA)…</button>
            <span class="discret" id="a-envoi-aide"></span></div>
          <div id="a-retours"></div>
        </div>
        <div class="carte" id="a-panneau-envoi" hidden>
          <h2>Envoi à la carte (OTA)</h2>
          <p id="a-envoi-adresse"></p>
          <div id="a-ecart" hidden>
            <p class="avert">Le fichier de la carte diffère de celui du dépôt : il sera remplacé (une copie est gardée sur ce PC).</p>
            <div class="a-comparaison"><div><b>Sur la carte</b><pre class="a-diff" id="a-sur-carte"></pre></div>
              <div><b>Dans le dépôt (envoyé)</b><pre class="a-diff" id="a-sur-depot"></pre></div></div>
            <p><label><input type="checkbox" id="a-ecart-vu"> Remplacer le fichier de la carte</label></p>
          </div>
          <p><label><input type="checkbox" id="a-redemarrer"> Redémarrer la carte ensuite</label>
            <span class="discret">— sinon elle l'exécute au prochain démarrage</span></p>
          <p id="a-envoi-rouges" hidden><label><input type="checkbox" id="a-envoi-rouges-lus"> <span id="a-envoi-rouges-texte"></span></label></p>
          <div class="a-actions"><button class="btn p" id="a-envoi-go" type="button" disabled>Envoyer</button>
            <button class="btn" id="a-envoi-annule" type="button">Fermer</button></div>
          <div id="a-envoi-retours"></div>
        </div>
      </div>
      <div class="carte a-ajout">
        <h2>Ajouter</h2>
        <input type="text" id="a-recherche" placeholder="Chercher dans la banque : minuterie, log, wifi…" autocomplete="off"
          aria-label="Chercher dans la banque">
        <div id="a-banque-erreur" class="avert rouge" hidden></div>
        <div id="a-resultats"></div>
        <div id="a-choix" hidden>
          <h3>Commande choisie</h3>
          <div class="a-l"><span class="code" id="a-choisie"></span><span class="etiq">banque</span></div>
          <div class="discret" id="a-choisie-desc"></div>
          <div id="a-champs"></div>
          <div class="a-apercu code" id="a-apercu"></div>
          <div class="erreur" id="a-ajout-erreur"></div>
          <button class="btn p" id="a-inserer" type="button">Insérer</button>
          <div id="a-existe" class="avert" hidden><span id="a-existe-texte"></span>
            <div class="a-actions"><button class="btn p" id="a-remplacer" type="button">Remplacer par la nouvelle</button>
              <button class="btn" id="a-enlever" type="button">Enlever l'existante</button></div></div>
        </div>
        <h3>Tes commandes</h3>
        <div id="a-perso"></div>
        <p id="a-proposition" hidden><span id="a-proposition-texte"></span>
          <button class="btn s" id="a-en-modele" type="button">En faire un modèle</button></p>
        <p><button class="btn" id="a-nouveau-modele" type="button">Nouveau modèle…</button></p>
        <div id="a-editeur" class="a-editeur" hidden>
          <h3>Modèle de commande</h3>
          <div class="a-champ"><label for="m-nom">Nom</label><input type="text" id="m-nom"></div>
          <div class="a-champ"><label for="m-categorie">Catégorie</label><input type="text" id="m-categorie"></div>
          <div class="a-champ"><label for="m-description">Description</label><input type="text" id="m-description"></div>
          <div class="a-champ"><label for="m-modele">Ligne</label><input type="text" id="m-modele" class="code"></div>
          <p class="discret">Dans la ligne, <code>{clé}</code> = un champ ci-dessous, rempli par le formulaire à l'insertion.</p>
          <div id="m-champs"></div>
          <button class="btn s" id="m-ajout-champ" type="button">+ Champ</button>
          <div class="a-apercu code" id="m-apercu"></div>
          <div id="m-retours"></div>
          <div class="a-actions"><button class="btn p" id="m-enregistre" type="button">Ajouter à la banque</button>
            <button class="btn" id="m-annule" type="button">Annuler</button></div>
        </div>
      </div>
    </div>
  </div>
"""

"""Script de la page « Etiquettes QR code » pour les fiches en ligne (plan A10) : contenu du QR code (texte ou lien),
bouton « Publier les fiches… » (diff puis envoi par POST /publier). Ajoute apres JS (etiquettes_qr_page_js.py), dont il
reprend api, el, avert, montreDiff et sale. textContent seul.
"""

JS_PUBLICATION = r"""
const CONTENUS = [['texte', 'le texte (lu sans réseau)'], ['lien', 'un lien vers la fiche en ligne (publique)']];

function dessineContenu() { options($('contenu'), CONTENUS, ETAT.reglage.contenu || 'texte'); }
$('contenu').onchange = e => {
  ETAT.reglage.contenu = e.target.value;      // ecrit meme pour « texte » : un gabarit en lien ne doit pas l'emporter
  change();
};

async function preparePublication(avant) {
  const z = $('ecriture'), env = ETAT.env, zone = z.firstChild;
  // enchaine apres une ecriture : abandonne si l'utilisateur a fait autre chose entre-temps (fetch jusqu'a 120 s)
  const depasse = () => avant && (ETAT.env !== env || z.firstChild !== zone);
  try {
    const prevu = await api('/publication/diff', {});
    if (depasse()) return;
    z.replaceChildren();
    if (avant) avert(z, avant, 'vert');
    if (prevu.refus.length) {
      z.appendChild(el('h3', {}, 'Publication des fiches refusée'));
      prevu.refus.forEach(r => avert(z, r.env + ' : ' + r.raison, 'rouge'));
      avert(z, 'Retirer ces lignes, écrire le réglage, puis relancer « Publier les fiches… ».');
      return;
    }
    prevu.signaux = ['Fiches PUBLIQUES, lisibles par tous sur ' + prevu.url + ' : '
                     + (prevu.publies.join(', ') || 'aucune carte en mode lien (fiches retirées)') + '.'];
    if (sale()) prevu.signaux.push('Les modifications non écrites de ' + ETAT.env + ' ne sont pas publiées : seuls les réglages écrits comptent.');
    montreDiff(prevu, 'Publication des fiches (branche etiquettes, GitHub Pages)', async empreinte => {
      const r = await api('/publier', {empreinte: empreinte});
      z.replaceChildren();
      avert(z, r.sha ? 'Fiches publiées (' + r.sha.slice(0, 9) + ') : en ligne sur ' + r.url + ' après une minute environ.'
                     : 'Rien à publier : les fiches en ligne sont à jour.', 'vert');
      chargeSuivi();                                   // badges « fiche à republier » recalcules
    }, 'Publier', 'Rien à publier : les fiches en ligne sont à jour.');
    if (avant) z.prepend(el('div', {class: 'avert vert'}, avant));   // montreDiff vide la zone : remis au-dessus
  } catch (e) {
    if (depasse()) return;
    z.replaceChildren();
    if (avant) avert(z, avant, 'vert');              // l'ecriture a reussi : ne pas la laisser croire refusee
    avert(z, 'Publication impossible : ' + e.message, 'rouge');
  }
}
$('btn-publier').onclick = () => preparePublication();

// A11 : GitHub Pages inactif -> bouton d'activation (une fois) ; gh absent ou non connecte : bouton cache, rien d'autre
async function verifiePages() {
  let p;
  try { p = await api('/pages'); } catch (e) { return; }
  $('btn-pages').classList.toggle('cache', p.actif !== false);     // inconnu (gh absent...) : rien a proposer
}
$('btn-pages').onclick = () => {
  const z = $('ecriture');
  z.replaceChildren();
  avert(z, 'Activer GitHub Pages sur la branche etiquettes (une seule fois, après une première publication) : '
           + 'les fiches publiées deviennent lisibles par tous.');
  const ok = el('button', {type: 'button', class: 'btn prim'}, 'Activer');
  const non = el('button', {type: 'button', class: 'btn'}, 'Annuler');
  ok.onclick = async () => {
    ok.disabled = non.disabled = true;
    try {
      const p = await api('/pages/activer', {});
      z.replaceChildren();
      avert(z, 'GitHub Pages activé : ' + (p.url || '') + ' (premier affichage après une à deux minutes).', 'vert');
      $('btn-pages').classList.add('cache');
    } catch (e) { avert(z, 'Activation refusée : ' + e.message, 'rouge'); ok.disabled = non.disabled = false; }
  };
  non.onclick = () => z.replaceChildren();
  const l = el('div', {class: 'ligne'});
  l.append(ok, non);
  z.appendChild(l);
};
verifiePages();
"""

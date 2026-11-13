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

async function preparePublication() {
  const z = $('ecriture');
  try {
    const prevu = await api('/publication/diff', {});
    z.replaceChildren();
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
    }, 'Publier');
  } catch (e) {
    z.replaceChildren();
    avert(z, 'Publication impossible : ' + e.message, 'rouge');
  }
}
$('btn-publier').onclick = preparePublication;
"""

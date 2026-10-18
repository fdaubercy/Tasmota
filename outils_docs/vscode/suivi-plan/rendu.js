// Rendu HTML de la vue « Suivi du plan » - fonctions PURES, sans vscode ni E/S.
// Entree : le resultat de analyse() du parseur (.claude/mods/suivi-plan/hooks/parseur-plan.mjs).
// Tout texte issu du .md est echappe (& < > " ') AVANT d'etre insere.
// Pas d'attribut style : la CSP n'autorise aucun style en ligne. La largeur des barres est
// portee par data-pourcent et appliquee par media/vue.js (CSSOM, permis par la CSP).
// Banc : node outils_docs/vscode/suivi-plan/test_rendu.js (la ligne marquee MUTANT y est
// neutralisee pour verifier que le banc detecte un echappement casse).
'use strict'

const ENTITES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }

function echappe(texte) {
  return String(texte ?? '').replace(/[&<>"']/g, c => ENTITES[c])   // MUTANT:echappe
}

// Texte du .md -> HTML : echappe, puis `code` en <code> (le contenu est deja echappe)
function enLigne(texte) {
  return echappe(texte).replace(/`([^`]+)`/g, '<code>$1</code>')
}

// Entier borne 0..100 (un pourcentage ne vient jamais du texte brut)
function borne(p) {
  const n = Math.round(Number(p))
  return Number.isFinite(n) ? Math.max(0, Math.min(100, n)) : 0
}

function entier(n) {
  const v = Math.trunc(Number(n))
  return Number.isFinite(v) && v > 0 ? v : 0
}

function barre(p, classe) {
  return `<div class="barre ${classe}"><div class="remplissage" data-pourcent="${borne(p)}"></div></div>`
}

// Profondeur visuelle d'une etape : 2 espaces (ou une tabulation) par niveau, 4 au plus
function profondeur(niveau) {
  return Math.min(4, Math.floor(entier(niveau) / 2))
}

function etape(e) {
  const preuve = e.preuve ? `<span class="preuve">preuve : ${enLigne(e.preuve)}</span>` : ''
  return `<li class="etape n${profondeur(e.niveau)}${e.fait ? ' fait' : ''}" data-type="etape" ` +
    `data-ligne="${entier(e.ligne)}" tabindex="0" role="button">` +
    `<span class="case" aria-hidden="true">${e.fait ? '&#9745;' : '&#9744;'}</span>` +
    `<span class="corps"><span class="texte">${enLigne(e.texte)}</span>${preuve}</span></li>`
}

function action(a) {
  const finie = a.total > 0 && a.fait === a.total
  const etapes = a.etapes.length
    ? `<ul class="etapes">${a.etapes.map(etape).join('')}</ul>`
    : '<p class="vide">Aucune sous-étape.</p>'
  return `<article class="action${finie ? ' finie' : ''}">` +
    `<h2 class="action-titre" data-type="action" data-ligne="${entier(a.ligne)}" tabindex="0" role="button">` +
    `<span class="id">${echappe(a.id)}</span> — ${enLigne(a.titre)}</h2>` +
    `<div class="ligne-barre">${barre(a.pourcent, 'petite')}` +
    `<span class="compte">${entier(a.fait)}/${entier(a.total)}</span>` +
    `<span class="pourcent" data-type="pourcent-action">${borne(a.pourcent)} %</span></div>` +
    `${etapes}</article>`
}

function colonne(titre, liste) {
  const items = liste.length
    ? liste.map(x => `<li class="amelioration${x.fait ? ' fait' : ''}" data-type="amelioration" ` +
        `data-ligne="${entier(x.ligne)}" tabindex="0" role="button">${enLigne(x.texte)}</li>`).join('')
    : '<li class="vide">Rien.</li>'
  return `<div class="colonne"><h3>${titre}</h3><ul>${items}</ul></div>`
}

function ameliorations(liste) {
  if (!liste.length) return ''
  const restant = liste.filter(x => !x.fait).length
  return '<section class="ameliorations"><h2>Améliorations restantes ' +
    `<span class="discret">(${restant} sur ${liste.length})</span></h2><div class="colonnes">` +
    colonne('Conversation', liste.filter(x => x.portee === 'conversation')) +
    colonne('Projet', liste.filter(x => x.portee !== 'conversation')) +
    '</div></section>'
}

// @minimum nombre de plans a partir duquel le bouton a un sens (2 quand un plan est deja affiche)
function boutonChoisir(plans, minimum = 2) {
  return Array.isArray(plans) && plans.length >= minimum
    ? `<button class="choisir" data-action="choisir" type="button">Choisir le plan (${plans.length})</button>`
    : ''
}

// Conversation Claude active qui ne suit aucun plan (ou que la vue ne sait pas reconnaitre)
function sansPlan(conversation, plans) {
  return '<section class="aucun"><h1>Aucun plan</h1>' +
    `<p>${enLigne(conversation.message || 'Cette conversation ne suit aucun plan.')}</p>` +
    '<p class="discret">Pour qu\'elle en suive un : <code>/suivi suivre &lt;chantier&gt;</code> dans la conversation.</p>' +
    `${boutonChoisir(plans, 1)}</section>`
}

// Fragment HTML de la vue.
// @a       resultat de analyse(), ou null s'il n'y a aucun plan
// @fichier chemin relatif du plan (tasks/plans/x.md)
// @plans   liste des plans disponibles (seule sa longueur compte ici)
// @options { conversation: { message } } : a null parce que la conversation active ne suit aucun plan
function rendu(a, fichier, plans, options = {}) {
  if (!a && options.conversation) return sansPlan(options.conversation, plans)
  if (!a) {
    return '<section class="aucun"><h1>Aucun plan</h1><p>Aucun fichier <code>.md</code> dans le ' +
      `dossier des plans${fichier ? ' (' + enLigne(fichier) + ')' : ''}. Format : <code>tasks/plans/_FORMAT.md</code>.</p></section>`
  }
  const m = a.meta || {}
  const statut = m.statut || '?'
  const classeStatut = /^(actif|en-pause|clos)$/.test(statut) ? statut : 'inconnu'
  const infos = [
    m.chantier ? `<span class="chantier">${echappe(m.chantier)}</span>` : '',
    `<span class="statut ${classeStatut}">${echappe(statut)}</span>`,
    m.maj ? `<span>maj ${echappe(m.maj)}</span>` : '',
    fichier ? `<span class="fichier" data-type="fichier" data-ligne="1" tabindex="0" role="button">${echappe(fichier)}</span>` : '',
  ].filter(Boolean).join('<span class="sep"> · </span>')
  const global = a.global == null ? '—' : `${borne(a.global)} %`
  const alertes = (a.alertes || []).length
    ? `<ul class="alertes">${a.alertes.map(x => `<li>${enLigne(x)}</li>`).join('')}</ul>` : ''
  return '<header class="entete">' +
    `<h1 class="titre">${enLigne(a.titre || 'Plan sans titre')}</h1>` +
    `<div class="infos">${infos}</div>` +
    barre(a.global == null ? 0 : a.global, 'grande') +
    `<div class="chiffres"><span class="global" data-type="pourcent-global">${global}</span>` +
    `<span class="discret">${entier(a.fait)}/${entier(a.total)} étapes</span>${boutonChoisir(plans)}</div>` +
    `</header>${alertes}` +
    `<section class="actions">${a.actions.map(action).join('')}</section>` +
    ameliorations(a.ameliorations || [])
}

// Document complet de la webview (CSP stricte : aucun style ni script en ligne, script par nonce)
function page(nonce, cspSource, uriCss, uriJs, contenu) {
  const n = echappe(nonce)
  const csp = `default-src 'none'; style-src ${cspSource}; script-src 'nonce-${nonce}'; img-src ${cspSource};`
  return '<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">' +
    `<meta http-equiv="Content-Security-Policy" content="${echappe(csp)}">` +
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">' +
    `<link rel="stylesheet" href="${echappe(uriCss)}"><title>Plan</title></head>` +
    `<body><main id="contenu">${contenu}</main>` +
    `<script nonce="${n}" src="${echappe(uriJs)}"></script></body></html>`
}

module.exports = { rendu, page, echappe }

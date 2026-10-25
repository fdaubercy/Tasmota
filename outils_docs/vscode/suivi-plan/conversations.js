// Reconnaitre la conversation Claude de l'onglet actif - fonctions PURES, sans vscode ni E/S.
// Imite l'extension Claude 2.1.301 (anthropic.claude-code, extension.js, mesure le 2026-10-18) :
//  - un onglet de conversation est une webview « claudeVSCodePanel » dont le libelle est le titre
//    de la session passe par uL1 : sans titre « Claude Code », plus de 25 caracteres -> les 24
//    premiers + « … » (puis n3 coupe a 200, sans effet apres uL1) ;
//  - titre d'une session (fetchSessionsInDir) : customTitle (fin, puis tete du transcript),
//    sinon aiTitle (fin, puis tete), a defaut lastPrompt puis summary (fin). Chaque champ est
//    pris a sa DERNIERE occurrence dans le bloc (D5) ; un bloc = 64 Ko de tete ou de fin ($2).
// Le libelle n'est qu'un titre tronque : deux conversations peuvent le partager. Dans ce cas,
// si elles ne suivent pas le meme plan, rien n'est devine (etat « ambigue »).
// Banc : node outils_docs/vscode/suivi-plan/test_conversations.js (la ligne marquee MUTANT y est
// neutralisee pour verifier que le banc detecte une troncature fausse).
'use strict'

const TAILLE_BLOC = 65536
const SANS_TITRE = 'Claude Code'
const TYPE_ONGLET = 'claudeVSCodePanel'

// Valeur texte de la DERNIERE occurrence de "nom":"..." dans un bloc de JSONL, ou undefined
function champ(bloc, nom) {
  let valeur
  let position = -1
  for (const motif of [`"${nom}":"`, `"${nom}": "`]) {
    let depart = 0
    for (;;) {
      const i = bloc.indexOf(motif, depart)
      if (i < 0) break
      const debut = i + motif.length
      let j = debut
      while (j < bloc.length && bloc[j] !== '"') j += bloc[j] === '\\' ? 2 : 1
      if (j >= bloc.length) break                      // chaine coupee par la fin du bloc
      if (i > position) { valeur = decode(bloc.slice(debut, j)); position = i }
      depart = j + 1
    }
  }
  return valeur
}

function decode(brut) {
  if (!brut.includes('\\')) return brut
  try { return JSON.parse(`"${brut}"`) } catch { return brut }
}

// Titre d'une session a partir des 64 Ko de tete et de fin de son transcript, ou null
function titreSession(tete, fin) {
  const t = String(tete || '')
  const f = String(fin || t)
  return champ(f, 'customTitle') ?? champ(t, 'customTitle') ?? champ(f, 'aiTitle') ?? champ(t, 'aiTitle') ??
    (champ(f, 'lastPrompt') || champ(f, 'summary') || null)
}

// Libelle de l'onglet d'une session de ce titre (regle uL1 de l'extension Claude)
function libelleOnglet(titre) {
  if (!titre) return SANS_TITRE
  return titre.length > 25 ? titre.substring(0, 24) + '…' : titre   // MUTANT:troncature
}

// Conversation rattachee qu'un onglet designe.
// @libelle       libelle de l'onglet Claude actif
// @conversations [{ session, fichier (tasks/plans/x.md | null), titre, horodatage }]
// @returns { etat: 'trouvee', conversation } | { etat: 'ambigue', candidates } | { etat: 'inconnue' }
function apparie(libelle, conversations) {
  const l = String(libelle || '').trim()
  if (!l || l === SANS_TITRE) return { etat: 'inconnue' }
  const candidates = (conversations || []).filter(c => c && c.titre && libelleOnglet(c.titre) === l)
  if (!candidates.length) return { etat: 'inconnue' }
  if (new Set(candidates.map(c => c.fichier ?? null)).size > 1) return { etat: 'ambigue', candidates }
  const conversation = candidates.reduce((a, b) => (Number(b.horodatage) > Number(a.horodatage) ? b : a))
  return { etat: 'trouvee', conversation }
}

// Ouvrir la vue pour la conversation active ? Oui si le reglage le permet, que la vue est fermee, que la
// conversation est reconnue et suit un plan, et qu'elle n'a pas deja eu la vue dans cette fenetre
// (`dejaOuvertes` : sessions ouvertes automatiquement ou dont la vue a ete refermee a la main).
function ouvrirPourConversation(reglage, vueOuverte, conv, dejaOuvertes) {
  return Boolean(reglage && !vueOuverte && conv && conv.session && conv.fichier && !dejaOuvertes.has(conv.session))
}

module.exports = { TAILLE_BLOC, SANS_TITRE, TYPE_ONGLET, champ, titreSession, libelleOnglet, apparie,
  ouvrirPourConversation }

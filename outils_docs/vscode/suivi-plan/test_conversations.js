// Banc de conversations.js (onglet Claude actif -> conversation rattachee) :
//   node outils_docs/vscode/suivi-plan/test_conversations.js        code de sortie 0 = vert
// Verifie :
//   1. libelle d'onglet : regle uL1 de l'extension Claude (25 caracteres, 24 + « … », « Claude Code ») ;
//   2. titre d'une session : customTitle > aiTitle (fin puis tete) > lastPrompt > summary, derniere
//      occurrence, echappements JSON, chaine coupee par la fin du bloc ignoree ;
//   3. appariement : trouvee (la plus recente), ambigue (plans differents), inconnue (« Claude Code ») ;
//   4. INFORMATION : titres et libelles des 5 transcripts les plus recents de ce depot (non compte) ;
//   5. TEMOIN : copie de conversations.js dont la ligne MUTANT:troncature est neutralisee, chargee
//      a part, doit faire echouer le controle du libelle (et la copie intacte, meme montage, le passer).
'use strict'
const fs = require('fs')
const os = require('os')
const path = require('path')
const Module = require('module')

const ICI = __dirname
let nbOk = 0
let nbEchecs = 0
function verifie(nom, ok, info) {
  if (ok) nbOk++
  else nbEchecs++
  console.log(`${ok ? 'OK    ' : 'ECHEC '} ${nom}${ok || !info ? '' : '  -> ' + info}`)
}

function chargeSource(source, nomFichier) {
  const m = new Module(nomFichier, module)
  m.filename = nomFichier
  m.paths = Module._nodeModulePaths(path.dirname(nomFichier))
  m._compile(source, nomFichier)
  return m.exports
}

// Controle du libelle, rejoue sur la copie intacte et sur le mutant
function libelleConforme(c) {
  return c.libelleOnglet('Plan panel sync entre conversations') === 'Plan panel sync entre co…' &&
    c.libelleOnglet('x'.repeat(25)) === 'x'.repeat(25) &&
    c.libelleOnglet('x'.repeat(26)) === 'x'.repeat(24) + '…'
}

const C = require('./conversations')

// 1. Libelle
verifie('libellé : 35 caractères -> 24 + « … »', C.libelleOnglet('Plan panel sync entre conversations') === 'Plan panel sync entre co…')
verifie('libellé : 25 caractères gardés tels quels', C.libelleOnglet('x'.repeat(25)) === 'x'.repeat(25))
verifie('libellé : 26 caractères -> 24 + « … »', C.libelleOnglet('x'.repeat(26)) === 'x'.repeat(24) + '…')
verifie('libellé : sans titre -> « Claude Code »', C.libelleOnglet(null) === 'Claude Code' && C.libelleOnglet('') === 'Claude Code')

// 2. Titre
const ligne = o => JSON.stringify(o)
const tete = [ligne({ type: 'user', message: 'x' }), ligne({ type: 'ai-title', aiTitle: 'Ancien titre' })].join('\n')
const fin = [ligne({ type: 'ai-title', aiTitle: 'Premier' }), ligne({ type: 'x' }), ligne({ type: 'ai-title', aiTitle: 'Titre « courant » \\ "cité"' })].join('\n')
verifie('titre : dernière occurrence de aiTitle, échappements décodés', C.titreSession(tete, fin) === 'Titre « courant » \\ "cité"', C.titreSession(tete, fin))
verifie('titre : aiTitle de la tête si la fin n\'en a pas', C.titreSession(tete, ligne({ type: 'y' })) === 'Ancien titre')
const renomme = fin + '\n' + ligne({ type: 'custom-title', customTitle: 'Renommée' }) + '\n' + ligne({ type: 'ai-title', aiTitle: 'Après' })
verifie('titre : customTitle passe devant aiTitle', C.titreSession(tete, renomme) === 'Renommée')
verifie('titre : customTitle de la tête passe devant aiTitle de la fin', C.titreSession(ligne({ customTitle: 'Tête' }), fin) === 'Tête')
verifie('titre : à défaut lastPrompt, puis summary', C.titreSession('', ligne({ lastPrompt: 'dernier message' })) === 'dernier message' &&
  C.titreSession('', ligne({ summary: 'résumé' })) === 'résumé')
verifie('titre : aucun champ -> null', C.titreSession('', ligne({ type: 'user' })) === null)
verifie('titre : chaîne coupée par la fin du bloc ignorée', C.titreSession('', ligne({ aiTitle: 'Bon' }) + '\n{"type":"ai-title","aiTitle":"Coup') === 'Bon')
verifie('titre : bloc de fin absent (petit fichier) -> la tête sert', C.titreSession(tete, '') === 'Ancien titre')

// 3. Appariement
const convs = [
  { session: 'a', fichier: 'tasks/plans/un.md', titre: 'Plan panel sync entre conversations', horodatage: 10 },
  { session: 'b', fichier: 'tasks/plans/deux.md', titre: 'Graphiques uPlot', horodatage: 20 },
  { session: 'c', fichier: 'tasks/plans/trois.md', titre: 'Titre commun très long numéro 1', horodatage: 30 },
  { session: 'd', fichier: 'tasks/plans/quatre.md', titre: 'Titre commun très long numéro 2', horodatage: 40 },
  { session: 'e', fichier: 'tasks/plans/deux.md', titre: 'Graphiques uPlot', horodatage: 50 },
  { session: 'f', fichier: null, titre: 'Conversation détachée', horodatage: 60 },
]
const t = C.apparie('Plan panel sync entre co…', convs)
verifie('appariement : libellé tronqué -> sa conversation', t.etat === 'trouvee' && t.conversation.session === 'a', JSON.stringify(t))
const m = C.apparie('Graphiques uPlot', convs)
verifie('appariement : même titre, même plan -> la plus récente', m.etat === 'trouvee' && m.conversation.session === 'e')
const amb = C.apparie('Titre commun très long n…', convs)
verifie('appariement : même libellé, plans différents -> ambiguë', amb.etat === 'ambigue' && amb.candidates.length === 2, JSON.stringify(amb))
verifie('appariement : conversation détachée -> trouvée, fichier null', C.apparie('Conversation détachée', convs).conversation?.fichier === null)
verifie('appariement : « Claude Code » -> inconnue', C.apparie('Claude Code', [{ session: 'z', fichier: 'x.md', titre: null }]).etat === 'inconnue')
verifie('appariement : libellé inconnu -> inconnue', C.apparie('Autre chose', convs).etat === 'inconnue')
verifie('appariement : espaces autour du libellé ignorés', C.apparie('  Graphiques uPlot ', convs).etat === 'trouvee')

// 4. Information : vrais transcripts de ce depot (lecture seule, non compte)
try {
  const projets = path.join(os.homedir(), '.claude', 'projects')
  const dossier = fs.readdirSync(projets).find(d => d.toLowerCase() === 'c--users-fdaub-documents-github-tasmota')
  if (dossier) {
    const base = path.join(projets, dossier)
    const recents = fs.readdirSync(base).filter(n => n.endsWith('.jsonl'))
      .map(n => ({ n, t: fs.statSync(path.join(base, n)).mtimeMs })).sort((a, b) => b.t - a.t).slice(0, 5)
    for (const { n } of recents) {
      const fd = fs.openSync(path.join(base, n), 'r')
      try {
        const taille = fs.fstatSync(fd).size
        const b = Buffer.alloc(C.TAILLE_BLOC)
        const lus = fs.readSync(fd, b, 0, C.TAILLE_BLOC, 0)
        const h = b.toString('utf8', 0, lus)
        const lusFin = taille > C.TAILLE_BLOC ? fs.readSync(fd, b, 0, C.TAILLE_BLOC, taille - C.TAILLE_BLOC) : 0
        const f = taille > C.TAILLE_BLOC ? b.toString('utf8', 0, lusFin) : h
        console.log(`INFO   ${n.slice(0, 8)} : « ${C.libelleOnglet(C.titreSession(h, f))} »`)
      } finally { fs.closeSync(fd) }
    }
  }
} catch (e) { console.log('INFO   transcripts illisibles :', e.message) }

// 4 bis. Ouverture automatique de la vue pour la conversation active qui suit un plan
{
  const suit = { session: 's1', fichier: 'tasks/plans/x.md' }
  const f = C.ouvrirPourConversation
  verifie('ouverture auto : conversation qui suit un plan, vue fermée -> ouvre', f === undefined ? false : f(true, false, suit, new Set()))
  if (f) {
    verifie('ouverture auto : vue déjà ouverte -> rien', !f(true, true, suit, new Set()))
    verifie('ouverture auto : réglage coupé -> rien', !f(false, false, suit, new Set()))
    verifie('ouverture auto : aucun plan suivi -> rien', !f(true, false, { session: 's1', fichier: null }, new Set()))
    verifie('ouverture auto : conversation non reconnue -> rien', !f(true, false, { session: null, fichier: null }, new Set()) && !f(true, false, null, new Set()))
    verifie('ouverture auto : déjà ouverte (ou refermée à la main) pour cette conversation -> rien', !f(true, false, suit, new Set(['s1'])))
    verifie('ouverture auto : une autre conversation déjà vue ne bloque pas celle-ci', f(true, false, suit, new Set(['s2'])))
  }
}

// 5. Temoin
const source = fs.readFileSync(path.join(ICI, 'conversations.js'), 'utf8')
const lignes = source.split('\n')
const iMutant = lignes.findIndex(l => l.includes('MUTANT:troncature'))
verifie('témoin : ligne MUTANT:troncature trouvée', iMutant >= 0)
if (iMutant >= 0) {
  const intacte = chargeSource(source, path.join(ICI, '_intacte_conversations.js'))
  lignes[iMutant] = '  return titre'
  const mutant = chargeSource(lignes.join('\n'), path.join(ICI, '_mutant_conversations.js'))
  verifie('témoin : copie intacte (même montage) conforme', libelleConforme(intacte))
  verifie('témoin : mutant (troncature supprimée) détecté', !libelleConforme(mutant))
}

console.log(`\n${nbOk} OK, ${nbEchecs} ECHEC(S)`)
process.exit(nbEchecs ? 1 : 0)

// Suivi des plans de travail : tasks/plans/<chantier>.md (format : tasks/plans/_FORMAT.md).
//
// - ExitPlanMode approuve : plan recopie dans tasks/plans/ (coches gardees s'il est revalide), le modele
//   recoit « Plan suivi : ... », la vue VS Code est demandee par le fichier signal ;
// - rappel complet du mode plan : consigne de format ajoutee ;
// - premier message de chaque conversation : bloc « suiviPlan » (plans actifs, prochaines etapes) ;
// - Edit/Write d'un plan : rappel doux si une etape est cochee sans « — preuve : » ;
// - ligne d'avancement ($.ui.status, plan de la conversation d'abord) : session.start, turn.complete,
//   apres edition, toutes les 30 s ;
// - commande /suivi (resume, liste, activer, clore, ouvrir, suivre, detacher) ;
// - plan de la conversation : rattache par ExitPlanMode, Edit/Write d'un plan, /suivi ouvrir|suivre,
//   lache par /suivi detacher ; a chaque message envoye, signal sans ouverture (la vue suit la conversation).
// Garde : installe pour tous les projets, le mod n'agit que si <racine>/tasks/plans existe.
// Contrat avec l'extension fdaubercy.suivi-plan, sous <USERPROFILE>/.claude/suivi-plan/ :
//   signal.json = { "racine": "<racine, barres />", "fichier": "tasks/plans/<x>.md" | null,
//                   "horodatage": <Date.now()>, "session": "<id>", "ouvrir": true|false }
//     (fichier null = la conversation ne suit aucun plan ; ouvrir absent = true)
//   conversations/<id>.json = { "session": "<id>", "racine": "...", "fichier": "..." | null, "horodatage": <ms> }
//     (un fichier par conversation : deux conversations n'ecrivent jamais le meme fichier)
// Aucun processus ni reseau. Parseur : ./parseur-plan.mjs (source unique, banc tests/test_parseur.mjs).
// L'hote lit on(...) et $.nom.methode(...) dans le source : les ecrire en toutes lettres ; les aides
// qui recoivent $ sont des fonctions de premier niveau.

import { analyse, ligneStatut, resume, slug, enPlanSuivi, fusionneCoches } from "./parseur-plan.mjs";

const DOSSIER = "tasks/plans";
const PERIODE = 30000;              // relecture des plans pour la ligne d'avancement
const REGLE = "Règle : coche une étape seulement après l'avoir vérifiée, avec « — preuve : … » (commit, fichier:ligne, sortie d'un banc), et mets à jour maj:.";
const CONSIGNE = [
  "Format du plan (suivi par le mod suivi-plan, référence : tasks/plans/_FORMAT.md) :",
  "- en-tête YAML entre deux lignes --- : chantier: <nom-court>, titre: <titre>, statut: actif ;",
  "- une action par titre « ## A1 — Titre de l'action », chacune avec ses sous-étapes « - [ ] … » (vérifiables) ;",
  "- une section « ## Améliorations restantes » dont chaque case est étiquetée [conversation] ou [projet] ;",
  "- le contexte et la vérification en texte libre (non comptés).",
  "Le plan approuvé sera recopié dans tasks/plans/<chantier>.md ; une étape ne se coche qu'avec « — preuve : … ».",
].join("\n");

// Etat du module, perdu au rechargement a chaud : minuterie et commande sont reprises au tour suivant.
let minuterie = null;
let commandeFaite = false;
const cache = new Map();            // chemin -> { mtimeMs, texte, a }

export function register(on) {
  on("session.start", async ($, e, next) => {
    const resultat = await next(e);
    const racine = await racineSuivie($);
    if (racine) await entretien($, racine);
    return resultat;
  });

  on("turn.complete", async ($, e, next) => {
    const resultat = await next(e);
    const racine = e.agentId ? null : await racineSuivie($);
    if (racine) await entretien($, racine);
    return resultat;
  });

  on("tool.call", { tool: "ExitPlanMode" }, async ($, e, next) => {
    const r = await next(e);
    const res = r.result;
    if (e.agentId || r.deny !== undefined || r.isError || !res?.plan || res.isAgent || res.awaitingLeaderApproval) return r;
    const racine = await racineSuivie($);
    if (!racine) return r;
    const notes = await recopiePlan($, racine, res);
    await majStatut($, racine);
    return { ...r, context: [...(r.context ?? []), ...notes] };
  }).catch(($, e, next) => next(e));

  on("tool.call", { tool: ["Edit", "Write", "MultiEdit"] }, async ($, e, next) => {
    const cible = typeof e.file_path === "string" ? await planVise($, e.file_path) : null;
    if (!cible) return next(e);
    const avant = await lis($, cible.chemin);
    const r = await next(e);
    if (r.deny !== undefined || r.isError) return r;
    cache.delete(cible.chemin);
    const apres = await lis($, cible.chemin);
    if (apres !== null && !e.agentId) await ecrisRattachement($, cible.racine, cible.fichier);
    if (avant === null && apres !== null) await ecrisSignal($, cible.racine, cible.fichier);   // plan cree
    await majStatut($, cible.racine);
    const sansPreuve = apres === null ? [] : cocheesSansPreuve(avant, apres);
    if (!sansPreuve.length) return r;
    const note = `Étape cochée sans preuve dans ${cible.fichier} : ${sansPreuve.map((t) => `« ${t} »`).join(", ")}. ` +
      "Ajoute « — preuve : … » (commit, fichier:ligne, sortie d'un banc), ou décoche-la si elle n'est pas vérifiée.";
    return { ...r, context: [...(r.context ?? []), note] };
  }).catch(($, e, next) => next(e));

  on("prompt.attachment", { type: "plan_mode" }, async ($, e, next) => {
    const r = await next(e);
    if (e.agentId || e.detail?.reminder !== "full" || typeof r.text !== "string") return r;
    return (await racineSuivie($)) ? { ...r, text: `${r.text}\n\n${CONSIGNE}` } : r;
  });

  // Message envoye dans cette conversation : la vue affiche son plan (ou « aucun plan »), sans s'ouvrir.
  // Signal ecrit AVANT next : apres, il partait 3,6 s plus tard (mesure le 2026-10-18), souvent
  // une fois l'utilisateur passe sur un autre onglet. Une commande /suivi ecrit son propre signal.
  on("prompt.submit", async ($, e, next) => {
    if (!e.isMeta && !e.command) {
      const racine = await racineSuivie($);
      if (racine) await ecrisSignal($, racine, await planRattache($, racine), { ouvrir: false });
    }
    return next(e);
  }).catch(($, e, next) => next(e));

  on("prompt.context", async ($, e, next) => {
    const r = await next(e);
    const racine = await racineSuivie($);
    const texte = racine ? await blocContexte($, racine) : "";
    return texte ? { ...r, blocks: [...r.blocks, { name: "suiviPlan", text: texte }] } : r;
  });

  // Commande enregistree par ce module : le hook repond lui-meme, sans next.
  on("command.run", { command: "suivi" }, async ($, e) => ({ text: await commandeSuivi($, String(e.args ?? "").trim()) }));
}

// ---------- garde, lecture des plans, ligne d'avancement ----------

// Racine de la session (barres /) si elle contient tasks/plans, sinon null.
async function racineSuivie($) {
  try {
    const racine = (await $.session.root()).replace(/\\/g, "/").replace(/\/+$/, "");
    return (await $.fs.exists(`${racine}/${DOSSIER}`)) ? racine : null;
  } catch {
    return null;
  }
}

async function lis($, chemin) {
  return (await $.fs.exists(chemin).catch(() => false)) ? $.fs.read(chemin).catch(() => null) : null;
}

// Plans du dossier (hors _*.md), le plus recemment modifie d'abord ; relus si leur mtime a change.
async function lisPlans($, racine) {
  const entrees = await $.fs.list(`${racine}/${DOSSIER}`).catch(() => []);
  const plans = [];
  for (const en of entrees) {
    if (en.kind !== "file" || !/\.md$/i.test(en.name) || en.name.startsWith("_")) continue;
    const chemin = `${racine}/${DOSSIER}/${en.name}`;
    let connu = cache.get(chemin);
    if (!connu || connu.mtimeMs !== en.mtimeMs || !en.mtimeMs) {
      const texte = await lis($, chemin);
      if (texte === null) continue;
      connu = { mtimeMs: en.mtimeMs, texte, a: analyse(texte) };
      cache.set(chemin, connu);
    }
    plans.push({ nom: en.name.replace(/\.md$/i, ""), chemin, fichier: `${DOSSIER}/${en.name}`, mtimeMs: en.mtimeMs, texte: connu.texte, a: connu.a });
  }
  return plans.sort((x, y) => y.mtimeMs - x.mtimeMs);
}

const actifs = (plans) => plans.filter((p) => p.a.meta.statut === "actif");

// Ligne d'avancement : le plan suivi par cette conversation (quel que soit son statut), sinon le
// plus recent des plans actifs.
async function majStatut($, racine) {
  const plans = await lisPlans($, racine);
  const suivi = await planRattache($, racine);
  const p = plans.find((x) => x.fichier === suivi) ?? actifs(plans)[0];
  $.ui.status(p ? ligneStatut(p.a, p.a.meta.chantier || p.nom) : undefined);
}

// Commande, ligne d'avancement et minuterie, remises en place apres un rechargement a chaud.
async function entretien($, racine) {
  if (!commandeFaite) {
    try {
      await $.command.register({
        name: "suivi",
        description: "Plan de la conversation : résumé, ouvrir, suivre, detacher, activer, clore, liste",
        argumentHint: "[ouvrir|suivre <chantier>|detacher|activer <chantier>|clore [<chantier>]|liste]",
      });
      commandeFaite = true;
    } catch {
      // session pas encore liee : nouvel essai au prochain tour
    }
  }
  await majStatut($, racine);
  if (!minuterie) {
    minuterie = $.clock.every(PERIODE, () => {
      racineSuivie($).then((r) => (r ? majStatut($, r) : $.ui.status(undefined))).catch(() => {});
    });
  }
}

// ---------- recopie d'un plan approuve ----------

function dateDuJour() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

async function recopiePlan($, racine, res) {
  const source = String(res.filePath ?? "").split(/[\\/]/).pop() ?? "";
  const brut = analyse(res.plan);
  const date = dateDuJour();
  const base = slug(brut.meta.chantier || brut.titre);
  let nom = base;
  let texte = null;
  for (let n = 2; n < 100; n++) {
    const ancien = await lis($, `${racine}/${DOSSIER}/${nom}.md`);
    if (ancien === null) break;
    const a = analyse(ancien);
    // Meme plan : meme fichier d'origine, sinon meme chantier declare, sinon meme titre sans origine.
    const meme = source ? a.meta.source === source
      : brut.meta.chantier ? a.meta.chantier === brut.meta.chantier : !a.meta.source && a.titre === brut.titre;
    if (meme) {
      texte = fusionneCoches(ancien, enPlanSuivi(res.plan, { source, date, chantier: nom }));
      break;
    }
    nom = `${base}-${n}`;                                      // nom pris par un autre plan
  }
  texte = modifieEntete(texte ?? enPlanSuivi(res.plan, { source, date, chantier: nom }), { chantier: nom });
  const fichier = `${DOSSIER}/${nom}.md`;
  await $.fs.write(`${racine}/${fichier}`, texte);
  cache.delete(`${racine}/${fichier}`);
  await ecrisRattachement($, racine, fichier);
  await ecrisSignal($, racine, fichier);
  const a = analyse(texte);
  const notes = [`Plan suivi : ${fichier} (${a.actions.length} actions, ${a.global ?? 0} %). ` +
    "Coche chaque étape vérifiée avec « — preuve : … » et mets à jour maj:."];
  if (!a.actions.length) {
    notes.push(`Ce plan n'a aucune action « ## A1 — titre » avec des sous-étapes « - [ ] » : réécris-le au format de ${DOSSIER}/_FORMAT.md avant de commencer.`);
  }
  return notes;
}

// Remplace (ou ajoute) des champs de l'en-tete --- de tete, en gardant les fins de ligne du fichier.
function modifieEntete(texte, champs) {
  const fin = /\r\n/.test(texte) ? "\r\n" : "\n";
  const lignes = texte.split(/\r?\n/);
  let ferme = lignes[0] === "---" ? lignes.indexOf("---", 1) : -1;
  if (ferme < 0) {
    lignes.unshift("---", "---");
    ferme = 1;
  }
  for (const [cle, valeur] of Object.entries(champs)) {
    const i = lignes.slice(1, ferme).findIndex((l) => new RegExp(`^${cle}\\s*:`).test(l));
    if (i >= 0) lignes[i + 1] = `${cle}: ${valeur}`;
    else lignes.splice(ferme++, 0, `${cle}: ${valeur}`);
  }
  return lignes.join(fin);
}

// Dossier d'echange avec l'extension (<USERPROFILE>/.claude/suivi-plan, barres /), ou null.
// Peut rejeter : les appelants l'enveloppent d'un try.
async function dossierEchange($) {
  const profil = (await $.env.get("USERPROFILE")) ?? (await $.env.get("HOME"));
  return profil ? `${profil.replace(/\\/g, "/").replace(/\/+$/, "")}/.claude/suivi-plan` : null;
}

// Identifiant de la conversation (nom de son transcript), ou null : rien n'est alors rattache.
async function idSession($) {
  try {
    const id = await $.session.id();
    return /^[A-Za-z0-9-]{1,80}$/.test(id) ? id : null;
  } catch {
    return null;
  }
}

// @fichier plan a afficher (tasks/plans/x.md), ou null : « cette conversation ne suit aucun plan »
// @ouvrir  false : la vue est mise a jour si elle est ouverte, sans s'ouvrir (message envoye)
async function ecrisSignal($, racine, fichier, { ouvrir = true } = {}) {
  try {
    const dossier = await dossierEchange($);
    if (!dossier) return;
    const signal = { racine, fichier, horodatage: Date.now(), session: await idSession($), ouvrir };
    await $.fs.write(`${dossier}/signal.json`, JSON.stringify(signal, null, 2) + "\n");
  } catch {
    // la vue ne s'ouvrira pas d'elle-meme : /suivi ouvrir donne le lien
  }
}

// Plan suivi par cette conversation (fichier null = detachee) : lu par l'extension a chaque
// changement d'onglet de conversation.
async function ecrisRattachement($, racine, fichier) {
  try {
    const [dossier, session] = [await dossierEchange($), await idSession($)];
    if (!dossier || !session) return;
    const r = { session, racine, fichier, horodatage: Date.now() };
    await $.fs.write(`${dossier}/conversations/${session}.json`, JSON.stringify(r, null, 2) + "\n");
  } catch {
    // la vue ne suivra pas cette conversation ; /suivi suivre <chantier> pour reessayer
  }
}

// Plan rattache a cette conversation pour cette racine (tasks/plans/x.md), sinon null.
async function planRattache($, racine) {
  try {
    const [dossier, session] = [await dossierEchange($), await idSession($)];
    if (!dossier || !session) return null;
    const chemin = `${dossier}/conversations/${session}.json`;
    const r = JSON.parse(await lis($, chemin) ?? "null");
    const memeRacine = String(r?.racine ?? "").toLowerCase() === racine.toLowerCase();
    return memeRacine && typeof r.fichier === "string" && (await $.fs.exists(`${racine}/${r.fichier}`)) ? r.fichier : null;
  } catch {
    return null;
  }
}

// ---------- edition d'un plan ----------

// { racine, chemin, fichier } si le chemin edite est un plan (tasks/plans/<x>.md, hors _*.md), sinon null.
async function planVise($, cheminEdite) {
  const racine = await racineSuivie($);
  if (!racine) return null;
  let p = cheminEdite.replace(/\\/g, "/");
  if (!/^([A-Za-z]:)?\//.test(p)) p = `${racine}/${p.replace(/^\.\//, "")}`;
  const prefixe = `${racine}/${DOSSIER}/`;
  if (!p.toLowerCase().startsWith(prefixe.toLowerCase())) return null;
  const reste = p.slice(prefixe.length);
  if (!/^[^/]+\.md$/i.test(reste) || reste.startsWith("_")) return null;
  return { racine, chemin: p, fichier: `${DOSSIER}/${reste}` };
}

const cleEtape = (texte) => texte.replace(/\s+/g, " ").trim().toLowerCase();

// Textes (3 au plus) des etapes passees de non faites (ou absentes) a faites, sans preuve.
function cocheesSansPreuve(avant, apres) {
  const dejaFaites = new Set();
  for (const act of avant === null ? [] : analyse(avant).actions) {
    for (const et of act.etapes) if (et.fait) dejaFaites.add(cleEtape(et.texte));
  }
  const r = [];
  for (const act of analyse(apres).actions) {
    for (const et of act.etapes) if (et.fait && !et.preuve && !dejaFaites.has(cleEtape(et.texte))) r.push(et.texte.slice(0, 80));
  }
  return r.slice(0, 3);
}

// ---------- contexte des conversations et commande /suivi ----------

// Le plan suivi par cette conversation d'abord (annonce comme tel, meme clos), puis les plans actifs
// les plus recents : 2 plans au plus, et la regle de coche ; 25 lignes au plus ; "" sans aucun plan.
async function blocContexte($, racine) {
  const tous = await lisPlans($, racine);
  const fichierSuivi = await planRattache($, racine);
  const rattache = tous.find((p) => p.fichier === fichierSuivi);
  const plans = [...(rattache ? [rattache] : []), ...actifs(tous).filter((p) => p !== rattache)].slice(0, 2);
  if (!plans.length) return "";
  const lignes = plans.flatMap((p) => [
    ...(p === rattache ? ["Plan suivi par cette conversation :"] : []),
    ...resume(p.a, p.fichier).split("\n").slice(0, plans.length > 1 ? 11 : 23),
  ]);
  return [...lignes.slice(0, 24), REGLE].join("\n");
}

async function commandeSuivi($, args) {
  const racine = await racineSuivie($);
  if (!racine) return `Pas de dossier ${DOSSIER} dans ce projet : rien à suivre.`;
  const plans = await lisPlans($, racine);
  const [action = "", ...reste] = args.split(/\s+/).filter(Boolean);
  const voulu = reste.join(" ");
  const trouve = (c) => plans.find((p) => p.nom === c || p.a.meta.chantier === c);
  const liste = plans.length
    ? plans.map((p) => `- ${p.a.meta.chantier || p.nom} · ${p.a.meta.statut || "?"} · ${p.a.global ?? 0} % (${p.fichier})`).join("\n")
    : `Aucun plan dans ${DOSSIER}/.`;
  const actif = actifs(plans)[0];
  const rattache = await planRattache($, racine);          // plan suivi par cette conversation, ou null
  const introuvable = `Plan « ${voulu} » introuvable.\n${liste}`;
  if (action === "") {
    const p = plans.find((x) => x.fichier === rattache) ?? actif;
    return p ? resume(p.a, p.fichier) : `Aucun plan actif.\n${liste}`;
  }
  if (action === "liste") return liste;
  if (action === "activer" || action === "clore") {
    const p = voulu ? trouve(voulu) : action === "clore" ? actif : null;
    if (!p) return voulu ? introuvable : `Usage : /suivi ${action === "activer" ? "activer <chantier>" : "clore [<chantier>] (aucun plan actif)"}`;
    const statut = action === "activer" ? "actif" : "clos";
    await $.fs.write(p.chemin, modifieEntete(p.texte, { statut, maj: dateDuJour() }));
    cache.delete(p.chemin);
    await majStatut($, racine);
    return `Plan ${p.a.meta.chantier || p.nom} : statut ${statut} (${p.fichier}).`;
  }
  if (action === "ouvrir" || action === "suivre") {
    const p = voulu ? trouve(voulu) : action === "ouvrir" ? plans.find((x) => x.fichier === rattache) ?? actif ?? plans[0] : null;
    if (!p) return voulu ? introuvable : action === "suivre" ? `Usage : /suivi suivre <chantier>\n${liste}` : `Aucun plan dans ${DOSSIER}/.`;
    await ecrisRattachement($, racine, p.fichier);
    await ecrisSignal($, racine, p.fichier);
    await majStatut($, racine);
    const lien = `Lien : vscode://fdaubercy.suivi-plan/ouvrir?fichier=${DOSSIER}/${encodeURIComponent(p.nom)}.md`;
    return action === "suivre"
      ? `Cette conversation suit ${p.fichier} : la vue l'affiche quand vous revenez sur son onglet.\n${lien}`
      : `Vue demandée pour ${p.fichier} (plan suivi par cette conversation).\n${lien}`;
  }
  if (action === "detacher") {
    await ecrisRattachement($, racine, null);
    await ecrisSignal($, racine, null, { ouvrir: false });
    await majStatut($, racine);
    return rattache
      ? `Cette conversation ne suit plus ${rattache} (le plan lui-même est inchangé). /suivi suivre <chantier> pour en reprendre un.`
      : "Cette conversation ne suivait aucun plan.";
  }
  return "Usage : /suivi [ouvrir [<chantier>]|suivre <chantier>|detacher|activer <chantier>|clore [<chantier>]|liste]";
}

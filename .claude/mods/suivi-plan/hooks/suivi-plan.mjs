// Suivi des plans de travail : tasks/plans/<chantier>.md (format : tasks/plans/_FORMAT.md).
//
// - ExitPlanMode approuve : plan recopie dans tasks/plans/ (coches gardees s'il est revalide), le modele
//   recoit « Plan suivi : ... », la vue VS Code est demandee par le fichier signal ;
// - rappel complet du mode plan : consigne de format ajoutee ;
// - premier message de chaque conversation : bloc « suiviPlan » (plans actifs, prochaines etapes) ;
// - Edit/Write d'un plan : rappel doux si une etape est cochee sans « — preuve : » ;
// - ligne d'avancement ($.ui.status) : session.start, turn.complete, apres edition, toutes les 30 s ;
// - commande /suivi (resume, liste, activer, clore, ouvrir).
// Garde : installe pour tous les projets, le mod n'agit que si <racine>/tasks/plans existe.
// Signal (contrat avec l'extension fdaubercy.suivi-plan) : <USERPROFILE>/.claude/suivi-plan/signal.json
//   = { "racine": "<racine, barres />", "fichier": "tasks/plans/<x>.md", "horodatage": <Date.now()> }
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

async function majStatut($, racine) {
  const actif = actifs(await lisPlans($, racine))[0];
  $.ui.status(actif ? ligneStatut(actif.a, actif.a.meta.chantier || actif.nom) : undefined);
}

// Commande, ligne d'avancement et minuterie, remises en place apres un rechargement a chaud.
async function entretien($, racine) {
  if (!commandeFaite) {
    try {
      await $.command.register({
        name: "suivi",
        description: "Avancement du plan actif : résumé, ouvrir, activer, clore, liste",
        argumentHint: "[ouvrir|activer <chantier>|clore [<chantier>]|liste]",
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

async function ecrisSignal($, racine, fichier) {
  try {
    const profil = (await $.env.get("USERPROFILE")) ?? (await $.env.get("HOME"));
    if (!profil) return;
    const chemin = `${profil.replace(/\\/g, "/").replace(/\/+$/, "")}/.claude/suivi-plan/signal.json`;
    await $.fs.write(chemin, JSON.stringify({ racine, fichier, horodatage: Date.now() }, null, 2) + "\n");
  } catch {
    // la vue ne s'ouvrira pas d'elle-meme : /suivi ouvrir donne le lien
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

// Plans actifs (2 au plus, les plus recents) et la regle de coche : 25 lignes au plus ; "" sans plan actif.
async function blocContexte($, racine) {
  const plans = actifs(await lisPlans($, racine)).slice(0, 2);
  if (!plans.length) return "";
  const lignes = plans.flatMap((p) => resume(p.a, p.fichier).split("\n").slice(0, plans.length > 1 ? 12 : 24));
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
  const introuvable = `Plan « ${voulu} » introuvable.\n${liste}`;
  if (action === "") return actif ? resume(actif.a, actif.fichier) : `Aucun plan actif.\n${liste}`;
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
  if (action === "ouvrir") {
    const p = voulu ? trouve(voulu) : actif ?? plans[0];
    if (!p) return voulu ? introuvable : `Aucun plan dans ${DOSSIER}/.`;
    await ecrisSignal($, racine, p.fichier);
    return `Vue demandée pour ${p.fichier}.\nLien : vscode://fdaubercy.suivi-plan/ouvrir?fichier=${DOSSIER}/${encodeURIComponent(p.nom)}.md`;
  }
  return "Usage : /suivi [ouvrir [<chantier>]|activer <chantier>|clore [<chantier>]|liste]";
}

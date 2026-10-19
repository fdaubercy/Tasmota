// Meteo du contexte : barre de remplissage de la fenetre de contexte et cout de la session,
// avec un bouton « Préparer la passation » (/fin-de-session) a partir de SEUIL %.
//
// Derive du mod d'exemple token-weather (anthropics/claude-code-playground, Apache-2.0).
// Aucun processus lance, aucun reseau, aucune ecriture : seulement $.session.usage() et l'UI.
//
// Ou c'est dessine (reference des mods, « Render sites », VS Code v2.1.299+) :
// - terminal (y compris le terminal integre de VS Code) : bande AbovePrompt, juste au-dessus
//   du prompt, bouton compris des que le seuil est franchi ;
// - panneau Claude de VS Code : la doc (v2.1.299) dit qu'AbovePrompt n'y est PAS dessinee. A
//   defaut, la barre passe par $.ui.status (ligne du mod pres du prompt, texte seul) ; au
//   franchissement du seuil, un toast et un pane « Passation » portent le bouton.
//   Constate le 2026-10-18 avec l'extension 2.1.301 : deux barres a l'ecran, donc la bande y est
//   bien dessinee. Des que la bande est rendue (bandeVue), la ligne de statut est retiree et le
//   pane n'est plus ouvert : la bande porte deja le bouton.
// Rafraichi a chaque fin de tour (pas pendant la generation : usage() ne bouge qu'a chaque reponse).
//
// L'hote lit on(...) et $.nom.methode(...) dans le source : les ecrire en toutes lettres, et les
// aides qui recoivent $ sont des fonctions de premier niveau.

const SEUIL = 45;            // % de contexte a partir duquel le bouton apparait (50 le 2026-10-18, 45 depuis)
const CASES = 20;            // largeur de la barre
const COMMANDE = "fin-de-session";
const PANE = "passation";

const METEO = [
  // Symboles a largeur simple, pas d'emoji : ils s'alignent dans toutes les polices.
  { jusqua: 25, icone: "☀", mot: "Beau", couleur: "green" },
  { jusqua: 50, icone: "☁", mot: "Nuageux", couleur: "cyan" },
  { jusqua: 75, icone: "☂", mot: "Averses", couleur: "yellow" },
  { jusqua: 90, icone: "☇", mot: "Orage", couleur: "magenta" },
  { jusqua: Infinity, icone: "↯", mot: "Compactage proche", couleur: "red" },
];

// Derniere lecture : { tokens, fenetre, pourcent, usd } ; null avant la premiere reponse.
let lecture = null;
let dejaPropose = false;     // toast + pane une seule fois par franchissement du seuil
let bandeVue = false;        // la bande AbovePrompt a ete rendue : pas de ligne de statut ni de pane

export function register(on) {
  on("session.start", async ($, e, next) => {
    const resultat = await next(e);
    lecture = null;
    dejaPropose = false;
    await lire($);
    return resultat;
  });

  on("turn.complete", async ($, e, next) => {
    const resultat = await next(e);
    if (!e.agentId) {
      await lire($);
    }
    return resultat;
  });

  on("session.measure", async ($, e, next) => {
    const resultat = await next(e);
    await lire($);
    return resultat;
  });

  on("ui.render", { component: "AbovePrompt" }, ($, e, next) => {
    if (e.hasSurvey || !lecture) {
      return next(e);
    }
    bandeVue = true;
    const { Box, Text, Button } = $.ui.resolve(e);
    const elements = ligne(Text, e.bodyColumns ?? 80);
    if (lecture.pourcent >= SEUIL) {
      elements.push(Text({ children: "  " }));
      elements.push(Button({ label: "Préparer la passation", onPress: () => passation($) }));
    }
    return Box({ flexDirection: "row", paddingX: 1, children: elements });
  });

  // L'id passe a $.ui.open devient le requestId du rendu.
  on("ui.render", { component: "Pane", requestId: PANE }, ($, e, next) => {
    if (!lecture) {
      return next(e);
    }
    const { Box, Text, Button } = $.ui.resolve(e);
    return Box({
      flexDirection: "column",
      paddingX: 1,
      children: [
        // La barre est deja sur la ligne de statut : le pane ne la repete pas.
        Text({ bold: true, children: `Contexte à ${lecture.pourcent} % : préparer la passation ?` }),
        Text({ dimColor: true, children: "Mettre à jour la reprise, les leçons et écrire le mini-export pour une nouvelle conversation." }),
        Button({ label: "Préparer la passation", onPress: () => passation($) }),
      ],
    });
  });
}

async function lire($) {
  try {
    const { context, cost } = await $.session.usage();
    if (!context || !context.window) {
      return;
    }
    const tokens = context.tokens ?? 0;
    if (tokens === 0 && lecture) {
      return; // lecture de session.start avant toute reponse : garder la derniere
    }
    const pourcent = Math.round(context.percent ?? (tokens / context.window) * 100);
    lecture = { tokens, fenetre: context.window, pourcent, usd: cost?.usd };
    $.ui.invalidate("ui.render");
    await surfacesHorsTerminal($);
    await seuil($);
  } catch {
    // Pas de lecture ce tour-ci : l'affichage garde la precedente.
  }
}

// Ligne de statut seulement la ou la bande n'est pas dessinee (doublon sinon).
async function surfacesHorsTerminal($) {
  if (bandeVue) {
    $.ui.status(undefined);
    return;
  }
  const surfaces = await $.session.surfaces();
  if (surfaces.some((s) => s !== "terminal" && s !== "desktop")) {
    $.ui.status(texteBarre());
  }
}

// Au-dela du seuil, le bouton est TOUJOURS visible (demande du 2026-10-18) : dans la bande s'il y en a
// une (redessinee a chaque tour), sinon dans le pane, rouvert a chaque tour s'il a ete ferme.
// Seul le toast est unique par franchissement.
async function seuil($) {
  if (lecture.pourcent < SEUIL) {
    dejaPropose = false;     // repasse sous le seuil (compactage, /clear) : on re-arme
    return;
  }
  if (!dejaPropose) {
    dejaPropose = true;
    $.ui.toast(`Contexte à ${lecture.pourcent} % : pensez à préparer la passation (/${COMMANDE}).`);
  }
  if (bandeVue) {
    return; // la bande porte deja le bouton
  }
  try {
    await $.ui.open({ id: PANE, title: "Passation", rows: 3 }); // id deja ouvert : simple retitrage
  } catch {
    // Pane refuse ou trop etroit : le toast reste le seul signal.
  }
}

async function passation($) {
  try {
    await $.command.run({ command: COMMANDE });
  } catch {
    // Nom refuse (commande de projet non vue par command.run) : pre-remplir, Entree pour lancer.
    await $.prompt.fill({ text: `/${COMMANDE} ` });
    $.ui.toast(`/${COMMANDE} est prête dans la zone de saisie : Entrée pour la lancer.`);
  }
  try {
    await $.ui.close({ id: PANE });
  } catch {
    // deja ferme
  }
}

function meteo(pourcent) {
  return METEO.find((m) => pourcent < m.jusqua) ?? METEO[METEO.length - 1];
}

function barre(pourcent) {
  const pleines = Math.max(0, Math.min(CASES, Math.round((pourcent / 100) * CASES)));
  return "█".repeat(pleines) + "░".repeat(CASES - pleines);
}

function cout() {
  return typeof lecture.usd === "number" ? ` · ${lecture.usd.toFixed(2).replace(".", ",")} $` : "";
}

function texteBarre() {
  const m = meteo(lecture.pourcent);
  return `${m.icone} ${barre(lecture.pourcent)} ${lecture.pourcent} % · ${court(lecture.tokens)} / ${court(lecture.fenetre)}${cout()}`;
}

function ligne(Text, colonnes) {
  const m = meteo(lecture.pourcent);
  const elements = [
    Text({ color: m.couleur, bold: true, children: `${m.icone} ` }),
    Text({ color: m.couleur, children: barre(lecture.pourcent) }),
    Text({ bold: true, children: ` ${lecture.pourcent} %` }),
    Text({ dimColor: true, children: ` · ${court(lecture.tokens)} / ${court(lecture.fenetre)}${cout()}` }),
  ];
  if (colonnes >= 70) {
    elements.push(Text({ dimColor: true, children: ` · ${m.mot}` }));
  }
  return elements;
}

function court(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n % 1_000_000 === 0 ? 0 : 1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n % 1_000 === 0 ? 0 : 1)}k`;
  return String(n);
}

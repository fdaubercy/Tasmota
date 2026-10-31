// Panneau « Suivi du plan » (app de bureau, et tout client qui place un Pane) : arbre d'elements
// construit a partir de analyse() (./parseur-plan.mjs).
// Fonctions PURES : h et la table d'elements ({ Box, Text }) sont passes par l'appelant, d'ou un banc
// sous node sans moteur (tests/test_panneau.mjs).
// Pendant de outils_docs/vscode/suivi-plan/rendu.js (vue VS Code) : memes blocs, dans le meme ordre.

// Entier borne 0..100 (un pourcentage ne vient jamais du texte brut)
export function borne(p) {
  const n = Math.round(Number(p));
  return Number.isFinite(n) ? Math.max(0, Math.min(100, n)) : 0;
}

const entier = (n) => {
  const v = Math.trunc(Number(n));
  return Number.isFinite(v) && v > 0 ? v : 0;
};

// Enfants sans les trous (false, null, undefined) des branches conditionnelles
const enfants = (...xs) => xs.flat().filter(Boolean);

function barre(h, { Box }, p) {
  const v = borne(p);
  return h(Box, { width: "100%", height: 1, backgroundColor: "inactive" },
    h(Box, { width: `${v}%`, height: 1, backgroundColor: v === 100 ? "success" : "suggestion" }));
}

function etape(h, { Box, Text }, e, i) {
  // 2 espaces (ou une tabulation) par niveau, 4 niveaux au plus, comme la vue VS Code
  const retrait = Math.min(4, Math.floor(entier(e.niveau) / 2)) * 2;
  return h(Box, { key: `e${i}`, flexDirection: "column", paddingLeft: retrait }, ...enfants(
    h(Text, e.fait ? { dimColor: true } : {}, `${e.fait ? "☑" : "☐"} ${e.texte}`),
    e.preuve && h(Text, { dimColor: true, size: "footnote" }, `   preuve : ${e.preuve}`),
  ));
}

function action(h, el, a) {
  const { Box, Text } = el;
  const finie = a.total > 0 && a.fait === a.total;
  const etapes = a.etapes.length
    ? a.etapes.map((e, i) => etape(h, el, e, i))
    : [h(Text, { dimColor: true, italic: true }, "Aucune sous-étape.")];
  return h(Box, { key: `a-${a.id}`, flexDirection: "column", gap: "xs" },
    h(Text, finie ? { bold: true, color: "success" } : { bold: true }, `${a.id} — ${a.titre}`),
    h(Box, { flexDirection: "row", gap: 1, alignItems: "center" },
      h(Box, { flexGrow: 1 }, barre(h, el, a.pourcent)),
      h(Text, { dimColor: true, tabular: true }, `${entier(a.fait)}/${entier(a.total)} · ${borne(a.pourcent)} %`)),
    ...etapes);
}

function colonne(h, { Box, Text }, titre, liste) {
  const items = liste.length
    ? liste.map((x, i) => h(Text, x.fait ? { key: `m${i}`, dimColor: true } : { key: `m${i}` }, `${x.fait ? "☑" : "☐"} ${x.texte}`))
    : [h(Text, { dimColor: true }, "Rien.")];
  return h(Box, { key: titre, flexDirection: "column" }, h(Text, { weight: "semibold" }, titre), ...items);
}

function ameliorations(h, el, liste) {
  if (!liste.length) return null;
  const { Box, Text } = el;
  const restant = liste.filter((x) => !x.fait).length;
  return h(Box, { flexDirection: "column", gap: "xs" },
    h(Text, { bold: true }, `Améliorations restantes (${restant} sur ${liste.length})`),
    colonne(h, el, "Conversation", liste.filter((x) => x.portee === "conversation")),
    colonne(h, el, "Projet", liste.filter((x) => x.portee !== "conversation")));
}

// Arbre du panneau.
// @a       resultat de analyse(), ou null : aucun plan a montrer
// @fichier chemin relatif du plan (tasks/plans/x.md)
export function panneau(h, el, a, fichier) {
  const { Box, Text } = el;
  if (!a) {
    return h(Box, { flexDirection: "column", gap: "xs", padding: "sm" },
      h(Text, { bold: true }, "Aucun plan"),
      h(Text, { dimColor: true }, "Cette conversation ne suit aucun plan, et aucun plan n'est actif."),
      h(Text, { dimColor: true }, "Pour en suivre un : /suivi suivre <chantier> (liste : /suivi liste)."));
  }
  const m = a.meta || {};
  const infos = [m.chantier, m.statut || "?", m.maj && `maj ${m.maj}`, fichier].filter(Boolean).join(" · ");
  const global = a.global == null ? "—" : `${borne(a.global)} %`;
  return h(Box, { flexDirection: "column", gap: "md", padding: "sm" }, ...enfants(
    h(Box, { flexDirection: "column", gap: "xs" },
      h(Text, { size: "heading", bold: true }, a.titre || "Plan sans titre"),
      h(Text, { dimColor: true }, infos),
      barre(h, el, a.global ?? 0),
      h(Text, { tabular: true }, `${global} · ${entier(a.fait)}/${entier(a.total)} étapes`)),
    (a.alertes || []).length && h(Box, { flexDirection: "column" },
      ...a.alertes.map((x, i) => h(Text, { key: `al${i}`, color: "warning" }, `⚠ ${x}`))),
    ...a.actions.map((x) => action(h, el, x)),
    ameliorations(h, el, a.ameliorations || []),
  ));
}

// Banc du panneau « Suivi du plan » : node .claude/mods/suivi-plan/tests/test_panneau.mjs
// h factice : l'arbre devient { type, props, enfants } ; on y cherche textes et largeurs de barres.
import assert from "node:assert/strict";
import { analyse } from "../hooks/parseur-plan.mjs";
import { panneau, borne } from "../hooks/panneau.mjs";

const h = (type, props, ...enfants) => ({ type, props: props ?? {}, enfants });
const el = { Box: "Box", Text: "Text" };
const noeuds = (n) => (n && typeof n === "object" ? [n, ...n.enfants.flatMap(noeuds)] : []);
const textes = (arbre) => noeuds(arbre).filter((n) => n.type === "Text").map((n) => n.enfants.join(""));
// Remplissages des barres (le fond « inactive » fait toujours 100 %)
const largeurs = (arbre) => noeuds(arbre).filter((n) => n.props.height === 1 && n.props.backgroundColor !== "inactive").map((n) => n.props.width);

const PLAN = [
  "---", "chantier: essai", "titre: Plan d'essai", "statut: actif", "maj: 2026-10-31", "---",
  "# Plan d'essai", "", "## A1 — Première action", "- [x] étape faite — preuve : banc vert", "- [ ] étape à faire", "",
  "## A2 — Deuxième action", "- [x] seule étape — preuve : commit abc", "",
  "## Améliorations restantes", "- [ ] [conversation] reste à voir", "- [x] [projet] déjà fait", "",
].join("\n");

let n = 0;
const cas = (nom, f) => { f(); n++; console.log(`OK     ${nom}`); };

const a = analyse(PLAN);
const arbre = panneau(h, el, a, "tasks/plans/essai.md");
const t = textes(arbre);

cas("en-tête : titre, infos, global", () => {
  assert.equal(t[0], "Plan d'essai");
  assert.equal(t[1], "essai · actif · maj 2026-10-31 · tasks/plans/essai.md");
  assert.ok(t.includes(`${borne(a.global)} % · 2/3 étapes`), t.join(" | "));
});

cas("barres : globale puis une par action, largeur = pourcentage borné", () => {
  assert.deepEqual(largeurs(arbre), [`${borne(a.global)}%`, "50%", "100%"]);
});

cas("action finie en couleur succès, l'autre non", () => {
  const titres = noeuds(arbre).filter((x) => x.type === "Text" && /^A\d — /.test(x.enfants.join("")));
  assert.deepEqual(titres.map((x) => x.props.color ?? null), [null, "success"]);
});

cas("étapes cochées/non cochées et preuve", () => {
  assert.ok(t.includes("☑ étape faite"));
  assert.ok(t.includes("☐ étape à faire"));
  assert.ok(t.includes("   preuve : banc vert"));
});

cas("améliorations : compte restant et répartition conversation / projet", () => {
  assert.ok(t.includes("Améliorations restantes (1 sur 2)"));
  const i = t.indexOf("Conversation"), j = t.indexOf("Projet");
  assert.ok(i >= 0 && j > i);
  assert.equal(t[i + 1], "☐ reste à voir");
  assert.equal(t[j + 1], "☑ déjà fait");
});

cas("aucun plan : message et commande pour en suivre un", () => {
  const vide = textes(panneau(h, el, null));
  assert.equal(vide[0], "Aucun plan");
  assert.ok(vide.some((x) => x.includes("/suivi suivre <chantier>")));
});

cas("arbre sans trous (aucun enfant false/null/undefined)", () => {
  assert.ok(noeuds(arbre).every((x) => x.enfants.every((c) => c !== false && c !== null && c !== undefined)));
});

cas("TEMOIN : une largeur faussée est détectée", () => {
  const casse = (type, props, ...e) => h(type, props?.width === "50%" ? { ...props, width: "0%" } : props, ...e);
  assert.notDeepEqual(largeurs(panneau(casse, el, a, "x")), largeurs(arbre));
});

console.log(`\nTEST_PANNEAU: OK (${n} tests)`);

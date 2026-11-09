// Mode carte de la page d'équilibrage (plan tasks/plans/equilibrage-par-la-carte.md) : ajouté par la carte des débits
// derrière equilibrage.html (equilibragePage.be::equilibragePage_envoiePage), jamais dans l'artifact. Utilise les globales
// de la page : CARTE, NOMS, ETATS, CIBLES_CALC, calcule, estime, majSchema, montre, courante, reglage, montrerRapports.
//   - lecture des 6 débits (/equilibrage?f=debits), au chargement, au bouton et en suivi direct ;
//   - schéma animé alimenté par les débits réels pendant le suivi direct, coloré selon les cibles du calculateur ;
//   - réglages de l'estimateur et puissances gardés sur la carte (/equilibrage?f=reglages, POST /equilibrage).

// ---- Lecture des débits sur la carte ----
const etatCarte = document.getElementById("carte-etat"), suivre = document.getElementById("suivre");
let minuterie = null;
let REEL = null;            // débits mesurés montrés par le schéma pendant le suivi direct
function nommeDeparts(noms) {
  NOMS = noms.map(n => String(n || ""));
  NOMS.forEach((n, k) => {
    const lm = document.querySelector(`label[for="m${k + 1}"]`), lp = document.querySelector(`label[for="p${k + 1}"]`);
    if (lm && n) lm.firstChild.textContent = `Départ ${k + 1} (${n}) : débit mesuré (L/min)`;
    if (lp && n) lp.firstChild.textContent = `Radiateur ${k + 1} (${n}) : puissance (W)`;
    const lg = document.querySelectorAll("#radiateurs legend")[k];
    if (lg && n) lg.textContent = `Radiateur ${k + 1} — ${n}`;
  });
}
let enCours = false;       // une lecture à la fois : une réponse tardive n'écrase pas une plus récente
async function lireCarte() {
  if (enCours) return;
  enCours = true;
  try {
    const r = await fetch("/equilibrage?f=debits", { cache: "no-store", signal: AbortSignal.timeout(5000) });
    if (!r.ok) throw new Error("réponse " + r.status);
    const j = await r.json();
    if (!Array.isArray(j.debits) || j.debits.length !== 6) throw new Error("mesures illisibles");
    nommeDeparts(Array.isArray(j.noms) ? j.noms : []);
    ETATS = j.debits.map((q, k) => j.muets && j.muets[k] ? "muet ?" : j.imprecis && j.imprecis[k] ? "imprécis" : "");
    j.debits.forEach((q, k) => { document.getElementById("m" + (k + 1)).value = typeof q === "number" ? q.toFixed(2).replace(".", ",") : ""; });
    calcule();
    REEL = suivre.checked ? j.debits.map(q => typeof q === "number" ? q : 0) : null;
    montreReel();
    const age = typeof j.age_s === "number" ? `mesure d'il y a ${Math.round(j.age_s)} s` : "aucune mesure encore";
    const alertes = ETATS.map((e, k) => e ? `départ ${k + 1} ${e}` : "").filter(Boolean).join(", ");
    etatCarte.textContent = `Lu à ${new Date().toLocaleTimeString("fr-FR")}, ${age}` + (alertes ? ` ; ${alertes}` : "") + ".";
  } catch (e) {
    const cause = e.name === "TimeoutError" ? "pas de réponse en 5 s" : e.message;
    etatCarte.textContent = "Lecture impossible : " + cause + ". Les valeurs affichées sont les dernières lues.";
  } finally {
    enCours = false;
  }
}
function planifie() {
  clearInterval(minuterie); minuterie = null;
  if (suivre.checked && !document.hidden) {
    minuterie = setInterval(lireCarte, Math.max(2, Number(CARTE.fenetre) || 10) * 1000);
  }
}

// ---- Schéma sur les débits réels (suivi direct) : remplace l'illustration de l'étape affichée ----
function montreReel() {
  if (!REEL) return;
  reglage = null;                       // pas d'animation de l'étape C : le schéma montre la nourrice telle qu'elle est
  montrerRapports = true;
  const cibles = CIBLES_CALC.length === 6 ? CIBLES_CALC : REEL.map(() => 0);
  majSchema(REEL.slice(), null, cibles);
  document.getElementById("schema-texte").textContent = "Débits réels de la carte (suivi en direct) : couleur et rapport selon la cible du calculateur.";
}
const montreEtape = montre;
montre = function (i) { montreEtape(i); montreReel(); };   // changer d'étape garde les débits réels

// ---- Réglages de l'estimateur gardés sur la carte ----
const CHAMPS = ["t-aller", "t-retour", "t-piece", "pac"];
for (let n = 1; n <= 6; n++) for (const s of ["-type", "-h", "-l", "-e", "-p", "-dt", ""]) CHAMPS.push(s ? "r" + n + s : "p" + n);
const boutonGarder = document.createElement("button");
boutonGarder.type = "button"; boutonGarder.className = "lire"; boutonGarder.textContent = "Garder les puissances sur la carte";
document.getElementById("carte-zone").insertBefore(boutonGarder, etatCarte);
async function lisReglages() {
  try {
    const r = await fetch("/equilibrage?f=reglages", { cache: "no-store", signal: AbortSignal.timeout(5000) });
    if (!r.ok) throw new Error("réponse " + r.status);
    const j = await r.json();
    let n = 0;
    for (const id of CHAMPS) {
      const el = document.getElementById(id);
      if (el && typeof j[id] === "string") { el.value = j[id]; ecrit(id, j[id]); n++; }
    }
    if (n) { estime(); calcule(); }
    return n;
  } catch (e) {
    etatCarte.textContent = "Réglages de la carte illisibles : " + e.message + ". Ceux du navigateur sont gardés.";
    return 0;
  }
}
boutonGarder.addEventListener("click", async () => {
  const reglages = {};
  for (const id of CHAMPS) { const el = document.getElementById(id); if (el) reglages[id] = String(el.value).trim().slice(0, 12); }
  try {
    const r = await fetch("/equilibrage", { method: "POST", body: new URLSearchParams({ reglages: JSON.stringify(reglages) }),
                                            signal: AbortSignal.timeout(5000) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.erreur || "réponse " + r.status);
    etatCarte.textContent = `Puissances et réglages gardés sur la carte à ${new Date().toLocaleTimeString("fr-FR")}.`;
  } catch (e) {
    etatCarte.textContent = "Enregistrement impossible : " + (e.name === "TimeoutError" ? "pas de réponse en 5 s" : e.message) + ".";
  }
});

// ---- Mise en route ----
if (CARTE) {
  document.getElementById("carte-zone").hidden = false;
  document.getElementById("calc-note").textContent = "Débits lus sur la carte ; puissances à saisir, ou reportées de l'estimateur, puis gardées sur la carte par le bouton.";
  document.getElementById("lire").addEventListener("click", lireCarte);
  suivre.addEventListener("change", () => {
    planifie();
    if (suivre.checked) lireCarte(); else { REEL = null; montreEtape(courante); }   // retour à l'illustration de l'étape
  });
  document.addEventListener("visibilitychange", () => { planifie(); if (suivre.checked && !document.hidden) lireCarte(); });
  nommeDeparts(CARTE.noms);
  // réglages de la carte d'abord (les cibles du calculateur en dépendent) ; planifie : case « Suivre » restaurée par le navigateur
  lisReglages().then(lireCarte).then(planifie);
}

"""Arrivee sur la page Build par le bouton « Televerser » de l'Atelier des graphiques (A7, plan atelier-destinations,
spec 2026-11-04-atelier-destinations-televersement-design.md §5 et §7.1, §7.7, §7.8).

Lien : `/?env=<env>&depuis=atelier&fichiers=<chemins de l'image, separes par des virgules>&redemarrer=<0|1>`. Les
parametres ne font que preremplir : la page choisit la carte dans l'onglet « Fichiers », affiche le bandeau, lance
le buildfs de l'env par le meme chemin que « Preparer la liste » (POST /lancer, X-Build), puis, a la fin REUSSIE de
cette image, coche exactement les fichiers de la liste presents dans l'image et « Redemarrer » selon le parametre.
Rien n'est envoye : l'utilisateur clique « Envoyer ». Env qui n'est pas une carte OTA, chemin hostile (`..`, absolu,
`\\`, lecteur), liste vide : ignores avec un message ; aucun buildfs sans fichier valide.
Lancement de la page en cours : le buildfs part a son `fin` (flux /flux). Build lance ailleurs (refus 409 sans
lancement de la page) : nouvel essai toutes les 5 s, 1 h au plus. Rechargement : `depuis`, `fichiers` et
`redemarrer` sont retires de l'URL des que le buildfs est ACCEPTE (pas avant : un rechargement pendant l'attente
d'un autre build reprend l'attente ; pas apres : un rechargement ne relance jamais le buildfs). Limite : un
rechargement pendant le buildfs perd la selection automatique (cocher a la main, ou rouvrir le lien de l'atelier).
Insere a la fin du JS de build_page_fichiers.py ; arriveeAtelier est appelee par demarre() de build_page.
"""

JS = r"""
// ---------- arrivee depuis l'Atelier des graphiques (A7, build_page_atelier.py) ----------
var AT = null;          // {env, liste, redemarrer, etat: attend | prepa | cocher, essais, minuterie}
var AT_BANDEAU = "Fichiers sélectionnés automatiquement par l'Atelier des graphiques, pour téléverser un graphique nouveau ou modifié. Vérifiez puis cliquez sur « Envoyer ».";

function atNote(t) { $("f-atelier").hidden = false; $("f-atelier-notes").appendChild(h("li", {texte: t})); }
function atAbandon(t) { atNote(t); AT = null; }
// Chemin de l'image (build_fichiers.liste) : relatif, segments non vides, ni . ni .., ni \ ni lecteur ni controle
function atCheminSur(c) {
  return c.length <= 200 && !/[\\:\x00-\x1f]/.test(c) && c.split("/").every(function (p) { return p && p !== "." && p !== ".."; });
}

// Appelee par demarre() une fois /envs et /execution lus : le debut du buildfs n'est donc pas pris pour un rejeu.
function arriveeAtelier() {
  var p = new URLSearchParams(location.search);
  if (p.get("depuis") !== "atelier") return;
  var env = p.get("env") || "", e = parNom[env];
  montreOnglet("fichiers");
  if (!e || e.famille !== "cartes" || !e.ota_possible)
    return atNote("Lien de l'Atelier des graphiques ignoré : « " + env + " » n'est pas une carte envoyable par le réseau. Rien n'est lancé.");
  var brut = p.get("fichiers") || "", liste = [], refus = [];
  if (brut.length > 1024) { atNote("Liste de fichiers trop longue (plus de 1 Ko) : ignorée."); brut = ""; }
  brut.split(",").forEach(function (c) {
    if (!c) return;
    if (!atCheminSur(c)) refus.push(c); else if (liste.indexOf(c) < 0) liste.push(c);
  });
  if (refus.length) atNote("Chemin refusé (hors du FS de la carte), non coché : " + refus.join(", "));
  var r = p.get("redemarrer");
  if (r !== "0" && r !== "1")
    atNote("Paramètre redemarrer ignoré (" + (r === null ? "absent" : "« " + r + " »") + ", attendu 0 ou 1) : « Redémarrer » non coché.");
  choisitCarte(env);
  if (!liste.length) return atNote("Lien de l'Atelier des graphiques : aucun fichier valide à sélectionner, rien n'est lancé.");
  AT = {env: env, liste: liste, redemarrer: r === "1", etat: "attend", essais: 0, minuterie: null};
  $("f-atelier-texte").textContent = AT_BANDEAU;
  $("f-atelier").hidden = false;
  if (enCours) atNote("Un lancement est en cours : la construction du FS de " + env + " partira à sa fin.");
  else atLance();
}

async function atLance() {
  if (!AT) return;
  AT.minuterie = null;
  if (F.env !== AT.env) return atAbandon("Autre carte choisie : sélection automatique abandonnée.");
  AT.etat = "prepa";
  var r = await preparerListe();
  if (!AT) return;
  if (r.ok) { history.replaceState(null, "", location.pathname + "?env=" + encodeURIComponent(AT.env)); return; }
  AT.etat = "attend";
  if (!/déjà en cours|réessayer/.test(r.texte || "")) return atAbandon("Construction du FS refusée : rien ne sera coché.");
  if (enCours) return atNote("Un lancement est en cours : la construction du FS partira à sa fin.");
  if (++AT.essais > 720) return atAbandon("Build toujours en cours après 1 h : sélection automatique abandonnée.");
  if (AT.essais === 1) atNote("Construction refusée (" + r.texte + ") : nouvel essai toutes les 5 s.");
  AT.minuterie = setTimeout(atLance, 5000);
}

// Fin d'un lancement (flux, hors rejeu ; appelee par fichiersEvenement)
function atelierFin() {
  if (!AT) return;
  if (AT.etat === "attend") { if (!enCours && !AT.minuterie) atLance(); return; }
  if (AT.etat !== "prepa" || !F.suivi || F.suivi.genre !== "prepa") return;     // pas la fin de notre buildfs
  if (F.suivi.statut === "succes") AT.etat = "cocher";                          // chargeListe (relance) puis atelierListe
  else atAbandon("Construction du FS en échec ou arrêtée : rien n'est coché.");
}

// Liste relue (fin de chargeListe) : coche exactement les fichiers de la liste presents dans l'image neuve.
function atelierListe() {
  if (!AT || AT.etat !== "cocher") return;
  if (F.env !== AT.env) return atAbandon("Autre carte choisie : sélection automatique abandonnée.");
  var presents = {}, absents = [];
  F.liste.fichiers.forEach(function (f) { presents[f.chemin] = true; });
  F.coches = {}; F.dossier = null;
  AT.liste.forEach(function (c) { if (presents[c]) F.coches[c] = true; else absents.push(c); });
  if (absents.length) atNote("Absent de l'image du FS, non coché : " + absents.join(", "));
  $("f-restart").checked = AT.redemarrer;
  $("f-restart").onchange.call($("f-restart"));       // grise « Recharger Berry » comme un clic
  AT = null;
  majFichiers();
}
"""

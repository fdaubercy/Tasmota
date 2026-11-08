"""Arrivee sur la page Build par le bouton « Televerser » de l'Atelier des graphiques (A7, plan atelier-destinations,
spec 2026-11-04-atelier-destinations-televersement-design.md §5 et §7.1, §7.7, §7.8).

Lien : `/?env=<env>&depuis=atelier&fichiers=<chemins de l'image, separes par des virgules>&redemarrer=<0|1>`. Les
parametres ne font que preremplir : la page choisit la carte dans l'onglet « Fichiers », affiche le bandeau, lance
le buildfs de l'env par le meme chemin que « Preparer la liste » (POST /lancer, X-Build), puis, a la fin REUSSIE de
cette image, coche exactement les fichiers de la liste presents dans l'image et « Redemarrer » selon le parametre.
Rien n'est envoye : l'utilisateur clique « Envoyer ». Env qui n'est pas une carte OTA, chemin hostile (`..`, absolu,
`\\`, lecteur) : ignores avec un message ; des chemins donnes mais tous refuses : aucun buildfs. Liste VIDE (lien
« Envoyer par la page Build » de l'atelier, A12 du 2026-11-08) : buildfs lance, rien coche, bandeau « cochez les fichiers ».
Lancement de la page en cours : le buildfs part a son `fin` (flux /flux). Build lance ailleurs (refus 409 sans
lancement de la page) : nouvel essai toutes les 5 s, 1 h au plus. Rechargement : `depuis`, `fichiers` et
`redemarrer` sont retires de l'URL des que le buildfs est ACCEPTE (pas avant : un rechargement pendant l'attente
d'un autre build reprend l'attente ; pas apres : un rechargement ne relance jamais le buildfs). Limite : un
rechargement pendant le buildfs perd la selection automatique (cocher a la main, ou rouvrir le lien de l'atelier).
Historique rejoue par /flux?depuis=0 : `F.prepa` n'est touche qu'hors rejeu, et /execution est relu juste avant le
POST : l'historique pas encore recu passe alors en rejeu, meme si /execution a echoue au chargement. `AT.n0` n'est pose
qu'une fois cette relecture faite : un `fin` arrive avant ne peut pas etre le notre. Un `fin` hors rejeu qui n'est pas
celui de notre buildfs abandonne avec un message, jamais en silence. Outil redemarre sous la page (flux renumerote, ou
`fin` jamais recu d'apres /execution a la reconnexion) : abandon dit, voir atelierRedemarrage.
Insere a la fin du JS de build_page_fichiers.py ; arriveeAtelier est appelee par demarre() de build_page.
"""

JS = r"""
// ---------- arrivee depuis l'Atelier des graphiques (A7, build_page_atelier.py) ----------
var AT = null;          // {env, liste, redemarrer, etat: attend | prepa | cocher, essais, minuterie, n0}
var AT_BANDEAU = "Fichiers sélectionnés automatiquement par l'Atelier des graphiques, pour téléverser un graphique nouveau ou modifié. Vérifiez puis cliquez sur « Envoyer ».";
var AT_BANDEAU_SEUL = "Image du FS reconstruite à la demande de l'Atelier des graphiques : cochez les fichiers à envoyer, puis cliquez sur « Envoyer ».";

function atNote(t) { $("f-atelier").hidden = false; $("f-atelier-notes").appendChild(h("li", {texte: t})); }
function atAbandon(t) { $("f-atelier-texte").textContent = ""; atNote(t); AT = null; }   // le bandeau de selection ne vaut plus
// Outil redemarre sous la page : notre buildfs n'enverra jamais son `fin`, ni « Préparer la liste » le sien
function atelierRedemarrage() {
  F.prepa = false;
  if (AT) atAbandon("L'outil a redémarré : sélection automatique abandonnée, relancez depuis l'atelier.");
  majBoutonsFichiers();
}
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
  if (!liste.length && p.get("fichiers"))            // des chemins donnes (trop longs ou tous refuses) : rien n'est lance
    return atNote("Lien de l'Atelier des graphiques : aucun fichier valide à sélectionner, rien n'est lancé.");
  AT = {env: env, liste: liste, redemarrer: r === "1", etat: "attend", essais: 0, minuterie: null};
  $("f-atelier-texte").textContent = liste.length ? AT_BANDEAU : AT_BANDEAU_SEUL;     // liste vide : construire seulement (A12)
  $("f-atelier").hidden = false;
  if (enCours) atNote("Un lancement est en cours : la construction du FS de " + env + " partira à sa fin.");
  else atLance();
}

async function atLance() {
  if (!AT) return;
  AT.minuterie = null;
  if (F.env !== AT.env) return atAbandon("Autre carte choisie : sélection automatique abandonnée.");
  AT.etat = "prepa"; AT.n0 = undefined;
  // Numero du flux avant NOTRE buildfs : un `fin` jusque-la est d'un ancien lancement (historique rejoue, meme si
  // /execution a echoue au chargement : le reste de l'historique passe alors en rejeu).
  var x = await appel("/execution");
  if (!AT) return;
  if (F.env !== AT.env) return atAbandon("Autre carte choisie : sélection automatique abandonnée.");
  if (!x.ok || !x.donnees || typeof x.donnees.numero !== "number")
    return atAbandon("État du serveur illisible (/execution : " + (x.texte || x.statut) + ") : sélection automatique abandonnée, cliquer « Préparer la liste ».");
  if (x.donnees.numero > dernierN && x.donnees.numero > rejeuJusqua) rejeuJusqua = x.donnees.numero;
  if (x.donnees.en_cours) {
    AT.etat = "attend";
    AT.minuterie = setTimeout(atLance, 5000);          // son `fin` a pu doubler cette reponse : ne pas dependre de lui
    if (!AT.attenteDite) atNote("Un lancement est en cours : la construction du FS de " + AT.env + " partira à sa fin.");
    AT.attenteDite = true;
    return;
  }
  AT.n0 = x.donnees.numero;
  var r = await preparerListe();
  if (!AT) return;
  if (r.ok || !r.statut) history.replaceState(null, "", location.pathname + "?env=" + encodeURIComponent(AT.env));
  if (r.ok) return;
  if (!r.statut)                                       // delai depasse : le serveur a peut-etre lance
    return atAbandon("Pas de réponse du serveur à la construction du FS (" + r.texte + ") : résultat incertain, " +
                     "rien ne sera coché automatiquement ; suivre le lancement puis cocher à la main.");
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
  if (AT.n0 === undefined || AT.etat !== "prepa") return;                       // d'avant notre buildfs
  if (!F.suivi || F.suivi.genre !== "prepa")
    return atAbandon("Un autre lancement s'est terminé à la place de la construction du FS demandée : sélection " +
                     "automatique abandonnée, cliquer « Préparer la liste ».");
  if (F.suivi.statut === "succes") AT.etat = "cocher";                          // chargeListe (relance) puis atelierListe
  else atAbandon("Construction du FS en échec ou arrêtée : rien n'est coché.");
}

// Liste relue (fin de chargeListe) : coche exactement les fichiers de la liste presents dans l'image neuve.
function atelierListe() {
  if (!AT || AT.etat !== "cocher") return;
  if (F.env !== AT.env) return atAbandon("Autre carte choisie : sélection automatique abandonnée.");
  if (!F.liste.fichiers.length)                        // /fichiers en panne, image illisible : rien ne prouve une absence
    return atAbandon("Liste de l'image du FS illisible (" + (F.liste.erreur || "aucun fichier") + ") : rien n'est coché.");
  var presents = Object.create(null), absents = [];    // « constructor » n'est pas un fichier present
  F.liste.fichiers.forEach(function (f) { presents[f.chemin] = true; });
  F.coches = Object.create(null); F.dossier = null;
  AT.liste.forEach(function (c) { if (presents[c]) F.coches[c] = true; else absents.push(c); });
  if (absents.length) atNote("Absent de l'image du FS, non coché : " + absents.join(", "));
  $("f-restart").checked = AT.redemarrer;
  $("f-restart").onchange.call($("f-restart"));       // grise « Recharger Berry » comme un clic
  AT = null;
  majFichiers();
}
"""

"""Script de l'onglet « autoexec.bat » (plan autoexec-bat, A11) : commande deja presente et suppression d'une ligne.
Insere dans la meme fonction que assistant_persist_page_autoexec_js.JS (il se sert de X, $, texte, rendu, bornes...).

  - decoupe : memes regles qu'autoexec_analyse.lignes (commentaire ignore, Backlog par segments, = separe aussi) ;
  - une commande dans une Backlog n'enleve que son segment ; une Backlog videe enleve sa ligne ;
  - toute modification passe par appliqueLignes -> aChange : le panneau d'envoi se ferme (c'est le DEPOT qui part) ;
  - « Inserer quand meme » reste possible : certaines commandes se repetent (Delay, Publish...) ; le bouton de « Tes
    commandes », lui, montre d'abord le choix ;
  - shortcut : les alias (SO146 = SetOption146, Power = Power1) ne sont pas reconnus, a ajouter si un fichier en porte.
Sonde : test_assistant_persist_autoexec_chrome.py.
"""

JS = r"""
// ---- Commande deja presente, suppression d'une ligne ----
function decoupe(l) {
  var c = l.trim();
  if (!c || c.charAt(0) === ";") return null;
  var m = /^(backlog\d*)(?:\s+(.*))?$/i.exec(c);
  return {mot: m ? m[1] : "", parties: (m ? (m[2] || "").split(";") : [c]).map(function (p) { return p.trim(); }).filter(Boolean)};
}
function nomCmd(p) { var m = /^([A-Za-z]\w*)(?=$|[\s=])/.exec(p); return m ? m[1].toLowerCase() : ""; }
function nomsDe(l) { var d = decoupe(l); return d ? d.parties.map(nomCmd).filter(Boolean) : []; }
function sansCmds(l, noms) {                           // la ligne sans ces commandes ; null s'il n'en reste rien
  var d = decoupe(l);
  if (!d) return l;
  var reste = d.parties.filter(function (p) { return noms.indexOf(nomCmd(p)) < 0; });
  if (reste.length === d.parties.length) return l;
  if (!reste.length) return null;
  return d.mot + " " + reste.join("; ") + (/;\s*$/.test(l) ? ";" : "");
}
function existantes(noms) {
  var res = [];
  texte().split("\n").forEach(function (l, i) { if (nomsDe(l).some(function (n) { return noms.indexOf(n) >= 0; })) res.push(i + 1); });
  return res;
}
function appliqueLignes(l, n) {
  var ta = $("a-texte"), h = ta.scrollTop;
  ta.value = l.join("\n");
  var d = bornes(n)[0];
  ta.setSelectionRange(d, d); ta.scrollTop = h;
  aChange(); clearTimeout(X.minuteur); analyse();      // analyse tout de suite : les numeros de la liste ont bouge
}
function ligneVisee() { return X.ligneIns ? X.ligneIns - 1 : 0; }   // X.ligneIns = ligne du curseur + 1, apres un geste dans le texte
function supprimeLigne() {
  var n = ligneVisee(), l = texte().split("\n");
  if (!X.lu || n < 1 || n > lignesDe(texte()).length) return;
  l.splice(n - 1, 1); appliqueLignes(l, n);
  if (n <= lignesDe(texte()).length) vaLigne(n);       // la ligne que le prochain clic retirerait se voit
}
function enleveDeLigne(n, nom) {                       // bouton d'un avertissement ; sans effet si la ligne a bouge entre-temps
  var l = texte().split("\n"), t = l[n - 1], s = t === undefined ? t : sansCmds(t, [nom]);
  if (s === t) return;
  if (s === null) l.splice(n - 1, 1); else l[n - 1] = s;
  appliqueLignes(l, n);
}
function nouvelle() { var r = X.choisie && X.lu ? rendu(X.choisie, X.valeurs) : null; return r && r.ligne ? r.ligne : null; }
function sansExistantes(noms) {                        // {lignes, place} : place = ou mettre une ligne a la place de la 1re touchee
  var sortie = [], place = -1;
  texte().split("\n").forEach(function (t) {
    var s = sansCmds(t, noms);
    if (s !== null) sortie.push(s);
    if (s !== t && place < 0) place = sortie.length;
  });
  return {lignes: sortie, place: place};
}
function remplaceExistante() {
  var ligne = nouvelle(), r = ligne ? sansExistantes(nomsDe(ligne)) : null;
  if (!r || r.place < 0) return;
  r.lignes.splice(r.place, 0, ligne);
  appliqueLignes(r.lignes, r.place + 1); vaLigne(r.place + 1); choisit(X.choisie);
}
function enleveExistante() {
  var ligne = nouvelle(), r = ligne ? sansExistantes(nomsDe(ligne)) : null;
  if (r && r.place >= 0) appliqueLignes(r.lignes, Math.min(r.place + 1, r.lignes.length));
}
function insereOuMontre() {                            // bouton « Inserer » de « Tes commandes »
  var ligne = nouvelle();
  if (ligne && existantes(nomsDe(ligne)).length) $("a-existe").scrollIntoView({block: "center"}); else insere();
}
function majLignes() {
  var n = ligneVisee(), ok = !!X.lu && n >= 1 && n <= lignesDe(texte()).length, b = $("a-supprimer");
  b.disabled = !ok; b.textContent = ok ? "Supprimer la ligne " + n : "Supprimer la ligne";
  var ligne = nouvelle(), ou = ligne ? existantes(nomsDe(ligne)) : [];
  $("a-existe").hidden = !ou.length;
  $("a-inserer").textContent = (ou.length ? "Insérer quand même à la ligne " : "Insérer à la ligne ") + ligneIns();
  if (ou.length) $("a-existe-texte").textContent = "Déjà dans le fichier, " + (ou.length > 1 ? "lignes " + ou.join(", ") : "ligne " + ou[0]) +
    " : « " + texte().split("\n")[ou[0] - 1].trim() + " ».";
}
function boutonEnlever(a, zone) {
  var b = el("button", {"class": "btn s", type: "button", "data-enleve": a.commande, title: "Enlever " + a.commande + " de la ligne " + a.ligne}, "Enlever");
  b.onclick = function (ev) { ev.stopPropagation(); enleveDeLigne(a.ligne, nomCmd(a.commande)); };
  zone.appendChild(document.createTextNode(" ")); zone.appendChild(b);
}
$("a-supprimer").onclick = supprimeLigne;
$("a-remplacer").onclick = remplaceExistante;
$("a-enlever").onclick = enleveExistante;
"""

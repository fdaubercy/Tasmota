"""Couleurs du panneau « Sortie » de la page Build (demande du 2026-11-02) : memes couleurs que le terminal de VS Code.

Le journal garde les codes ANSI de pio (PLATFORMIO_FORCE_ANSI, build_serie.Serie._lance_pio) ; ce JS, insere dans
build_page.PAGE a la marque /*JS_COULEURS*/, les traduit en <span>, le texte passant par textContent. Palette : thème
sombre par defaut de VS Code (Dark Modern, celui de l'utilisateur : aucun reglage terminal.ansi* dans son profil), et
« gras = couleur vive » comme son reglage par defaut terminal.integrated.drawBoldTextInBrightColors.
"""

JS = r"""
var ANSI_16 = ["#000000", "#cd3131", "#0dbc79", "#e5e510", "#2472c8", "#bc3fbc", "#11a8cd", "#e5e5e5",
               "#666666", "#f14c4c", "#23d18b", "#f5f543", "#3b8eea", "#d670d6", "#29b8db", "#ffffff"];
var ANSI_CODE = /\x1b\[([0-9;]*)([@-~])|\x1b\][^\x07]*\x07/g;

function ansiRetire(t) { return t.replace(ANSI_CODE, ""); }

function ansi256(n) {
  if (n < 16) return ANSI_16[n];
  if (n >= 232) { var g = 8 + (n - 232) * 10; return "rgb(" + g + "," + g + "," + g + ")"; }
  n -= 16;
  var v = function (c) { return c ? 55 + c * 40 : 0; };
  return "rgb(" + v(Math.floor(n / 36)) + "," + v(Math.floor(n / 6) % 6) + "," + v(n % 6) + ")";
}

// Applique un code SGR (« 1;31 ») a l'etat st, qui survit d'une ligne a l'autre comme dans un terminal
function ansiSgr(texte, st) {
  var c = (texte || "0").split(";").map(Number);
  for (var i = 0; i < c.length; i++) {
    var n = c[i];
    if (n === 0) { Object.keys(st).forEach(function (k) { delete st[k]; }); }
    else if (n === 1) st.gras = true;
    else if (n === 2) st.pale = true;
    else if (n === 3) st.italique = true;
    else if (n === 4) st.souligne = true;
    else if (n === 7) st.inverse = true;
    else if (n === 22) { delete st.gras; delete st.pale; }
    else if (n === 23) delete st.italique;
    else if (n === 24) delete st.souligne;
    else if (n === 27) delete st.inverse;
    else if (n >= 30 && n <= 37) st.texte = n - 30;
    else if (n >= 90 && n <= 97) st.texte = n - 82;
    else if (n === 39) delete st.texte;
    else if (n >= 40 && n <= 47) st.fond = n - 40;
    else if (n >= 100 && n <= 107) st.fond = n - 92;
    else if (n === 49) delete st.fond;
    else if ((n === 38 || n === 48) && c[i + 1] === 5) { st[n === 38 ? "texte" : "fond"] = ansi256(c[i + 2]); i += 2; }
    else if ((n === 38 || n === 48) && c[i + 1] === 2) { st[n === 38 ? "texte" : "fond"] = "rgb(" + c.slice(i + 2, i + 5).join(",") + ")"; i += 4; }
  }
}

function ansiStyle(st) {
  var couleur = function (x) { return typeof x === "number" ? ANSI_16[x] : x; };
  var texte = st.texte, s = "";
  if (st.gras && typeof texte === "number" && texte < 8) texte += 8;
  var encre = couleur(texte), fond = couleur(st.fond);
  if (st.inverse) { var e = encre; encre = fond || "#181818"; fond = e || "#cccccc"; }
  if (encre) s += "color:" + encre + ";";
  if (fond) s += "background:" + fond + ";";
  if (st.gras) s += "font-weight:bold;";
  if (st.pale) s += "opacity:.6;";
  if (st.italique) s += "font-style:italic;";
  if (st.souligne) s += "text-decoration:underline;";
  return s;
}

// Remplit div avec la ligne, codes traduits ; st : voir ansiSgr
function ansiDans(div, ligne, st) {
  div.textContent = "";
  var pose = function (morceau) {
    if (!morceau) return;
    var style = ansiStyle(st);
    if (!style) { div.appendChild(document.createTextNode(morceau)); return; }
    var s = document.createElement("span");
    s.style.cssText = style;
    s.textContent = morceau;
    div.appendChild(s);
  };
  var debut = 0, m;
  ANSI_CODE.lastIndex = 0;
  while ((m = ANSI_CODE.exec(ligne))) {
    pose(ligne.slice(debut, m.index));
    if (m[2] === "m") ansiSgr(m[1], st);
    debut = ANSI_CODE.lastIndex;
  }
  pose(ligne.slice(debut));
}
"""

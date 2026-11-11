"""Rangee « Lieu de travail » de l'annuaire (modele J) : CSS, HTML et JS inseres dans annuaire_page.PAGE.

Le lieu choisi (code de lieux.LIEUX, memorise dans localStorage, try/catch) est ajoute en `lieu=<code>` au lien
« Ouvrir » des outils dont la fiche du registre porte `lieu` ; `Tous` = lien inchange.
Libelles et nombres (envs de cartes) viennent de registre.lieux ; texte insere par textContent seulement.
"""

CSS = r"""
  .lieux{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:0 0 10px;font-size:13px}
  .lieux .intitule{color:var(--doux);margin-right:4px}
  .lieux .puce{border:1px solid var(--btn-bord);background:var(--btn);color:var(--texte);border-radius:14px;padding:3px 11px;font:inherit;cursor:pointer}
  .lieux .puce .n{color:var(--doux);margin-left:5px;font-size:12px}
  .lieux .puce[aria-pressed="true"]{background:var(--bleu);border-color:var(--bleu);color:#fff}
  .lieux .puce[aria-pressed="true"] .n{color:#fff}
"""

HTML = '<div id="lieux" class="lieux" role="group" aria-label="Lieu de travail"></div>'

JS = r"""
var lieuChoisi = "", lieuxPrets = false;
function lieuMemorise(code) { try { localStorage.setItem("annuaire-lieu", code); } catch (e) {} }
function lieuRelu() { try { return localStorage.getItem("annuaire-lieu") || ""; } catch (e) { return ""; } }
// Adresse d'un outil : `lieu=` ajoute avec ? ou & (un lien d'autre appareil porte deja ?jeton=).
function lienLieu(o, lien) {
  if (!lien || !o.lieu || !lieuChoisi) return lien;
  return lien + (lien.indexOf("?") < 0 ? "?" : "&") + "lieu=" + encodeURIComponent(lieuChoisi);
}
function dessineLieux() {
  var conteneur = $("lieux");
  if (lieuxPrets || !registre || !registre.lieux) return;
  lieuxPrets = true;
  var codes = registre.lieux.map(function (l) { return l[0]; }), memo = lieuRelu();
  lieuChoisi = codes.indexOf(memo) >= 0 ? memo : "";
  function puce(code, libelle, nombre) {
    var b = h("button", {"class": "puce", type: "button", "data-lieu": code, "aria-pressed": "false"}, libelle,
              nombre === null ? null : h("span", {"class": "n", texte: String(nombre)}));
    b.onclick = function () {
      lieuChoisi = code; lieuMemorise(code);
      conteneur.querySelectorAll(".puce").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
      dessine();
    };
    if (code === lieuChoisi) b.setAttribute("aria-pressed", "true");
    return b;
  }
  conteneur.appendChild(h("span", {"class": "intitule", texte: "Lieu de travail"}));
  conteneur.appendChild(puce("", "Tous", null));
  registre.lieux.forEach(function (l) { conteneur.appendChild(puce(l[0], l[1], l[2])); });
}
"""

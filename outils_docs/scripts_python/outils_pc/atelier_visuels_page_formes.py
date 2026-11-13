"""Editeur de formes de l'atelier des visuels (mode dessin a plat) : CSS, HTML et JS inseres dans la page par `atelier_visuels_page.py`.

HTML_FORMES : palette d'outils et de gabarits (colonne gauche) + panneau « element selectionne » (colonne droite, `#avf-sel`).
Le canevas SVG d'edition est cree par le JS dans `#av-canevas` (conteneur a fournir par la page, sinon `<body>`).
Couleurs d'interface : variables de theme de la page (--bg, --pa, --tx, --mu, --li, --ac) avec repli ; les couleurs du dessin restent libres.
"""

from atelier_visuels_page_formes_dom_js import JS_DOM
from atelier_visuels_page_formes_js import JS_PUR

JS_FORMES = JS_PUR + JS_DOM

CSS_FORMES = """
.avf-bloc { background: var(--pa, #f6f7f9); color: var(--tx, #1f2328); border: 1px solid var(--li, #d0d7de); border-radius: 6px; padding: 8px; margin-bottom: 8px; }
.avf-bloc h3 { margin: 0 0 6px; font-size: 13px; color: var(--mu, #656d76); font-weight: 600; }
.avf-grille { display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px; }
.avf-bloc button { background: var(--bg, #ffffff); color: var(--tx, #1f2328); border: 1px solid var(--li, #d0d7de); border-radius: 4px; padding: 4px 6px; font: inherit; cursor: pointer; }
.avf-bloc button:hover { border-color: var(--ac, #0969da); }
.avf-bloc button[aria-pressed="true"] { background: var(--ac, #0969da); border-color: var(--ac, #0969da); color: var(--bg, #ffffff); }
.avf-bloc label { display: block; margin: 4px 0; color: var(--tx, #1f2328); font-size: 13px; }
.avf-bloc input, .avf-bloc select { background: var(--bg, #ffffff); color: var(--tx, #1f2328); border: 1px solid var(--li, #d0d7de); border-radius: 4px; font: inherit; }
.avf-bloc input[type=number] { width: 5em; }
.avf-bloc [hidden] { display: none; }
.avf-note { color: var(--mu, #656d76); font-size: 12px; }
.avf-canevas { display: block; width: 100%; max-width: 100%; touch-action: none; user-select: none; background: var(--pa, #f6f7f9); border: 1px solid var(--li, #d0d7de); }
.avf-poignee { cursor: pointer; }
"""

_GABARITS = [("mur", "Mur de facade"), ("toitMono", "Toit monopente"), ("toitDeux", "Toit a deux pans"), ("fenetre", "Fenetre"), ("porte", "Porte"),
             ("porteGarage", "Porte de garage"), ("voletRoulant", "Volet roulant"), ("cheminee", "Cheminee"), ("boite", "Boite aux lettres"), ("numero", "Numero")]

HTML_FORMES = (
    "<div id='avf-racine'>"
    "<section class='avf-bloc'><h3>Outils</h3><div class='avf-grille'>"
    "<button type='button' data-avf-outil='sel' aria-pressed='true'>Selection</button>"
    "<button type='button' data-avf-outil='rect' aria-pressed='false'>Rectangle</button>"
    "<button type='button' data-avf-outil='polygon' aria-pressed='false'>Polygone</button>"
    "<button type='button' data-avf-act='supprime'>Supprimer</button>"
    "<button type='button' data-avf-act='annule' title='Ctrl+Z'>Annuler</button>"
    "<button type='button' data-avf-act='retablit' title='Ctrl+Y'>Retablir</button></div>"
    "<label>Nouvelle forme : <select id='avf-zone-outil'><option value=''>dessin</option><option value='effacer'>zone a effacer</option>"
    "<option value='garder'>zone gardee en photo</option></select></label>"
    "<label>Photo en fond <input type='range' id='avf-opacite' min='0' max='1' step='0.05' value='0.4'></label>"
    "<p class='avf-note'>Polygone : un clic par sommet, double-clic pour fermer. Aimantation a 8 px. Poids du dessin : <span id='avf-poids'>0 Ko</span></p></section>"
    "<section class='avf-bloc'><h3>Gabarits</h3><div class='avf-grille'>"
    + "".join(f"<button type='button' data-avf-gab='{k}'>{t}</button>" for k, t in _GABARITS)
    + "</div></section>"
    "<section class='avf-bloc' id='avf-sel' hidden><h3 id='avf-titre-sel'>Element</h3>"
    "<label id='avf-l-fill'>Couleur <input type='color' id='avf-fill' value='#888888'> "
    "<button type='button' data-avf-act='repique'>Couleur de la photo</button></label>"
    "<label>Motif <select id='avf-motif'><option value=''>aucun (uni)</option><option value='briques'>briques</option>"
    "<option value='tuiles'>tuiles</option><option value='lames'>lames</option></select></label>"
    "<label><input type='checkbox' id='avf-trait'> Contour <input type='color' id='avf-trait-c' value='#ffffff'> "
    "<input type='number' id='avf-sw' min='0' max='20' step='0.5' value='2'></label>"
    "<label id='avf-l-pente'>Pente du toit (px) <input type='number' id='avf-pente' step='1' value='0'></label>"
    "<label id='avf-l-battants'>Battants <select id='avf-battants'><option value='1'>1</option><option value='2'>2</option></select></label>"
    "<label id='avf-l-texte'>Texte <input type='text' id='avf-texte' maxlength='8'></label>"
    "<label>Nature <select id='avf-zone'><option value=''>dessin</option><option value='effacer'>zone a effacer</option>"
    "<option value='garder'>zone gardee en photo</option></select></label>"
    "<div class='avf-grille'><button type='button' data-avf-act='avant'>Premier plan</button>"
    "<button type='button' data-avf-act='arriere'>Arriere-plan</button></div></section>"
    "</div>"
)

"""Generation d'un projet KiCad (schema + PCB) a partir d'une description Python.

Pourquoi : un schema et un PCB ecrits a la main par un agent divergent vite. Ici
UNE description (composants, broches -> nets, placement) produit les deux, et
le PCB porte les liens (`path`) vers les symboles : dans KiCad, « Mettre a jour
le PCB depuis le schema » (F8) fonctionne ensuite normalement, et l'utilisateur
peut reprendre la main dans l'interface.

Schema : chaque broche recoit un label de net a son extremite (pas de fils) ;
les broches sans net recoivent un drapeau « non connecte ». Lisible, et surtout
exact par construction. Les symboles sont copies des bibliotheques officielles
(`extends` aplatis), comme le fait KiCad a l'enregistrement.

PCB : voir kicad_carte.py, a executer avec le Python de KiCad (`C:\\Program Files\\KiCad\\10.0\\bin\\python.exe`),
qui fournit `pcbnew`. Le schema, lui, n'a besoin que de la bibliotheque standard.
"""
import copy
import math
import os
import re
import uuid
from pathlib import Path

KICAD = Path(os.environ.get("KICAD_DIR", r"C:\Program Files\KiCad\10.0"))
SYM_DIR = KICAD / "share" / "kicad" / "symbols"
FP_DIR = KICAD / "share" / "kicad" / "footprints"
# Bibliotheques livrees avec la skill (chemins relatifs au projet dans ses tables)
ASSETS = Path(__file__).resolve().parent.parent / "assets"
BIBLIOS_SKILL = {"Modules_Tasmota": ASSETS / "Modules_Tasmota.pretty",
                 "Signature_Auteur": ASSETS / "Signature_Auteur.pretty"}
MODELES_3D = ASSETS / "Modules_Tasmota.3dshapes"


def chemin_biblio(lib):
    """Dossier .pretty d'une bibliotheque : celle de la skill, sinon celle de KiCad."""
    return BIBLIOS_SKILL.get(lib, FP_DIR / f"{lib}.pretty")


def uri_projet(chemin, dossier):
    """Chemin `${KIPRJMOD}/...` relatif au projet (absolu si autre lecteur Windows)."""
    try:
        return "${KIPRJMOD}/" + os.path.relpath(chemin, dossier).replace("\\", "/")
    except ValueError:
        return Path(chemin).as_posix()


def variable_3d(dossier, projet):
    """Definit PCB_TASMOTA_3D dans le .kicad_pro (pieges 35-36) en gardant le reste :
    les empreintes Modules_Tasmota y cherchent leurs modeles STEP."""
    import json
    pro = Path(dossier) / f"{projet}.kicad_pro"
    d = (json.loads(pro.read_text(encoding="utf-8")) if pro.exists()
         else {"meta": {"filename": pro.name, "version": 3}})
    d.setdefault("text_variables", {})["PCB_TASMOTA_3D"] = uri_projet(MODELES_3D, dossier)
    pro.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def nid():
    return str(uuid.uuid4())


# ------------------------------------------------------------ S-expressions
class Q(str):
    """Chaine entre guillemets (contenu deja echappe)."""


def q(texte):
    return Q(str(texte).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n"))


_TOK = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))')


def parse(texte):
    pile, pos, fin = [[]], 0, len(texte.rstrip())
    while pos < fin:
        m = _TOK.match(texte, pos)
        if not m:
            raise ValueError(f"S-expression illisible a {pos}")
        pos = m.end()
        if m.group(1):
            pile.append([])
        elif m.group(2):
            fait = pile.pop()
            pile[-1].append(fait)
        elif m.group(3) is not None:
            pile[-1].append(Q(m.group(3)))
        else:
            pile[-1].append(m.group(4))
    return pile[0]


def dump(o, niveau=0):
    if isinstance(o, Q):
        return f'"{o}"'
    if not isinstance(o, list):
        return str(o)
    if not any(isinstance(x, list) for x in o):
        return "(" + " ".join(dump(x) for x in o) + ")"
    ind = "\t" * (niveau + 1)
    corps = []
    for x in o:
        corps.append(("\n" + ind + dump(x, niveau + 1)) if isinstance(x, list) else " " + dump(x))
    return "(" + "".join(corps).lstrip() + "\n" + "\t" * niveau + ")"


def enfants(noeud, tete):
    return [x for x in noeud if isinstance(x, list) and x and x[0] == tete]


# ------------------------------------------------------------ symboles
_LIBS = {}


def _bloc(texte, debut):
    """Texte de la S-expression qui commence a `debut` (parentheses equilibrees)."""
    prof, i, dans = 0, debut, False
    while i < len(texte):
        ch = texte[i]
        if dans:
            if ch == "\\":
                i += 1
            elif ch == '"':
                dans = False
        elif ch == '"':
            dans = True
        elif ch == "(":
            prof += 1
        elif ch == ")":
            prof -= 1
            if prof == 0:
                return texte[debut:i + 1]
        i += 1
    raise ValueError("S-expression non fermee")


def _lib(nom):
    """Bibliotheque reduite a une liste paresseuse : on n'analyse que les symboles demandes
    (Connector.kicad_sym fait 335 000 lignes : tout analyser coute ~1 min)."""
    if nom not in _LIBS:
        _LIBS[nom] = (SYM_DIR / f"{nom}.kicad_sym").read_text(encoding="utf-8")
    return _LIBS[nom]


def _cherche(lib, nom):
    texte = _lib(lib)
    m = re.search(r'\n\t\(symbol "%s"\s' % re.escape(nom), texte)
    if not m:
        raise KeyError(f"symbole {nom} absent de {lib}")
    return parse(_bloc(texte, m.start() + 2))[0]


def symbole(lib_id):
    """Symbole aplati (sans `extends`), nomme 'Lib:Nom' comme dans un schema."""
    lib, nom = lib_id.split(":")
    sym = _symbole_brut(lib, nom)
    sym = copy.deepcopy(sym)
    sym[1] = q(lib_id)
    return sym


def _symbole_brut(lib, nom):
    s = _cherche(lib, nom)
    ext = enfants(s, "extends")
    if not ext:
        return s
    parent = copy.deepcopy(_symbole_brut(lib, ext[0][1]))
    pnom = parent[1]
    props = enfants(s, "property")
    corps = [x for x in parent[2:] if not (isinstance(x, list) and x[0] == "property")]
    for x in corps:
        if isinstance(x, list) and x[0] == "symbol":
            x[1] = q(nom + x[1][len(pnom):])
    return ["symbol", q(nom)] + [x for x in corps if not (isinstance(x, list) and x[0] == "symbol")] \
        + props + [x for x in corps if isinstance(x, list) and x[0] == "symbol"]


def broches(lib_id):
    """[(unite, numero, x, y, angle, type, nom)] ; unite 0 = commune a toutes."""
    sym = symbole(lib_id)
    res = []
    for sous in enfants(sym, "symbol"):
        m = re.match(r"^(.*)_(\d+)_(\d+)$", sous[1])
        if not m or int(m.group(3)) > 1:
            continue
        for p in enfants(sous, "pin"):
            at = enfants(p, "at")[0]
            num = enfants(p, "number")[0][1]
            nom = enfants(p, "name")[0][1] if enfants(p, "name") else ""
            res.append((int(m.group(2)), str(num), float(at[1]), float(at[2]),
                        int(float(at[3])) if len(at) > 3 else 0, p[1], str(nom)))
    return res


# ------------------------------------------------------------ schema
def est_alimentation(net):
    """Nets d'alimentation : labels GLOBAUX (nom sans prefixe). Les autres sont des
    labels locaux, que KiCad nomme '/NOM' : le PCB doit porter exactement ce nom,
    sinon le DRC --schematic-parity signale un net_conflict par pastille."""
    return net.startswith("+") or net.startswith("GND") or net.startswith("VCC")


def nom_net_pcb(net):
    return net if est_alimentation(net) or net.startswith("unconnected-") else "/" + net


def net_non_connecte(ref, nom_broche, numero):
    """Nom que KiCad donne au net d'une broche marquee non connectee (sinon net_conflict)."""
    if nom_broche in ("", "~"):
        return f"unconnected-({ref}-Pad{numero})"
    return f"unconnected-({ref}-{nom_broche}-Pad{numero})"


def _eff(taille=1.27, justify=None, cache=False):
    e = ["effects", ["font", ["size", taille, taille]]]
    if justify:
        e.append(["justify"] + justify.split())
    if cache:
        e.append(["hide", "yes"])
    return e


class Schema:
    def __init__(self, projet, titre, rev, date, societe="", commentaires=(), papier="A3"):
        self.projet, self.racine = projet, nid()
        self.entete = [["paper", q(papier)],
                       ["title_block", ["title", q(titre)], ["date", q(date)], ["rev", q(rev)],
                        ["company", q(societe)]] + [["comment", i + 1, q(c)] for i, c in enumerate(commentaires)]]
        self.libs, self.items, self.composants = {}, [], {}
        self.nb_flags = 0

    def composant(self, ref, lib_id, valeur, empreinte, pos, nets, unite=1, rot=0,
                  champs=None, bom=True, carte=True):
        """nets : {numero de broche: nom de net, ou None = non connecte}."""
        self.libs.setdefault(lib_id, symbole(lib_id))
        x0, y0 = (round(round(v / 2.54) * 2.54, 2) for v in pos)     # grille de connexion
        u = nid()
        pins = [b for b in broches(lib_id) if b[0] in (0, unite)]
        props = [("Reference", ref, False), ("Value", valeur, False),
                 ("Footprint", empreinte or "", True), ("Datasheet", "~", True),
                 ("Description", "", True)] + [(k, v, True) for k, v in (champs or {}).items()]
        ys = [y0 - self._rot(b[2], b[3], rot)[1] for b in pins] or [y0]
        xs = [x0 + self._rot(b[2], b[3], rot)[0] for b in pins] or [x0]
        cx = (min(xs) + max(xs)) / 2
        node = ["symbol", ["lib_id", q(lib_id)], ["at", x0, y0, rot], ["unit", unite],
                ["exclude_from_sim", "no"], ["in_bom", "yes" if bom else "no"],
                ["on_board", "yes" if carte else "no"], ["dnp", "no"], ["uuid", q(u)]]
        for i, (k, v, cache) in enumerate(props):
            py = min(ys) - 3.81 if k == "Reference" else (max(ys) + 3.81 if k == "Value" else y0)
            node.append(["property", q(k), q(v), ["at", round(cx, 2), round(py, 2), 0], _eff(cache=cache)])
        for b in pins:
            node.append(["pin", q(b[1]), ["uuid", q(nid())]])
        node.append(["instances", ["project", q(self.projet),
                                   ["path", q("/" + self.racine), ["reference", q(ref)], ["unit", unite]]]])
        self.items.append(node)
        info = self.composants.setdefault(ref, {"lib_id": lib_id, "valeur": valeur, "empreinte": empreinte,
                                                "uuid": u, "nets": {}, "noms": {}, "carte": carte})
        for b in pins:
            dx, dy = self._rot(b[2], b[3], rot)
            px, py = round(x0 + dx, 2), round(y0 - dy, 2)
            net = nets.get(b[1], "__absent__")
            if net == "__absent__":
                if b[1] in info["nets"]:
                    continue
                raise ValueError(f"{ref} broche {b[1]} sans affectation (net ou None)")
            info["nets"][b[1]] = net
            info["noms"][b[1]] = b[6]
            if net is None:
                self.items.append(["no_connect", ["at", px, py], ["uuid", q(nid())]])
            else:
                self.label(net, (px, py), (b[4] + rot + 180) % 360)
        return u

    @staticmethod
    def _rot(x, y, rot):
        a = math.radians(rot)
        return (round(x * math.cos(a) - y * math.sin(a), 4), round(x * math.sin(a) + y * math.cos(a), 4))

    def label(self, net, pos, angle=0):
        just = "left bottom" if angle in (0, 90) else "right bottom"
        if est_alimentation(net):
            self.items.append(["global_label", q(net), ["shape", "passive"], ["at", pos[0], pos[1], angle],
                               ["fields_autoplaced", "yes"], _eff(justify=just.replace(" bottom", "")),
                               ["uuid", q(nid())],
                               ["property", q("Intersheetrefs"), q("${INTERSHEET_REFS}"),
                                ["at", pos[0], pos[1], 0], _eff(cache=True)]])
        else:
            self.items.append(["label", q(net), ["at", pos[0], pos[1], angle], ["fields_autoplaced", "yes"],
                               _eff(justify=just), ["uuid", q(nid())]])

    def drapeau(self, net, pos):
        """PWR_FLAG : declare le net alimente (ERC)."""
        self.nb_flags += 1
        self.composant(f"#FLG{self.nb_flags:02d}", "power:PWR_FLAG", "PWR_FLAG", "", pos,
                       {"1": net}, bom=False, carte=False)

    def texte(self, txt, pos, taille=1.27):
        self.items.append(["text", q(txt), ["exclude_from_sim", "no"], ["at", pos[0], pos[1], 0],
                           _eff(taille, "left top"), ["uuid", q(nid())]])

    def cadre(self, titre, x0, y0, x1, y1):
        self.items.append(["rectangle", ["start", x0, y0], ["end", x1, y1],
                           ["stroke", ["width", 0], ["type", "dash"]], ["fill", ["type", "none"]],
                           ["uuid", q(nid())]])
        self.texte(titre, (x0 + 1.27, y0 + 1.27), 2)

    def ecrit(self, chemin):
        doc = ["kicad_sch", ["version", 20231120], ["generator", q("eeschema")],
               ["generator_version", q("8.0")], ["uuid", q(self.racine)]] + self.entete
        doc.append(["lib_symbols"] + list(self.libs.values()))
        doc += self.items
        doc.append(["sheet_instances", ["path", q("/"), ["page", q("1")]]])
        Path(chemin).write_text(dump(doc) + "\n", encoding="utf-8")
        self.tables_bibliotheques(Path(chemin).parent)

    def tables_bibliotheques(self, dossier):
        """sym-lib-table et fp-lib-table PROPRES AU PROJET (seules les bibliotheques
        utilisees) : le projet s'ouvre meme sur un poste ou KiCad 10 n'a jamais ete
        configure (tables globales absentes de %APPDATA%/kicad/10.0, constate le 2026-10-12)."""
        syms = sorted({lib.split(":")[0] for lib in self.libs})
        fps = sorted({c["empreinte"].split(":")[0] for c in self.composants.values() if c["empreinte"]}
                     | {"Signature_Auteur"})                 # signature sur chaque carte
        ligne = '  (lib (name "{0}")(type "KiCad")(uri "{1}")(options "")(descr ""))'
        for fichier, tete, noms, var, ext in (("sym-lib-table", "sym_lib_table", syms, "KICAD10_SYMBOL_DIR", ".kicad_sym"),
                                               ("fp-lib-table", "fp_lib_table", fps, "KICAD10_FOOTPRINT_DIR", ".pretty")):
            corps = "\n".join(ligne.format(n, uri_projet(BIBLIOS_SKILL[n], dossier)
                                           if ext == ".pretty" and n in BIBLIOS_SKILL
                                           else f"${{{var}}}/{n}{ext}") for n in noms)
            (dossier / fichier).write_text(f"({tete}\n  (version 7)\n{corps}\n)\n", encoding="utf-8")

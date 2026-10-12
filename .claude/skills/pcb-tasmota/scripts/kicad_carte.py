"""Partie PCB de la generation (pcbnew) : empreintes, contour, textes, zones, regles,
remplissage par kicad-cli, retrait des vias isoles. Le schema est dans kicad_gen.py.

A executer avec le Python de KiCad (C:/Program Files/KiCad/10.0/bin/python.exe).
"""
from pathlib import Path

from kicad_gen import KICAD, _bloc, chemin_biblio, net_non_connecte, nom_net_pcb, variable_3d


# ------------------------------------------------------------ PCB (pcbnew)
def id_couche(nom):
    """Nom court -> constante pcbnew. PIEGE : board.GetLayerID("F.SilkS") rend UNDEFINED
    sur une carte neuve (le nom affiche est "F.Silkscreen") et le fichier devient illisible."""
    import pcbnew
    return {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu, "F.SilkS": pcbnew.F_SilkS, "B.SilkS": pcbnew.B_SilkS,
            "F.Fab": pcbnew.F_Fab, "B.Fab": pcbnew.B_Fab, "Edge.Cuts": pcbnew.Edge_Cuts,
            "Cmts.User": pcbnew.Cmts_User}[nom]


def mm(v):
    import pcbnew
    return pcbnew.FromMM(v)


def pt(x, y):
    import pcbnew
    return pcbnew.VECTOR2I(mm(x), mm(y))


class Carte:
    """Construit le .kicad_pcb a partir du Schema et d'un dict de placement."""

    def __init__(self, schema, origine=(100.0, 50.0)):
        import pcbnew
        self.pcbnew, self.schema = pcbnew, schema
        self.ox, self.oy = origine
        self.board = pcbnew.BOARD()
        self.nets = {}
        self.empreintes = {}

    def abs(self, x, y):
        return self.ox + x, self.oy + y

    def net(self, nom):
        if nom not in self.nets:
            ni = self.pcbnew.NETINFO_ITEM(self.board, nom_net_pcb(nom))
            self.board.Add(ni)
            self.nets[nom] = ni
        return self.nets[nom]

    def place(self, placement):
        """placement : {ref: (x, y, rotation)} en mm, repere de la carte."""
        pn = self.pcbnew
        for ref, info in self.schema.composants.items():
            if not info["carte"] or not info["empreinte"]:
                continue
            if ref not in placement:
                raise ValueError(f"{ref} n'a pas de placement")
            lib, nom = info["empreinte"].split(":")
            fp = pn.FootprintLoad(str(chemin_biblio(lib)), nom)
            fp.SetFPID(pn.LIB_ID(lib, nom))
            fp.SetReference(ref)
            fp.SetValue(info["valeur"])
            fp.SetPath(pn.KIID_PATH("/" + info["uuid"]))
            fp.SetSheetname("Root")
            fp.SetSheetfile(self.schema.projet + ".kicad_sch")
            x, y, r = placement[ref]
            fp.SetPosition(pt(*self.abs(x, y)))
            fp.SetOrientationDegrees(r)
            self.board.Add(fp)
            for pad in fp.Pads():
                num = pad.GetNumber()
                if num not in info["nets"]:
                    continue
                n = info["nets"][num] or net_non_connecte(ref, info["noms"].get(num, ""), num)
                pad.SetNet(self.net(n))
            self.empreintes[ref] = fp

    def contour(self, l, h, rayon=2.0):
        pn = self.pcbnew
        r = rayon
        segs = [((r, 0), (l - r, 0)), ((l, r), (l, h - r)), ((l - r, h), (r, h)), ((0, h - r), (0, r))]
        for a, b in segs:
            s = pn.PCB_SHAPE(self.board, pn.SHAPE_T_SEGMENT)
            s.SetStart(pt(*self.abs(*a))); s.SetEnd(pt(*self.abs(*b)))
            s.SetLayer(pn.Edge_Cuts); s.SetWidth(mm(0.1))
            self.board.Add(s)
        for cx, cy, dep in ((r, r, (0, r)), (l - r, r, (l - r, 0)), (l - r, h - r, (l, h - r)), (r, h - r, (r, h))):
            a = pn.PCB_SHAPE(self.board, pn.SHAPE_T_ARC)
            a.SetCenter(pt(*self.abs(cx, cy))); a.SetStart(pt(*self.abs(*dep)))
            a.SetArcAngleAndEnd(pn.EDA_ANGLE(90, pn.DEGREES_T), True)
            a.SetLayer(pn.Edge_Cuts); a.SetWidth(mm(0.1))
            self.board.Add(a)

    def texte(self, txt, x, y, taille=1.2, epaisseur=0.18, couche="F.SilkS", rot=0, gras=False):
        pn = self.pcbnew
        t = pn.PCB_TEXT(self.board)
        t.SetText(txt)
        t.SetPosition(pt(*self.abs(x, y)))
        t.SetLayer(id_couche(couche))
        t.SetTextSize(pn.VECTOR2I(mm(taille), mm(taille)))
        t.SetTextThickness(mm(epaisseur))
        t.SetTextAngleDegrees(rot)
        if couche.startswith("B."):
            t.SetMirrored(True)
        self.board.Add(t)

    def empreinte_libre(self, bibliotheque, nom, x, y, rot=0, ref="LOGO1"):
        """Empreinte hors schema (logo, signature : attribut board_only, donc ignoree par
        le controle de parite). `bibliotheque` = chemin d'un dossier .pretty."""
        pn = self.pcbnew
        fp = pn.FootprintLoad(str(bibliotheque), nom)
        if fp is None:
            raise FileNotFoundError(f"{nom} absent de {bibliotheque}")
        fp.SetFPID(pn.LIB_ID(Path(bibliotheque).stem, nom))
        fp.SetReference(ref)
        fp.SetPosition(pt(*self.abs(x, y)))
        fp.SetOrientationDegrees(rot)
        self.board.Add(fp)
        self.empreintes[ref] = fp
        return fp

    def reperes(self, masques=(), deplaces=None):
        """Repere (ref) de sergraphie : masque, ou deplace en coordonnees carte."""
        for ref in masques:
            self.empreintes[ref].Reference().SetVisible(False)
        for ref, (x, y, r) in (deplaces or {}).items():
            t = self.empreintes[ref].Reference()
            t.SetPosition(pt(*self.abs(x, y)))
            t.SetTextAngleDegrees(r)

    def cadre(self, rect, texte=None, couche="Cmts.User"):
        """Encombrement d'un module enfiche (non fabrique : couche de commentaires)."""
        pn = self.pcbnew
        s = pn.PCB_SHAPE(self.board, pn.SHAPE_T_RECT)
        s.SetStart(pt(*self.abs(rect[0], rect[1]))); s.SetEnd(pt(*self.abs(rect[2], rect[3])))
        s.SetLayer(id_couche(couche)); s.SetWidth(mm(0.15))
        self.board.Add(s)
        if texte:
            self.texte(texte, (rect[0] + rect[2]) / 2, rect[1] + 1.2, 1.0, 0.15, couche=couche)

    def zone(self, net, couche, rect, isolement=0.4, priorite=0):
        pn = self.pcbnew
        z = pn.ZONE(self.board)
        z.SetLayer(id_couche(couche))
        z.SetNet(self.net(net))
        o = z.Outline(); o.NewOutline()
        x0, y0, x1, y1 = rect
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            ax, ay = self.abs(x, y)
            o.Append(mm(ax), mm(ay))
        z.SetLocalClearance(mm(isolement))
        z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pn.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.5))
        z.SetThermalReliefSpokeWidth(mm(0.6))
        z.SetAssignedPriority(priorite)
        self.board.Add(z)
        return z

    def interdiction(self, rect, nom="antenne"):
        """Zone d'exclusion cuivre (pistes, vias, remplissages) sur les 2 couches."""
        pn = self.pcbnew
        z = pn.ZONE(self.board)
        z.SetIsRuleArea(True)
        z.SetRuleAreaName(nom) if hasattr(z, "SetRuleAreaName") else None
        z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
        ls = pn.LSET(); ls.AddLayer(pn.F_Cu); ls.AddLayer(pn.B_Cu)
        z.SetLayerSet(ls)
        o = z.Outline(); o.NewOutline()
        x0, y0, x1, y1 = rect
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            ax, ay = self.abs(x, y)
            o.Append(mm(ax), mm(ay))
        self.board.Add(z)

    def regles(self, isolement=0.2, piste_min=0.2, via_min=0.5, percage_min=0.3, bord=0.5,
               texte_min=1.0, epaisseur_texte_min=0.15, anneau_min=0.15):
        """Contraintes de la carte : valeurs JLCPCB 2 couches avec marge (voir references/)."""
        ds = self.board.GetDesignSettings()
        ds.m_MinClearance = mm(isolement)
        ds.m_TrackMinWidth = mm(piste_min)
        ds.m_ViasMinSize = mm(via_min)
        ds.m_MinThroughDrill = mm(percage_min)
        ds.m_CopperEdgeClearance = mm(bord)
        ds.m_MinSilkTextHeight = mm(texte_min)
        ds.m_MinSilkTextThickness = mm(epaisseur_texte_min)
        ds.m_ViasMinAnnularWidth = mm(anneau_min)
        ds.m_HoleToHoleMin = mm(0.5)

    def enregistre(self, chemin):
        """Enregistre, puis remplit les zones par kicad-cli.

        PIEGE (constate le 2026-10-12, KiCad 10.0.3) : `pcbnew.ZONE_FILLER(board).Fill()`
        sur une carte construite en memoire plante le processus (access violation,
        meme apres BuildConnectivity), et `pcbnew.LoadBoard()` hors de l'IHM echoue
        sur `assert "process" failed in Pgm()`. Le remplissage passe donc par
        `kicad-cli pcb drc --refill-zones --save-board`, qui fait la meme chose.
        """
        self.pcbnew.SaveBoard(str(chemin), self.board)
        variable_3d(Path(chemin).parent, Path(chemin).stem)   # modeles 3D des modules
        Path(chemin).with_suffix(".kicad_dru").write_text(REGLES_DRU, encoding="utf-8")
        remplit_zones(chemin)
        n = retire_vias_isolees(chemin)
        if n:
            print(f"{n} via(s) de couture isolee(s) retiree(s)")
            remplit_zones(chemin)


# Regles propres au projet (fichier .kicad_dru, lu par l'IHM et par kicad-cli).
REGLES_DRU = """(version 1)
# Petites pastilles de masse cernees par des pistes : un seul rayon thermique suffit
# (courant de signal). Sans cette regle, le DRC exige 2 rayons (starved_thermal).
(rule "rayon_thermique_unique"
\t(constraint min_resolved_spokes 1))
"""


def _cli(*args):
    import subprocess
    return subprocess.run([str(KICAD / "bin" / "kicad-cli.exe"), *map(str, args)],
                          check=False, capture_output=True, text=True)


def remplit_zones(chemin):
    rapport = Path(chemin).with_suffix(".remplissage.rpt")
    _cli("pcb", "drc", "--refill-zones", "--save-board", "-o", rapport, chemin)
    rapport.unlink(missing_ok=True)


def retire_vias_isolees(chemin):
    """Retire du fichier les vias que le DRC dit isoles (via_dangling) : un via de
    couture tombe parfois dans un ilot de cuivre que le remplissage supprime."""
    import json
    rapport = Path(chemin).with_suffix(".vias.json")
    _cli("pcb", "drc", "--format", "json", "-o", rapport, chemin)
    try:
        viol = json.loads(rapport.read_text(encoding="utf-8")).get("violations", [])
    finally:
        rapport.unlink(missing_ok=True)
    uuids = [it["uuid"] for v in viol if v["type"] == "via_dangling" for it in v["items"]]
    texte = Path(chemin).read_text(encoding="utf-8")
    n = 0
    for u in uuids:
        i = texte.find(u)
        debut = texte.rfind("(via", 0, i) if i >= 0 else -1
        if debut < 0:
            continue
        bloc = _bloc(texte, debut)
        texte = texte[:debut] + texte[debut + len(bloc):]
        n += 1
    Path(chemin).write_text(texte, encoding="utf-8")
    return n

"""Autorouteur a grille, 2 couches, pour cartes porteuses en traversant.

Pourquoi : KiCad n'a pas d'autorouteur integre. Pour une carte porteuse (une
quarantaine de nets, pastilles traversantes accessibles des deux faces), un A*
sur grille suffit et reste entierement local, sans Java.
Option : `moteur="freerouting"` (ou variable PCB_ROUTEUR=freerouting) delegue
route_tout a Freerouting (routeur_freerouting.py), l'API restant la meme.

Principe :
  - grille de pas 0,3175 mm (= 2,54 / 8) : les broches au pas de 0,1" tombent
    sur des noeuds ;
  - pour chaque demi-largeur de piste h, une carte numpy [couche, y, x] dit qui
    « tient » chaque noeud : 0 = libre, n = seul le net n est a moins de
    (isolement + h + marge), -1 = interdit (deux nets, bord, zone d'exclusion,
    trou non metallise). Un noeud est praticable pour le net n si 0 ou n ;
  - A* 8 directions, cout de virage et cout de via ; un net multi-broches
    croit en arbre (de l'arbre deja route vers la pastille la plus proche) ;
  - en cas d'echec : on arrache tout, on passe les nets en echec en tete,
    on recommence (10 passes au plus), on garde la meilleure passe.

Vitesse (mesuree le 2026-10-12 sur la carte cuve) : l'heuristique est une table
numpy calculee une fois par recherche, g / parents / fermes sont des tableaux
plats, la grille a un lisere infranchissable (pas de test de bornes), et a
egalite de f le noeud le plus avance sort en premier. `poids` > 1 = A* pondere
(plus rapide, chemins un peu moins courts).

La marge couvre l'ecart entre noeuds (une piste diagonale passe entre deux
noeuds controles). La verification qui fait foi reste le DRC de KiCad
(`kicad-cli pcb drc`) : ce routeur ne pretend pas la remplacer.
"""
import heapq
import math
import os

import numpy as np
import pcbnew

SQ2 = math.sqrt(2)
MOUVEMENTS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
              (1, 1, SQ2), (1, -1, SQ2), (-1, 1, SQ2), (-1, -1, SQ2)]
COUCHES = (pcbnew.F_Cu, pcbnew.B_Cu)


class Routeur:
    def __init__(self, carte, largeur, hauteur, pas=0.3175, isolement=0.25, marge=0.12,
                 bord=0.6, via=(0.8, 0.4), cout_via=14.0, cout_virage=0.4, interdits=(),
                 poids=1.0, moteur=None):
        self.c, self.board = carte, carte.board
        self.pas, self.iso, self.marge, self.bord = pas, isolement, marge, bord
        self.via_d, self.via_p = via
        self.cout_via, self.cout_virage = cout_via / pas, cout_virage
        self.poids = poids
        self.moteur = (moteur or os.environ.get("PCB_ROUTEUR") or "grille").lower()
        self.nx, self.ny = int(largeur / pas) + 1, int(hauteur / pas) + 1
        self.N = self.nx * self.ny
        self.X = np.arange(self.nx) * pas
        self.Y = np.arange(self.ny) * pas
        self.dims = (largeur, hauteur)
        # (x0, y0, x1, y1[, couches]) : ceux du generateur + les zones d'interdiction
        # de la carte et des empreintes (boite englobante, donc prudente)
        self.interdits = [tuple(z[:4]) + (tuple(z[4]) if len(z) > 4 else (0, 1),) for z in interdits]
        self.interdits += list(self._zones_interdites())
        self.items, self.cartes = [], {}
        self.deja = {}                      # nets routes par Freerouting : nom -> complet ?
        self.obst_pads = list(self._obstacles_pastilles())
        self.obst_fixes = self.obst_pads + list(self._obstacles_pistes(self.board.GetTracks()))
        self.obst = list(self.obst_fixes)

    # ---------------------------------------------------------- obstacles
    def _loc(self, v):
        return pcbnew.ToMM(v.x) - self.c.ox, pcbnew.ToMM(v.y) - self.c.oy

    def _zones_interdites(self):
        zones = list(self.board.Zones())
        for fp in self.board.GetFootprints():
            zones += list(fp.Zones())
        for z in zones:
            if not (z.GetIsRuleArea() and z.GetDoNotAllowTracks()):
                continue
            couches = tuple(i for i, l in enumerate(COUCHES) if z.IsOnLayer(l))
            if couches:
                bb = z.GetBoundingBox()
                (x0, y0), (x1, y1) = self._loc(bb.GetOrigin()), self._loc(bb.GetEnd())
                yield (x0, y0, x1, y1, couches)

    def _obstacles_pastilles(self):
        for fp in self.board.GetFootprints():
            for pad in fp.Pads():
                code = pad.GetNetCode() or -1
                cx, cy = self._loc(pad.GetPosition())
                couches = [i for i, l in enumerate(COUCHES) if pad.IsOnLayer(l)]
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    r = pcbnew.ToMM(pad.GetDrillSize().x) / 2
                    yield ((0, 1), ("circ", cx, cy, r), -1, pad)
                    continue
                if not couches:
                    continue
                try:
                    forme = pad.GetShape(pcbnew.F_Cu)
                except TypeError:
                    forme = pad.GetShape()
                if forme == pcbnew.PAD_SHAPE_CIRCLE:
                    try:
                        r = pcbnew.ToMM(pad.GetSize(pcbnew.F_Cu).x) / 2
                    except TypeError:
                        r = pcbnew.ToMM(pad.GetSize().x) / 2
                    yield (tuple(couches), ("circ", cx, cy, r), code, pad)
                else:
                    bb = pad.GetBoundingBox()
                    x0, y0 = self._loc(bb.GetOrigin())
                    x1, y1 = self._loc(bb.GetEnd())
                    yield (tuple(couches), ("rect", (x0 + x1) / 2, (y0 + y1) / 2,
                                            (x1 - x0) / 2, (y1 - y0) / 2), code, pad)

    def _obstacles_pistes(self, pistes):
        """Pistes et vias deja sur la carte (ou importes de Freerouting)."""
        for t in pistes:
            code = t.GetNetCode() or -1
            if t.GetClass() == "PCB_VIA":
                try:                               # sans couche : assert (KiCad 10)
                    d = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu))
                except TypeError:
                    d = pcbnew.ToMM(t.GetWidth())
                x, y = self._loc(t.GetPosition())
                yield ((0, 1), ("circ", x, y, d / 2), code, None)
                continue
            if t.GetLayer() not in COUCHES:
                continue
            l, h = COUCHES.index(t.GetLayer()), pcbnew.ToMM(t.GetWidth()) / 2
            pts = [t.GetStart(), t.GetMid(), t.GetEnd()] if t.GetClass() == "PCB_ARC" \
                else [t.GetStart(), t.GetEnd()]
            for a, b in zip(pts, pts[1:]):
                (x1, y1), (x2, y2) = self._loc(a), self._loc(b)
                yield ((l,), ("seg", x1, y1, x2, y2, h), code, None)

    def _distance(self, forme, xs, ys):
        X, Y = np.meshgrid(self.X[xs], self.Y[ys])
        k = forme[0]
        if k == "circ":
            return np.hypot(X - forme[1], Y - forme[2]) - forme[3]
        if k == "rect":
            dx = np.maximum(np.abs(X - forme[1]) - forme[3], 0)
            dy = np.maximum(np.abs(Y - forme[2]) - forme[4], 0)
            return np.hypot(dx, dy)
        _, x1, y1, x2, y2, r = forme
        vx, vy = x2 - x1, y2 - y1
        L2 = vx * vx + vy * vy or 1e-12
        t = np.clip(((X - x1) * vx + (Y - y1) * vy) / L2, 0, 1)
        return np.hypot(X - (x1 + t * vx), Y - (y1 + t * vy)) - r

    def _etendue(self, forme, seuil):
        k = forme[0]
        if k == "circ":
            xa, xb, ya, yb = forme[1] - forme[3], forme[1] + forme[3], forme[2] - forme[3], forme[2] + forme[3]
        elif k == "rect":
            xa, xb, ya, yb = forme[1] - forme[3], forme[1] + forme[3], forme[2] - forme[4], forme[2] + forme[4]
        else:
            xa, xb = min(forme[1], forme[3]) - forme[5], max(forme[1], forme[3]) + forme[5]
            ya, yb = min(forme[2], forme[4]) - forme[5], max(forme[2], forme[4]) + forme[5]
        i0 = max(int((xa - seuil) / self.pas) - 1, 0); i1 = min(int((xb + seuil) / self.pas) + 2, self.nx)
        j0 = max(int((ya - seuil) / self.pas) - 1, 0); j1 = min(int((yb + seuil) / self.pas) + 2, self.ny)
        return slice(i0, i1), slice(j0, j1)

    def _peint(self, carte, h, obstacle):
        couches, forme, code, _ = obstacle
        seuil = self.iso + h + self.marge
        xs, ys = self._etendue(forme, seuil)
        if xs.start >= xs.stop or ys.start >= ys.stop:
            return
        masque = self._distance(forme, xs, ys) < seuil
        for l in couches:
            sous = carte[l, ys, xs]
            if code == -1:
                sous[masque] = -1
            else:
                sous[masque & (sous == 0)] = code
                sous[masque & (sous != 0) & (sous != code)] = -1

    def carte(self, h):
        """Carte d'occupation pour une demi-largeur h (construite a la demande)."""
        h = round(h, 4)
        if h not in self.cartes:
            m = np.zeros((2, self.ny, self.nx), dtype=np.int32)
            g = self.bord + h + self.marge
            L, H = self.dims
            m[:, :, self.X < g] = -1; m[:, :, self.X > L - g] = -1
            m[:, self.Y < g, :] = -1; m[:, self.Y > H - g, :] = -1
            for x0, y0, x1, y1, couches in self.interdits:
                e = h + self.marge
                ji = np.where((self.Y > y0 - e) & (self.Y < y1 + e))[0]
                ii = np.where((self.X > x0 - e) & (self.X < x1 + e))[0]
                if len(ji) and len(ii):
                    m[list(couches), ji[0]:ji[-1] + 1, ii[0]:ii[-1] + 1] = -1
            for o in self.obst:
                self._peint(m, h, o)
            self.cartes[h] = m
        return self.cartes[h]

    def _ajoute(self, obstacle):
        self.obst.append(obstacle)
        for h, m in self.cartes.items():
            self._peint(m, h, obstacle)

    def adopte_pistes(self, pistes):
        """Prend en charge des pistes posees par un autre outil (Freerouting) :
        obstacles pour la suite (masse, coutures), arrachees par _arrache."""
        for t in pistes:
            self.items.append(t)
            for o in self._obstacles_pistes([t]):
                self._ajoute(o)

    def retire_net(self, nom):
        """Retire les pistes et vias du net `nom` posees par ce routeur (ou adoptees)."""
        code = self.c.nets[nom].GetNetCode()
        for it in [i for i in self.items if i.GetNetCode() == code]:
            self.board.Remove(it)
        self.items = [i for i in self.items if i.GetNetCode() != code]
        self.obst = self.obst_fixes + list(self._obstacles_pistes(self.items))
        self.cartes = {}

    # ---------------------------------------------------------- routage
    def _cellules_pastille(self, obstacle):
        couches, forme, _, _ = obstacle
        xs, ys = self._etendue(forme, 0)
        d = self._distance(forme, xs, ys)
        jj, ii = np.where(d <= -0.05)
        if not len(jj):                             # pastille plus petite qu'une maille
            jj, ii = np.unravel_index(np.argmin(d), d.shape)
            jj, ii = np.array([jj]), np.array([ii])
        cel = [(int(j) + ys.start) * self.nx + int(i) + xs.start for j, i in zip(jj, ii)]
        return [l * self.N + c for l in couches for c in cel]

    def route_net(self, nom, largeur):
        if nom in self.deja:                        # deja traite par Freerouting
            return self.deja[nom]
        ni = self.c.nets.get(nom)
        if ni is None:
            return True
        code = ni.GetNetCode()
        pads = [o for o in self.obst_pads if o[2] == code]
        if len(pads) < 2:
            return True
        m = self.carte(largeur / 2).reshape(2, -1)
        vm = self.carte(self.via_d / 2).reshape(2, -1)
        prat = ((m == 0) | (m == code)).astype(np.uint8).ravel()
        cellules = [self._cellules_pastille(o) for o in pads]
        for cel in cellules:
            prat[cel] = 1
        p3 = prat.reshape(2, self.ny, self.nx)      # lisere infranchissable : aucun voisin
        p3[:, [0, -1], :] = 0                       # ne sort de la grille (ni ne change
        p3[:, :, [0, -1]] = 0                       # de ligne), donc pas de test de bornes
        praticable = bytearray(prat.tobytes())
        via_ok = bytearray((((vm[0] == 0) | (vm[0] == code)) & ((vm[1] == 0) | (vm[1] == code)))
                           .astype(np.uint8).tobytes())
        arbre = set(cellules[0])
        reste = list(range(1, len(pads)))
        while reste:
            chemin, idx = self._astar(arbre, {s: k for k in reste for s in cellules[k]},
                                      [self._centre(pads[k]) for k in reste], praticable, via_ok)
            if chemin is None:
                return False
            self._materialise(chemin, largeur, ni, code)
            arbre.update(chemin)
            arbre.update(cellules[idx])
            reste.remove(idx)
        return True

    def _centre(self, o):
        f = o[1]
        return f[1] / self.pas, f[2] / self.pas

    def _heuristique(self, centres):
        """Distance octile au centre le plus proche, pour tous les noeuds (2 couches)."""
        xs = np.arange(self.nx, dtype=np.float64)[None, :]
        ys = np.arange(self.ny, dtype=np.float64)[:, None]
        best = None
        for cx, cy in set(centres):
            dx, dy = np.abs(xs - cx), np.abs(ys - cy)
            h = np.maximum(dx, dy) + (SQ2 - 1) * np.minimum(dx, dy)
            best = h if best is None else np.minimum(best, h)
        lst = (best * self.poids).ravel().tolist()
        return lst + lst

    def _astar(self, sources, cibles, centres, praticable, via_ok):
        N = self.N
        H = self._heuristique(centres)
        inf = float("inf")
        g = [inf] * (2 * N)
        parent = {}
        direc = bytearray(2 * N)                    # 0 = depart ou via, k + 1 = mouvement k
        ferme = bytearray(2 * N)
        cv, cvia = self.cout_virage, self.cout_via
        # (decalage, cout, code, voisins orthogonaux a verifier pour une diagonale)
        mv = [(dy * self.nx + dx, c, k + 1, dx if dx and dy else 0, dy * self.nx if dx and dy else 0)
              for k, (dx, dy, c) in enumerate(MOUVEMENTS)]
        tas = []
        for s in sources:
            g[s] = 0.0
            tas.append((H[s], s))
        heapq.heapify(tas)
        pop, push = heapq.heappop, heapq.heappush
        departage = 1 - 1e-6                        # a f egal, le noeud le plus avance d'abord
        limite = 12 * N
        while tas and limite:
            limite -= 1
            s = pop(tas)[1]
            if ferme[s]:
                continue
            ferme[s] = 1
            if s in cibles:
                chemin = [s]
                while chemin[-1] in parent:
                    chemin.append(parent[chemin[-1]])
                return chemin[::-1], cibles[s]
            gc, d0 = g[s], direc[s]
            for off, c, k, oa, ob in mv:
                t = s + off
                if ferme[t] or not praticable[t]:
                    continue
                # diagonale : les DEUX voisins orthogonaux doivent etre libres, sinon la
                # piste frole l'obstacle entre deux noeuds (violation 0,15 mm constatee)
                if oa and not (praticable[s + oa] and praticable[s + ob]):
                    continue
                ng = gc + c + (cv if d0 and d0 != k else 0.0)
                if ng < g[t]:
                    g[t], parent[t], direc[t] = ng, s, k
                    push(tas, (ng * departage + H[t], t))
            if s < N:
                r, t = s, s + N
            else:
                r, t = s - N, s - N
            if via_ok[r] and praticable[t] and not ferme[t]:
                ng = gc + cvia
                if ng < g[t]:
                    g[t], parent[t], direc[t] = ng, s, 0
                    push(tas, (ng * departage + H[t], t))
        return None, None

    def _xy(self, s):
        l, r = divmod(s, self.N)
        y, x = divmod(r, self.nx)
        return l, x * self.pas, y * self.pas

    def _materialise(self, chemin, largeur, ni, code):
        pts = [self._xy(s) for s in chemin]
        troncon = [pts[0]]
        for p in pts[1:]:
            if p[0] != troncon[-1][0]:                       # changement de couche
                self._pistes(troncon, largeur, ni, code)
                self._via(p[1], p[2], ni, code)
                troncon = [p]
            else:
                troncon.append(p)
        self._pistes(troncon, largeur, ni, code)

    def _pistes(self, pts, largeur, ni, code):
        if len(pts) < 2:
            return
        sommets = [pts[0]]
        for a, b, c in zip(pts, pts[1:], pts[2:]):
            if (round(b[1] - a[1], 6), round(b[2] - a[2], 6)) != (round(c[1] - b[1], 6), round(c[2] - b[2], 6)):
                sommets.append(b)
        sommets.append(pts[-1])
        l = sommets[0][0]
        for a, b in zip(sommets, sommets[1:]):
            t = pcbnew.PCB_TRACK(self.board)
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[1] + self.c.ox), pcbnew.FromMM(a[2] + self.c.oy)))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(b[1] + self.c.ox), pcbnew.FromMM(b[2] + self.c.oy)))
            t.SetWidth(pcbnew.FromMM(largeur))
            t.SetLayer(COUCHES[l])
            t.SetNet(ni)
            self.board.Add(t)
            self.items.append(t)
            self._ajoute(((l,), ("seg", a[1], a[2], b[1], b[2], largeur / 2), code, None))

    def _via(self, x, y, ni, code):
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x + self.c.ox), pcbnew.FromMM(y + self.c.oy)))
        v.SetDrill(pcbnew.FromMM(self.via_p))
        try:
            v.SetWidth(pcbnew.FromMM(self.via_d))
        except TypeError:
            v.SetWidth(pcbnew.F_Cu, pcbnew.FromMM(self.via_d))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(ni)
        self.board.Add(v)
        self.items.append(v)
        self._ajoute(((0, 1), ("circ", x, y, self.via_d / 2), code, None))

    def coutures(self, nom, pas=5.08, exclus=(), journal=print):
        """Vias de couture du net `nom` (la masse) sur une grille reguliere, la ou
        rien d'autre n'est a portee : ils relient les plans des deux faces et evitent
        les ilots de cuivre isoles (DRC starved_thermal). A appeler APRES le routage."""
        ni = self.c.nets[nom]
        code = ni.GetNetCode()
        vm = self.carte(self.via_d / 2 + 0.3)            # 0,3 mm de plus : vias bien degages
        n, k = 0, max(int(pas / self.pas), 1)
        for j in range(k // 2, self.ny, k):
            for i in range(k // 2, self.nx, k):
                x, y = i * self.pas, j * self.pas
                if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in exclus):
                    continue                              # ex. sous la signature
                if vm[0, j, i] == 0 and vm[1, j, i] == 0:
                    self._via(x, y, ni, code)
                    n += 1
        journal(f"{n} vias de couture {nom}")
        return n

    def _arrache(self):
        for it in self.items:
            self.board.Remove(it)
        self.items, self.cartes, self.deja = [], {}, {}
        self.obst = list(self.obst_fixes)

    def route_tout(self, nets, passes=10, journal=print):
        """nets : [(nom, largeur_mm)] dans l'ordre de priorite. Rend la liste des echecs."""
        if self.moteur == "freerouting":
            from routeur_freerouting import route_freerouting
            return route_freerouting(self, nets, journal=journal)
        ordre, meilleur = list(nets), None
        for p in range(passes):
            echecs = [n for n, w in ordre if not self.route_net(n, w)]
            journal(f"passe {p + 1} : {len(ordre) - len(echecs)}/{len(ordre)} nets routes"
                    + (f", echecs : {', '.join(echecs)}" if echecs else ""))
            if meilleur is None or len(echecs) < len(meilleur[1]):
                meilleur = (list(ordre), echecs)
            if not echecs:
                return []
            self._arrache()
            ordre = [x for x in ordre if x[0] in echecs] + [x for x in ordre if x[0] not in echecs]
        self._arrache()
        echecs = [n for n, w in meilleur[0] if not self.route_net(n, w)]
        journal(f"retenu : {len(meilleur[0]) - len(echecs)}/{len(meilleur[0])} nets routes")
        return echecs

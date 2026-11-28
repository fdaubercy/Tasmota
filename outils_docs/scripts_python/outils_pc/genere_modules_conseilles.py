"""Classeur des modules du commerce conseillés pour chaque env personnalisé (ESP32-S3 + périphériques).

Lit les données de outils_docs/materiel/modules_conseilles/ :
  recommandations.json  choix par env (voie A : carte industrielle rail DIN ; voie B : dev-kit + cartes filles)
  cartes_s3.json        catalogue des cartes ESP32-S3 (relevé web du 2026-11-26)
  peripheriques.json    dev-kit, platine 16 relais, ADS1115, 4-20 mA, interfaces, alimentations
Écrit un .xlsx par Excel (COM, pywin32) : Python système, pas celui de PlatformIO.

Usage : C:\\Python312\\python genere_modules_conseilles.py <sortie.xlsx> [--photos <dossier>] [--telecharge-photos] [--ecrase]
  --photos : dossier des miniatures PNG + photos.json (nom du produit -> fichier) ; sans lui, colonne « Photo » en liens seuls.
  --telecharge-photos : (re)télécharge d'abord les photos dans ce dossier (photo du fabricant, sinon image de l'annonce
    AliExpress relevée dans photos_aliexpress.tsv), miniatures PNG par Pillow. Mettre ce dossier HORS du dépôt.
Ne réécrit jamais un classeur existant sans --ecrase. Instance Excel PRIVÉE (DispatchEx) : l'Excel ouvert de l'utilisateur
n'est pas touché.
"""
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
DONNEES = os.path.normpath(os.path.join(ICI, "..", "..", "materiel", "modules_conseilles"))
ENTETES = ["Voie", "Rôle dans le module", "Produit", "Caractéristiques", "Tasmota", "Réserves",
           "Prix AliExpress", "AliExpress", "Prix Amazon.fr", "Amazon.fr", "Fabricant", "Photo"]
LARGEURS = [7, 34, 30, 48, 40, 40, 22, 11, 20, 11, 11, 20]
HAUTEUR_PHOTO = 80


def charge(nom):
    with open(os.path.join(DONNEES, nom), encoding="utf-8") as f:
        return json.load(f)


def texte(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return " ; ".join(texte(x) for x in v)
    if isinstance(v, dict):
        return " ; ".join(f"{k} : {texte(x)}" for k, x in v.items())
    return str(v)


def catalogue():
    """Dictionnaire nom -> fiche, cartes (C:) et périphériques (P:)."""
    cat = {}
    for c in charge("cartes_s3.json"):
        carac = " ; ".join(f"{k} : {texte(c.get(k))}" for k in
                           ("flash_psram", "relais", "entrees_num", "entrees_ana", "rs485", "ethernet", "alim", "boitier")
                           if c.get(k))
        cat["C:" + c["nom"]] = dict(c, caracteristiques=carac)
    for cle, liste in charge("peripheriques.json")["categories"].items():
        for p in liste:
            cat["P:" + p["nom"]] = dict(p, categorie=cle)
    return cat


def trouve(cat, ref):
    noms = [n for n in cat if n.startswith(ref)]
    if len(noms) != 1:
        raise SystemExit(f"Référence {ref!r} : {len(noms)} produit(s) trouvé(s) au lieu d'un")
    return cat[noms[0]]


def telecharge_photos(cat, dossier):
    """Miniatures PNG des produits dans dossier, index photos.json. Le brut téléchargé reste dans dossier/brut."""
    import hashlib
    import urllib.request
    from PIL import Image
    with open(os.path.join(DONNEES, "photos_aliexpress.tsv"), encoding="utf-8") as f:
        og = dict(l.rstrip("\r\n").split("\t") for l in f if "\t" in l)
    os.makedirs(os.path.join(dossier, "brut"), exist_ok=True)
    res = {}
    for fiche in cat.values():
        L = fiche.get("liens", {})
        url = L.get("photo") or og.get(L.get("aliexpress") or "")
        if not url:
            continue
        h = hashlib.sha1(fiche["nom"].encode()).hexdigest()[:10]
        brut, png = os.path.join(dossier, "brut", h), os.path.join(dossier, h + ".png")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r, open(brut, "wb") as f:
                f.write(r.read())
            with Image.open(brut) as im:
                im.thumbnail((360, 360))
                im.convert("RGB").save(png)
            res[fiche["nom"]] = {"fichier": png, "url": url}
        except Exception as e:  # photo absente = lien seul dans le classeur, pas un échec
            print(f"photo non téléchargée : {fiche['nom'][:50]} ({e})")
    with open(os.path.join(dossier, "photos.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"{len(res)} photos téléchargées dans {dossier}")


def lien_valide(url, morts):
    return bool(url) and not any(m in url for m in morts)


class Classeur:
    def __init__(self, photos):
        import win32com.client
        self.xl = win32com.client.DispatchEx("Excel.Application")
        self.xl.Visible = False
        self.xl.DisplayAlerts = False
        self.wb = self.xl.Workbooks.Add()
        self.vierge = self.wb.Worksheets(1)
        self.photos = photos
        self.nb_photos = 0

    def feuille(self, nom):
        ws = self.wb.Worksheets.Add(None, self.wb.Worksheets(self.wb.Worksheets.Count))  # positionnel : After= nommé est ignoré par COM
        ws.Name = nom[:31]
        ws.Cells.Font.Name = "Arial"
        ws.Cells.Font.Size = 10
        return ws

    def ligne(self, ws, r, valeurs, gras=False, fond=None):
        rg = ws.Range(ws.Cells(r, 1), ws.Cells(r, len(valeurs)))
        rg.Value = tuple(valeurs)
        rg.WrapText = True
        rg.VerticalAlignment = -4160  # haut
        if gras:
            rg.Font.Bold = True
        if fond is not None:
            rg.Interior.Color = fond
        return rg

    def lien(self, ws, r, c, url, texte_lien):
        if url:
            ws.Hyperlinks.Add(ws.Cells(r, c), url, "", url, texte_lien)  # positionnel : les noms sont ignorés par COM
        else:
            ws.Cells(r, c).Value = "non trouvé"

    def photo(self, ws, r, c, nom, url):
        info = self.photos.get(nom) if self.photos else None
        if info and os.path.exists(info["fichier"]):
            cell = ws.Cells(r, c)
            pic = ws.Shapes.AddPicture(os.path.normpath(info["fichier"]), 0, -1, cell.Left + 2, cell.Top + 2, -1, -1)
            pic.LockAspectRatio = True
            pic.Height = HAUTEUR_PHOTO
            if pic.Width > cell.Width - 4:
                pic.Width = cell.Width - 4
            ws.Rows(r).RowHeight = max(ws.Rows(r).RowHeight, HAUTEUR_PHOTO + 6)
            self.nb_photos += 1
        elif url:
            self.lien(ws, r, c, url, "voir la photo")

    def produit(self, ws, r, voie, role, fiche, remarque, morts, douteux):
        L = fiche.get("liens", {})
        reserves = texte(fiche.get("incertitudes"))
        if remarque:
            reserves = remarque + (" | " + reserves if reserves else "")
        prix_ali = texte(L.get("aliexpress_prix"))
        if any(fiche["nom"].startswith(d) for d in douteux):
            prix_ali = "DOUTEUX : " + prix_ali
        self.ligne(ws, r, [voie, role, fiche["nom"], texte(fiche.get("caracteristiques")), texte(fiche.get("tasmota")),
                           reserves, prix_ali, "", texte(L.get("amazon_prix")) if lien_valide(L.get("amazon"), morts) else "",
                           "", "", ""])
        self.lien(ws, r, 8, L.get("aliexpress"), "AliExpress")
        self.lien(ws, r, 10, L.get("amazon") if lien_valide(L.get("amazon"), morts) else None, "Amazon.fr")
        self.lien(ws, r, 11, L.get("fabricant"), "Fiche")
        self.photo(ws, r, 12, fiche["nom"], L.get("photo"))

    def entetes(self, ws, r):
        self.ligne(ws, r, ENTETES, gras=True, fond=0xE0C8A0)
        for i, w in enumerate(LARGEURS, 1):
            ws.Columns(i).ColumnWidth = w

    def enregistre(self, sortie):
        self.vierge.Delete()
        self.wb.Worksheets(1).Activate()
        self.wb.SaveAs(sortie, 51)
        self.wb.Close(False)
        self.xl.Quit()


def lisez_moi(cl, reco, feuilles):
    ws = cl.feuille("Lisez-moi")
    lignes = [
        ("Modules du commerce conseillés par env (ESP32-S3)", True),
        (f"Relevé du {reco['_date']}. Prix d'appel : variante la moins chère affichée, à vérifier au panier avant d'acheter.", False),
        ("Voie A : carte industrielle rail DIN, alimentée en 12/24 V. Voie B : dev-kit ESP32-S3-DevKitC-1 N16R8 sur carte porteuse, avec des cartes filles.", False),
        ("Support Tasmota : seule la Waveshare ESP32-S3-ETH-8DI-8RO est attestée (discussion #24205, template blakadder). "
         "Les KinCony à PCF8575 ne sont pas gérées par le driver du firmware (il faudrait du Berry).", False),
        ("Platine 16 relais : " + reco["_regle_platine"], False),
        ("Mesures analogiques : " + reco["_regle_analogique"], False),
        ("Un lien absent s'écrit « non trouvé » : aucun lien n'est deviné. Les réserves de chaque produit sont dans sa ligne.", False),
        ("Données et générateur : outils_docs/materiel/modules_conseilles/ et outils_docs/scripts_python/outils_pc/genere_modules_conseilles.py.", False),
        ("", False), ("Feuilles :", True),
    ] + [(f"  {f['id']} : {', '.join(f['envs'])}", False) for f in feuilles] + [
        ("  Cartes S3 : catalogue complet des cartes relevées", False),
        ("  Périphériques : dev-kit, platine 16 relais, analogique, 4-20 mA, interfaces, alimentations", False),
        ("  En place et commerce : écrans 7B intégrés et appareils du commerce", False)]
    ws.Columns(1).ColumnWidth = 150
    for i, (t, gras) in enumerate(lignes, 1):
        ws.Cells(i, 1).Value = t
        ws.Cells(i, 1).WrapText = True
        ws.Cells(i, 1).Font.Bold = gras
    ws.Cells(1, 1).Font.Size = 14


def synthese(cl, cat, reco):
    ws = cl.feuille("Synthèse")
    cl.ligne(ws, 1, ["Feuille", "Env(s)", "Statut et besoins", "Voie A (carte)", "Voie B (dev-kit)"], gras=True, fond=0xE0C8A0)
    for i, w in enumerate([24, 40, 80, 45, 45], 1):
        ws.Columns(i).ColumnWidth = w
    for r, f in enumerate(reco["feuilles"], 2):
        a = "\n".join(trouve(cat, x["ref"])["nom"] for x in f["voie_a"])
        b = "\n".join(trouve(cat, x["ref"])["nom"] for x in f["voie_b"])
        cl.ligne(ws, r, [f["id"], "\n".join(f["envs"]), f["statut"], a, b])


def feuille_env(cl, cat, reco, f):
    ws = cl.feuille(f["id"])
    morts, douteux = reco["liens_morts"], reco["prix_douteux"]
    ws.Cells(1, 1).Value = f["id"] + " : " + ", ".join(f["envs"])
    ws.Cells(1, 1).Font.Bold = True
    ws.Cells(1, 1).Font.Size = 13
    ws.Cells(2, 1).Value = f["statut"]
    r = 3
    refs = [x["ref"] for x in f["voie_a"] + f["voie_b"]]
    if any(x.startswith("P:eletechsup R4") for x in refs):
        ws.Cells(r, 1).Value = "Platine relais : " + reco["_regle_platine"]
        r += 1
    if any(x.startswith(("P:Adafruit ADS1115", "P:Convertisseur 4-20", "P:Waveshare Modbus RTU Analog", "C:KinCony B4")) for x in refs):
        ws.Cells(r, 1).Value = "Analogique : " + reco["_regle_analogique"]
        r += 1
    r += 1
    cl.entetes(ws, r)
    for voie, cle in (("A", "voie_a"), ("B", "voie_b")):
        for x in f[cle]:
            r += 1
            cl.produit(ws, r, voie, x["role"], trouve(cat, x["ref"]), x.get("remarque"), morts, douteux)
    ws.Range(ws.Cells(2, 1), ws.Cells(5, 1)).WrapText = False


def feuille_catalogue(cl, nom, fiches, reco):
    ws = cl.feuille(nom)
    cl.entetes(ws, 1)
    ws.Cells(1, 1).Value = "Catégorie"
    for r, (categorie, fiche) in enumerate(fiches, 2):
        cl.produit(ws, r, categorie, "", fiche, None, reco["liens_morts"], reco["prix_douteux"])


def feuille_commerce(cl, reco):
    ws = cl.feuille("En place et commerce")
    cl.ligne(ws, 1, ["Env", "Matériel", "Nature"], gras=True, fond=0xE0C8A0)
    for i, w in enumerate([42, 110, 26], 1):
        ws.Columns(i).ColumnWidth = w
    r = 1
    for nature, cle in (("Carte intégrée, déjà en place", "deja_en_place"), ("Appareil du commerce, pas de remplacement", "commerce")):
        for x in reco[cle]:
            r += 1
            cl.ligne(ws, r, [x["env"], x["materiel"], nature])


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        raise SystemExit(__doc__)
    sortie = os.path.abspath(args[0])
    if os.path.exists(sortie) and "--ecrase" not in args:
        raise SystemExit(f"{sortie} existe déjà : rien écrit (--ecrase pour le remplacer)")
    reco = charge("recommandations.json")
    cat = catalogue()
    photos = {}
    if "--photos" in args:
        dossier = os.path.abspath(args[args.index("--photos") + 1])
        if "--telecharge-photos" in args:
            telecharge_photos(cat, dossier)
        with open(os.path.join(dossier, "photos.json"), encoding="utf-8") as f:
            photos = json.load(f)
    for f in reco["feuilles"]:  # références vérifiées AVANT d'ouvrir Excel
        for x in f["voie_a"] + f["voie_b"]:
            trouve(cat, x["ref"])
    if os.path.exists(sortie):
        os.remove(sortie)
    cl = Classeur(photos)
    try:
        lisez_moi(cl, reco, reco["feuilles"])
        synthese(cl, cat, reco)
        for f in reco["feuilles"]:
            feuille_env(cl, cat, reco, f)
        feuille_catalogue(cl, "Cartes S3", [("carte", c) for n, c in cat.items() if n.startswith("C:")], reco)
        feuille_catalogue(cl, "Périphériques", [(c["categorie"], c) for n, c in cat.items() if n.startswith("P:")], reco)
        feuille_commerce(cl, reco)
        cl.enregistre(sortie)
    except Exception:
        cl.wb.Close(False)
        cl.xl.Quit()
        raise
    print(f"{sortie} : {len(reco['feuilles'])} feuilles d'env, {cl.nb_photos} photos insérées")


if __name__ == "__main__":
    main()

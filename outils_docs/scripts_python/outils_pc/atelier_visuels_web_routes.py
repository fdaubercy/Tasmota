"""Routes JSON de l'atelier des visuels branchees sur les modules autonomes (icones, IA, ecriture, suivi) ; le serveur
(`atelier_visuels_web.py`) garde l'acces, les en-tetes, les tailles et les codes. Rien ici ne parle HTTP au client.

    GET  /icones/recherche?q=     GET /icones/svg?jeu=&nom=     POST /icones/garde {jeu, nom, confirme_attribution}
    GET  /ia/fournisseurs         GET /ia/quota?fournisseur=
    POST /ia/demande {env, fournisseur, consigne, confirme, empreinte | photo (base64)}   POST /ia/cle {fournisseur, cle}
    POST /ecriture/prevoit {env, description, empreinte_fond?}   POST /ecriture/ecrit {... + empreinte (celle du diff)}
    GET  /suivi?env=              {carte: identique | differente | absente | inconnue}
Erreurs : ValueError (400), LookupError (404), RuntimeError (409), HorsLigne (503). La cle d'un fournisseur n'est jamais rendue.
"""
import base64
import binascii
import json
import urllib.error
import urllib.request

import atelier_visuels_ecriture as ave
import atelier_visuels_ia as ia
import atelier_visuels_ia_config as cfg
import atelier_visuels_icones_web as ico
import atelier_visuels_suivi as avs
import build_envs
import tapp_envoi

DELAI_CARTE = 3
MAX_CORPS_IA = 10 * 1024 * 1024        # corps JSON de /ia/demande, photo en base64 comprise ; 1 Mo pour les autres routes
CHEMINS_IA = {"/ia/demande"}
ROUTES_GET = {"/icones/recherche", "/icones/svg", "/ia/fournisseurs", "/ia/quota", "/suivi"}
ROUTES_POST = {"/icones/garde", "/ia/demande", "/ia/cle", "/ecriture/prevoit", "/ecriture/ecrit"}
HorsLigne = ico.HorsLigne


def lecteur_http(racine, adresse_de=None):
    """lecteur(env, chemin) pour atelier_visuels_suivi : GET http sur la carte (IP du persist ou du maitre), 3 s ; None si 404."""
    def adresse(env):
        if adresse_de:
            return adresse_de(env)
        e = next((x for x in build_envs.liste_envs(racine) if x.nom == env and x.famille == "cartes"), None)
        return e.ip if e else ""

    def lecteur(env, chemin):
        a = adresse(env)
        if not a:
            raise OSError("adresse de la carte inconnue")
        try:
            with urllib.request.urlopen(urllib.request.Request(f"http://{a}{chemin}", headers={"Referer": f"http://{a}/"}),
                                        timeout=DELAI_CARTE) as r:
                return r.read(1024 * 1024)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise OSError(f"HTTP {e.code}") from None
    return lecteur


def fabrique_routes(racine, fonds, verrou, builds_en_cours=None, ouvre=None, cache_icones=None, config_fichier=None,
                    fabrique_ia=None, lecteur=None):
    """(get, post) : get(chemin, q) et post(chemin, q, corps_octets) rendent un dict JSON."""
    cache = cache_icones if cache_icones is not None else ico.cache_defaut()
    lecteur = lecteur or lecteur_http(racine)

    def builds():
        if builds_en_cours:
            return builds_en_cours()
        import build_serie                       # meme detection que la page build
        return build_serie.builds_en_cours_defaut()

    def env_valide(env):
        if env not in tapp_envoi.cartes(racine):
            raise LookupError(f"carte inconnue : {env!r}")
        return env

    def config():
        return cfg.lit(config_fichier)

    def fournisseur_valide(c, fid):
        if fid not in (fabrique_ia or ia.fabrique_defaut)(c, str(racine)):
            raise LookupError(f"fournisseur inconnu : {fid!r}")
        return fid

    def fond_garde(empreinte):
        if empreinte is None:
            return None, None
        with verrou:
            trouve = fonds.get(empreinte)
        if trouve is None:
            raise LookupError("fond inconnu : le renvoyer par POST /fond")
        return trouve[1], trouve[0]

    def get(chemin, q):
        if chemin == "/icones/recherche":
            return {"icones": ico.recherche(q.get("q"), ouvre, cache)}
        if chemin == "/icones/svg":
            return ico.svg(q.get("jeu"), q.get("nom"), ouvre, cache)
        if chemin == "/ia/fournisseurs":
            c = config()
            return {"fournisseurs": ia.fournisseurs(c, fabrique_ia, str(racine)), "reglages": cfg.pour_page(c)}
        if chemin == "/ia/quota":
            c = config()
            return ia.quota(c, fournisseur_valide(c, q.get("fournisseur")))
        if chemin == "/suivi":
            return avs.etat(racine, env_valide(q.get("env")), lecteur)
        raise LookupError("introuvable")

    def post(chemin, q, corps):
        try:
            d = json.loads(corps or b"{}")
        except ValueError:
            raise ValueError("corps JSON illisible") from None
        if not isinstance(d, dict):
            raise ValueError("objet JSON attendu")
        if chemin == "/icones/garde":
            info = ico.svg(d.get("jeu"), d.get("nom"), ouvre, cache)        # le SVG est relu chez Iconify, jamais pris du client
            try:
                f = ico.garde(racine, d["jeu"], d["nom"], info, d.get("confirme_attribution") is True)
            except FileExistsError:
                raise RuntimeError("icone deja gardee") from None
            return {"chemin": f.relative_to(racine).as_posix(), "licence": info["licence"]}
        if chemin == "/ia/cle":
            c = config()
            fid, cle = fournisseur_valide(c, d.get("fournisseur")), d.get("cle")
            if cle not in (None, "") and (not isinstance(cle, str) or len(cle) > 512 or any(ch.isspace() or ord(ch) < 32 for ch in cle)):
                raise ValueError("cle invalide (512 caracteres au plus, sans espace)")
            cfg.regle(c, fid, cle=cle or None)
            cfg.ecrit(c)
            return {"fournisseur": fid, "cle": cfg.masque(cle)}
        env = env_valide(d.get("env"))
        if chemin == "/ia/demande":
            c = config()
            fid = fournisseur_valide(c, d.get("fournisseur"))
            if d.get("photo") is not None:
                try:
                    image = base64.b64decode(d["photo"], validate=True)
                except (binascii.Error, ValueError, TypeError):
                    raise ValueError("photo : base64 invalide") from None
            else:
                image = fond_garde(d.get("empreinte"))[0]
            return ia.demande(str(racine), env, fid, d.get("consigne"), image, d.get("confirme") is True, c, fabrique_ia)
        if chemin in ("/ecriture/prevoit", "/ecriture/ecrit"):
            fond, type_fond = fond_garde(d.get("empreinte_fond"))
            args = (racine, env, d.get("description"), fond, type_fond)
            if chemin == "/ecriture/prevoit":
                return ave.prevoit(*args)
            if not isinstance(d.get("empreinte"), str):
                raise ValueError("empreinte du diff absente")
            return {"ecrits": ave.ecrit(*args, d["empreinte"], builds)}
        raise LookupError("introuvable")

    return get, post

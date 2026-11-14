"""Fiches publiques des etiquettes en mode lien (plan etiquettes-qrcode A10) : HTML d'une fiche, publication sur GitHub Pages.

Une carte reglee `"contenu": "lien"` porte dans son QR code l'adresse fixe de sa fiche (`etiquettes_qr_modele.url_fiche`),
lisible partout. Les fiches vivent sur la branche orpheline `etiquettes` du depot, servie par GitHub Pages ; elles sont
regenerees a chaque publication, pour TOUTES les cartes en mode lien et elles seules (une carte repassee en texte voit sa
fiche retiree). La branche est ecrite par la plomberie git (hash-object, mktree, commit-tree) puis poussee SANS forcer, par
dessus sa pointe actuelle sur origin (fetch de cette seule ref) : l'arbre de travail, l'index et `development` ne bougent pas.

Filtre : une ligne de fiche passe d'abord le filtre de l'A2 (cle et valeur secretes du persist, dans `resout_avec`), puis
`etiquettes_qr_filtre_public.controle_public` sur la ligne telle que publiee (libelle, avant, valeur, apres). Une seule
ligne refusee bloque toute la publication : la raison est rendue, la ligne se retire dans la page.
"""

import datetime
import hashlib
import html
import json
import os
import re
import subprocess

import etiquettes_qr_filtre_public as filtre
import etiquettes_qr_modele as modele

BRANCHE = "etiquettes"
REF_DISTANTE = "refs/remotes/origin/" + BRANCHE
DELAI_RESEAU = 120                                 # s, fetch et push
DATE = re.compile(r'<p class="date">[^<]*</p>')

CSS = ("body{margin:0;font:16px/1.5 system-ui,sans-serif;background:#f6f7f9;color:#222}"
       "main{max-width:560px;margin:0 auto;padding:24px 16px}h1{font-size:22px;margin:0 0 16px;overflow-wrap:anywhere}"
       "dl{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;margin:0;background:#fff;border:1px solid #ddd;"
       "border-radius:8px;padding:14px}dt{color:#666}dd{margin:0;overflow-wrap:anywhere}.seule{grid-column:1 / 3}"
       ".date{color:#666;font-size:13px;margin-top:14px}"
       "@media (prefers-color-scheme:dark){body{background:#121417;color:#e6e6e6}dl{background:#1d2025;border-color:#3a3f47}"
       "dt,.date{color:#a8adb5}}")


def _git(racine, *args, entree=None, brut=False):
    # en octets : le mode texte de Windows changerait chaque \n envoye en \r\n (noms de l'arbre, contenu des fiches) ;
    # jamais d'invite d'identifiants (elle figerait la page), messages en anglais (texte de « ref absente » reconnu)
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "LC_ALL": "C"}
    try:
        r = subprocess.run(["git", "-C", str(racine), *args], input=None if entree is None else entree.encode("utf-8"),
                           stdin=subprocess.DEVNULL if entree is None else None, capture_output=True, env=env,
                           timeout=DELAI_RESEAU if args[0] in ("fetch", "push") else 60)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"git {args[0]} : pas de réponse en {DELAI_RESEAU} s (réseau ?)") from None
    sortie = r.stdout.decode("utf-8")
    erreur = re.sub(r"//[^@/\s]*@", "//", r.stderr.decode("utf-8", "replace").strip())     # jamais un jeton d'URL
    if r.returncode:
        raise RuntimeError(f"git {args[0]} : {erreur or r.returncode}")
    return sortie if brut else sortie.strip()


def url_fiche(racine, env):
    """Adresse publique de la fiche ; ValueError si le depot n'est pas sur GitHub."""
    return modele.url_fiche(racine, env)


def lignes_publiees(resolu, persist):
    """[(numero de ligne, libelle, valeur publiee, raison du refus | None)] des lignes lues (etat ok) d'un reglage resolu.
    Toute la ligne publiee (libelle, avant, valeur, apres, ligne libre) passe les deux filtres : secret du persist (A2),
    puis controle_public."""
    secrets = modele._valeurs_secretes(persist, set())
    res = []
    for n, l in enumerate(resolu["lignes"], 1):
        if l["etat"] != "ok":
            continue
        texte = f"{l['libelle']} {l['valeur']}"
        raison = "contient une valeur secrète du persist" if modele._sensible(texte, secrets) else filtre.controle_public(texte)
        res.append((n, l["libelle"], l["valeur"], raison))
    return res


def refus_de(resolu, persist):
    """Avertissements de l'apercu en mode lien : une ligne par valeur qui ne peut pas paraitre sur la fiche publique.
    Nommee par son seul numero : ni sa valeur ni son libelle ne sont recopies."""
    return [f"Ligne {n} : ne peut pas paraître sur la fiche publique, {raison}"
            for n, _, _, raison in lignes_publiees(resolu, persist) if raison]


def fiche_html(racine, env, reglage, envs=None, date=None):
    """HTML autonome de la fiche : aucune ressource externe, valeurs echappees, noindex, clair/sombre, date de publication."""
    persist = modele.persist_de(racine, env)
    resolu = modele.resout_avec(reglage, modele.champs_standards(racine, env, envs), persist)
    titre = html.escape(env)                     # deja public dans l'adresse ; le hostname ne passe que par une ligne
    lignes = []
    for _, lib, val, _ in lignes_publiees(resolu, persist):
        if lib:
            lignes.append(f"<dt>{html.escape(lib)}</dt><dd>{html.escape(val)}</dd>")
        else:
            lignes.append(f'<dd class="seule">{html.escape(val)}</dd>')
    date = date or datetime.date.today().isoformat()
    return ("<!DOCTYPE html>\n<html lang=\"fr\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<meta name=\"robots\" content=\"noindex, nofollow\"><meta name=\"color-scheme\" content=\"light dark\">"
            f"<title>{titre}</title><style>{CSS}</style></head>\n<body><main><h1>{titre}</h1><dl>"
            + "".join(lignes) + f"</dl>\n<p class=\"date\">Publiée le {date}</p></main></body></html>\n")


def _pointe(racine):
    """Pointe de la branche sur origin (fetch de cette seule ref), None si elle n'existe pas encore."""
    try:
        _git(racine, "fetch", "--quiet", "origin", f"+refs/heads/{BRANCHE}:{REF_DISTANTE}")
    except RuntimeError as e:
        if "couldn't find remote ref" not in str(e):
            raise RuntimeError(f"lecture de la branche {BRANCHE} sur origin impossible : {e}") from None
        return None
    return _git(racine, "rev-parse", REF_DISTANTE)


def _publies(racine, pointe):
    if not pointe:
        return {}
    noms = _git(racine, "ls-tree", "--name-only", pointe).splitlines()
    return {n: _git(racine, "cat-file", "blob", f"{pointe}:{n}", brut=True) for n in noms}


def prevoit_publication(racine, envs, cartes=None):
    """{fichiers: [{chemin, avant, apres}] qui changent, refus: [{env, raison}], publies: [env], url, empreinte}.
    `envs` : noms des cartes du depot ; seules celles reglees en mode lien sont publiees. `cartes` : liste de
    `build_envs.liste_envs` deja lue."""
    lien = [e for e in sorted(envs) if modele.charge_reglage(racine, e).get("contenu") == "lien"]
    pointe = _pointe(racine)
    avant = _publies(racine, pointe)
    apres, refus = {".nojekyll": ""}, []
    for env in lien:
        reglage = modele.charge_reglage(racine, env)
        persist = modele.persist_de(racine, env)
        resolu = modele.resout_avec(reglage, modele.champs_standards(racine, env, cartes), persist)
        refus += [{"env": env, "raison": r} for r in refus_de(resolu, persist)]
        f = fiche_html(racine, env, reglage, cartes)
        ancien = avant.get(f"{env}.html")
        # meme contenu a la date pres : la fiche publiee est gardee (pas de nouvel envoi chaque jour)
        apres[f"{env}.html"] = ancien if ancien and DATE.sub("", ancien) == DATE.sub("", f) else f
    fichiers = [{"chemin": n, "avant": avant.get(n), "apres": apres.get(n)}
                for n in sorted(set(avant) | set(apres)) if avant.get(n) != apres.get(n)]
    empreinte = hashlib.sha256(json.dumps([pointe, apres], sort_keys=True).encode("utf-8")).hexdigest()
    return {"fichiers": fichiers, "refus": refus, "publies": lien, "pointe": pointe, "contenu": apres,
            "url": modele.url_depot(racine), "empreinte": empreinte}


def publie(racine, envs, empreinte, builds_en_cours, cartes=None, prevu=None):
    """Pousse les fiches sur `etiquettes` ; sha du commit, ou None si rien ne change. RuntimeError : build en cours (ou
    detection impossible), ligne refusee, empreinte perimee, push refuse (la branche a bouge ailleurs). `prevu` : une
    prevision deja faite (publie_tout), sans second fetch."""
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("détection des builds en cours impossible : publication refusée, réessayer")
    if builds:
        raise RuntimeError("un build est en cours : publication refusée")
    p = prevu or prevoit_publication(racine, envs, cartes)
    if p["refus"]:
        raise RuntimeError("publication refusée : " + " ; ".join(f"{r['env']} : {r['raison']}" for r in p["refus"]))
    if p["empreinte"] != empreinte:
        raise RuntimeError("les fiches ont changé depuis l'aperçu : relancer « Publier… »")
    if not p["fichiers"]:
        return None
    entrees = "".join(f"100644 blob {_git(racine, 'hash-object', '-w', '--stdin', entree=contenu)}\t{nom}\n"
                      for nom, contenu in sorted(p["contenu"].items()))
    arbre = _git(racine, "mktree", entree=entrees)
    parent = ["-p", p["pointe"]] if p["pointe"] else []
    sha = _git(racine, "commit-tree", arbre, *parent, "-m", f"etiquettes : fiches publiques ({len(p['publies'])} carte(s))")
    _git(racine, "push", "--quiet", "origin", f"{sha}:refs/heads/{BRANCHE}")
    try:
        _git(racine, "update-ref", REF_DISTANTE, sha)
    except RuntimeError:
        pass                                     # fiches en ligne : la ref locale sera relue au prochain fetch
    return sha


# --- A11 : publication automatisee (page 7970, page Build, sortie du build) -------------------------------------------

def fiche_a_republier(racine, env, cartes=None):
    """Vrai si la fiche en ligne de `env` ne correspond plus a son reglage, SANS reseau : compare a la derniere pointe
    connue (`refs/remotes/origin/etiquettes`, mise a jour par chaque publication), date ignoree. Carte en texte : vrai
    seulement si une fiche est encore en ligne (a retirer)."""
    try:
        publiee = _git(racine, "cat-file", "blob", f"{REF_DISTANTE}:{modele._env_valide(env)}.html", brut=True)
    except RuntimeError:
        publiee = None                           # pas de branche connue, ou pas de fiche pour cette carte
    reglage = modele.charge_reglage(racine, env)
    if reglage.get("contenu") != "lien":
        return publiee is not None
    return publiee is None or DATE.sub("", publiee) != DATE.sub("", fiche_html(racine, env, reglage, cartes))


def publie_tout(racine, builds_en_cours):
    """Publie les fiches de toutes les cartes du depot (page Build, fin de serie) : sha, ou None si rien ne change.
    RuntimeError : ligne refusee, build en cours, reseau. Pas de diff montre : l'utilisateur l'a choisi par sa case."""
    import build_envs
    cartes = build_envs.liste_envs(racine)
    envs = [e.nom for e in cartes if e.famille == "cartes"]
    p = prevoit_publication(racine, envs, cartes)
    return publie(racine, envs, p["empreinte"], builds_en_cours, cartes, prevu=p)


GH = ["gh"]                                      # remplace par un faux gh dans le banc


def _gh(racine, *args):
    """(code, sortie, erreur) d'un appel a gh pour le depot GitHub de `racine` ; jamais d'invite."""
    base = modele.url_depot(racine)
    if not base:
        raise RuntimeError("le remote origin du dépôt n'est pas sur GitHub")
    m = re.match(r"https://([^.]+)\.github\.io/([^/]+)/", base)
    if not m:
        raise RuntimeError(f"adresse GitHub Pages inattendue : {base}")
    proprio, depot = m.groups()
    args = [a.replace("{depot}", f"repos/{proprio}/{depot}") for a in args]
    try:
        r = subprocess.run([*GH, *args], capture_output=True, stdin=subprocess.DEVNULL, timeout=60,
                           env={**os.environ, "GH_PROMPT_DISABLED": "1", "NO_COLOR": "1"})
    except FileNotFoundError:
        raise RuntimeError("gh (GitHub CLI) introuvable : activer Pages à la main sur github.com") from None
    except subprocess.TimeoutExpired:
        raise RuntimeError("gh : pas de réponse en 60 s") from None
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace").strip()


def etat_pages(racine):
    """{"actif": bool, "url", "branche"} de GitHub Pages du depot ; RuntimeError si gh ne repond pas (non connecte...)."""
    code, sortie, erreur = _gh(racine, "api", "{depot}/pages")
    if code == 0:
        d = json.loads(sortie or "{}")
        return {"actif": True, "url": d.get("html_url"), "branche": (d.get("source") or {}).get("branch")}
    if "HTTP 404" in erreur:
        return {"actif": False, "url": None, "branche": None}
    raise RuntimeError(f"gh : {erreur or code}")


def active_pages(racine):
    """Active GitHub Pages sur la branche `etiquettes`, dossier racine (une fois). RuntimeError avec le message de gh."""
    code, _, erreur = _gh(racine, "api", "-X", "POST", "{depot}/pages", "-f", f"source[branch]={BRANCHE}", "-f", "source[path]=/")
    if code:
        raise RuntimeError(f"activation de GitHub Pages refusée : {erreur or code}")

"""Alerte du coprocesseur Wi-Fi des P4 (data/fs/controleCoprocesseur.be) a la creation d'un env (2026-10-26).

Une carte nait d'un modele (fichiers_berry_creation) : sa section du cenv, son persist et son autoexec sont
recopies. L'alerte « firmware du coprocesseur ESP32-C6 pas a jour » ne vaut que sur un P4 : selon la PUCE de la
base choisie, ces trois copies sont ajustees, quel que soit le modele.
  - base P4 (tasmota32p4*) : bloc serveur.coprocesseur ajoute au persist s'il manque, cle "bloque" ajoutee au
    bloc si elle y manque (decide le 2026-10-27, voir VERSION_BLOQUEE), ligne
    demarrage.charge(["controleCoprocesseur"], "serveur.coprocesseur") ajoutee a l'autoexec s'il ne la porte
    pas, module retire des custom_files_exclude (il est alors charge depuis le LittleFS ; le P4 du garage le
    solidifie, une copie de sa section le solidifie aussi) ;
  - autre puce : activation "ON" -> "OFF" dans le persist (demarrage.charge ne l'importe plus), module retire
    de custom_berry_solidify et ajoute a custom_files_exclude (ni flash ni LittleFS).
Le persist n'est retouche que par insertion ou remplacement dans le TEXTE (octets du reste gardes, comme
fichiers_berry_creation._persist). Importe par fichiers_berry_creation : il ne l'importe pas en retour. Chaque ajustement est rendu en avertissement, visible dans la page.
"""

import json
import re

CHEMIN = "data/fs/controleCoprocesseur.be"
LIGNE_AUTOEXEC = ('demarrage.charge(["controleCoprocesseur"], "serveur.coprocesseur")'
                  "    # alerte « firmware du C6 pas a jour » (accueil web, MQTT)")
# Version du C6 qui refuse tout OTA (bug esp-hosted-mcu #143 : bootloader DIO + application QIO 2.1 a 2.8), constatee
# sur le P4 du garage le 2026-10-26. Posee d'office sur toute nouvelle carte P4 (decision de l'utilisateur, 2026-10-27) :
# sans elle, la carte ne l'apprendrait qu'apres un essai rate, et le perdrait au flash serie suivant (FS reecrit).
# Sans risque : si le C6 de la carte est dans une autre version, controleCoprocesseur.be l'efface au demarrage.
VERSION_BLOQUEE = "2.6.6"
BLOC = (("activation", "ON"), ("url", "https://ota.tasmota.com/tasmota32/coprocessor"), ("mqtt", "ON"),
        ("bloque", VERSION_BLOQUEE))
OPTION = re.compile(r"([A-Za-z_][\w.]*)\s*=\s*(.*)$")


def est_p4(base):
    return base.split("-")[0].startswith("tasmota32p4")


# ---- Section du cenv -------------------------------------------------------------------------------------
def _valeur(ligne):
    return ligne.split(";")[0].strip()


def _continuation(ligne):
    s = ligne.strip()
    return bool(s) and ligne[:1].isspace() and s[0] not in ";#"


def _options(lignes):
    """{option: (indice de la ligne 'option =', [indices des lignes de continuation])}"""
    res, courante = {}, None
    for i, l in enumerate(lignes[1:], 1):
        m = OPTION.match(l)
        if m:
            courante = m.group(1)
            res[courante] = (i, [])
        elif courante and _continuation(l):
            res[courante][1].append(i)
        elif l.strip() and l.strip()[0] not in ";#":
            courante = None
    return res


def _contient(lignes, option):
    o = _options(lignes).get(option)
    if o is None:
        return False
    i, suite = o
    return OPTION.match(lignes[i]).group(2).split(";")[0].strip() == CHEMIN or any(_valeur(lignes[k]) == CHEMIN for k in suite)


def _retire(lignes, option):
    o = _options(lignes).get(option)
    if o is None:
        return lignes
    i, suite = o
    res = list(lignes)
    for k in reversed(suite):
        if _valeur(res[k]) == CHEMIN:
            del res[k]
    m = OPTION.match(res[i])
    if m.group(2).split(";")[0].strip() == CHEMIN:
        col = res[i].index(m.group(2))
        if i + 1 < len(res) and _continuation(res[i + 1]):
            res[i] = res[i][:col] + res[i + 1].strip()                 # la valeur suivante remonte sur la ligne
            del res[i + 1]
        else:
            del res[i]                                                  # liste reduite a ce seul fichier
    return res


def _ajoute(lignes, option):
    o = _options(lignes).get(option)
    res = list(lignes)
    if o is None:
        res.append(f"{option:<30}=   {CHEMIN}")
        return res
    i, suite = o
    m = OPTION.match(res[i])
    col = res[i].index(m.group(2)) if m.group(2) else len(res[i])
    res.insert((suite[-1] if suite else i) + 1, " " * col + CHEMIN)
    return res


def adapte_cenv(lignes, p4, avertissements):
    """Section copiee du modele (liste de lignes, en-tete compris), ajustee a la puce de la base."""
    if p4:
        if _contient(lignes, "custom_files_exclude"):
            avertissements.append(f"carte P4 : {CHEMIN} retire de custom_files_exclude (alerte du coprocesseur Wi-Fi)")
            return _retire(lignes, "custom_files_exclude")
        return lignes
    res = lignes
    if _contient(res, "custom_berry_solidify"):
        res = _retire(res, "custom_berry_solidify")
        avertissements.append(f"carte sans coprocesseur Wi-Fi : {CHEMIN} retire de custom_berry_solidify")
    if not _contient(res, "custom_files_exclude"):
        res = _ajoute(res, "custom_files_exclude")
        avertissements.append(f"carte sans coprocesseur Wi-Fi : {CHEMIN} ajoute a custom_files_exclude")
    return res


# ---- Persist ---------------------------------------------------------------------------------------------
def _membres(texte, debut):
    """Membres DIRECTS de l'objet dont le '{' est a l'indice debut : [(cle, debut de la cle, debut de la valeur,
    fin de la valeur)]. Meme lecture que fichiers_berry_creation.spans_json (texte JSON deja valide)."""
    n = len(texte)

    def blanc(i):
        while i < n and texte[i] in " \t\r\n﻿":
            i += 1
        return i

    def chaine(i):
        j = i + 1
        while texte[j] != '"':
            j += 2 if texte[j] == "\\" else 1
        return j + 1

    def valeur(i):
        i = blanc(i)
        if texte[i] == '"':
            return chaine(i)
        if texte[i] in "{[":
            fermant = "}" if texte[i] == "{" else "]"
            i = blanc(i + 1)
            while texte[i] != fermant:
                if fermant == "}":
                    i = blanc(blanc(chaine(i)) + 1)             # cle, puis ':'
                i = blanc(valeur(i))
                if texte[i] == ",":
                    i = blanc(i + 1)
            return i + 1
        while i < n and texte[i] not in ",}] \t\r\n":
            i += 1
        return i

    res, i = [], blanc(debut + 1)
    while texte[i] != "}":
        fin_cle = chaine(i)
        cle = json.loads(texte[i:fin_cle])
        v = blanc(blanc(fin_cle) + 1)
        fin = valeur(v)
        res.append((cle, i, v, fin))
        i = blanc(fin)
        if texte[i] == ",":
            i = blanc(i + 1)
    return res


def adapte_persist(texte, p4, avertissements):
    """Persist de la nouvelle carte (texte), ajuste a la puce de la base. Texte invalide : rendu tel quel."""
    try:
        donnees = json.loads(texte)
    except ValueError:
        avertissements.append("_persist.json illisible : alerte du coprocesseur Wi-Fi non ajustee")
        return texte
    serveur = donnees.get("serveur") if isinstance(donnees, dict) else None
    bloc = serveur.get("coprocesseur") if isinstance(serveur, dict) else None
    if not isinstance(serveur, dict):
        return texte
    entree = next(m for m in _membres(texte, texte.index("{")) if m[0] == "serveur")
    enfants = _membres(texte, entree[2])
    if not p4:
        if isinstance(bloc, dict) and bloc.get("activation") == "ON":
            copro = next(m for m in enfants if m[0] == "coprocesseur")
            activation = next(m for m in _membres(texte, copro[2]) if m[0] == "activation")
            avertissements.append("carte sans coprocesseur Wi-Fi : serveur.coprocesseur.activation passe a OFF")
            return texte[:activation[2]] + '"OFF"' + texte[activation[3]:]
        return texte
    if isinstance(bloc, dict):
        if "bloque" in bloc:
            return texte
        copro = next(m for m in enfants if m[0] == "coprocesseur")
        membres = _membres(texte, copro[2])
        if not membres:
            avertissements.append('_persist.json : bloc serveur.coprocesseur vide, cle "bloque" a ajouter a la main')
            return texte
        _, cle, _, fin = membres[-1]
        eol = "\r\n" if "\r\n" in texte else "\n"
        ind = texte[texte.rfind("\n", 0, cle) + 1:cle]
        avertissements.append(f'carte P4 : serveur.coprocesseur.bloque = "{VERSION_BLOQUEE}" ajoute au persist '
                              "(C6 qui refuse les mises a jour par le reseau, efface par la carte si son C6 differe)")
        return texte[:fin] + f',{eol}{ind}"bloque": {json.dumps(VERSION_BLOQUEE)}' + texte[fin:]
    if bloc is not None:
        return texte
    if not enfants:
        avertissements.append("_persist.json : bloc serveur vide, serveur.coprocesseur a ajouter a la main")
        return texte
    _, cle, _, fin = enfants[-1]
    eol = "\r\n" if "\r\n" in texte else "\n"
    ind = texte[texte.rfind("\n", 0, cle) + 1:cle]
    unite = "\t" if ind.startswith("\t") else "    "
    membres = ("," + eol).join(f'{ind}{unite}"{k}": {json.dumps(v)}' for k, v in BLOC)
    ajout = f',{eol}{ind}"coprocesseur": {{{eol}{membres}{eol}{ind}}}'
    avertissements.append("carte P4 : bloc serveur.coprocesseur ajoute au persist (alerte du coprocesseur Wi-Fi)")
    return texte[:fin] + ajout + texte[fin:]


# ---- Autoexec --------------------------------------------------------------------------------------------
def adapte_autoexec(texte, p4, avertissements):
    """Autoexec de la nouvelle carte : sur un P4, la ligne de chargement ajoutee a la fin du bloc
    'if demarrage.prologue()' si elle manque. Ailleurs, inchange (activation OFF dans le persist suffit)."""
    if not p4 or "controleCoprocesseur" in texte:
        return texte
    eol = "\r\n" if "\r\n" in texte else "\n"
    lignes = texte.split(eol)
    ouverture = next((i for i, l in enumerate(lignes) if re.match(r"\s*if\s+demarrage\.prologue\(\)", l)), None)
    fin = next((i for i in range(len(lignes) - 1, -1, -1) if re.fullmatch(r"end\s*", lignes[i])), None)
    if ouverture is None or fin is None or fin < ouverture:
        avertissements.append("autoexec.be sans bloc « if demarrage.prologue() » : ligne "
                              + LIGNE_AUTOEXEC.split("    #")[0] + " a ajouter a la main")
        return texte
    precedente = next((lignes[i] for i in range(fin - 1, ouverture, -1) if lignes[i].strip()), "    x")
    ind = precedente[:len(precedente) - len(precedente.lstrip())] or "    "
    lignes.insert(fin, ind + LIGNE_AUTOEXEC)
    avertissements.append("carte P4 : chargement de controleCoprocesseur ajoute a l'autoexec")
    return eol.join(lignes)

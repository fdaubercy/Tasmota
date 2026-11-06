#!/usr/bin/env python3
"""Banc de autoexec_commandes.py : commandes connues et commandes qui redemarrent (plan autoexec-bat, A1).

Sans reseau : le fige est compare au code C du fork et aux .be de data/fs ; la doc n'est jamais telechargee.
Faux depot en dossier temporaire pour les regles de lecture (macros, prefixe, #ifdef, synonymes, classement).
Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_autoexec_commandes.py
"""
import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path

import autoexec_commandes as ac

RACINE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RACINE / "outils_docs" / "scripts_python" / "build"))
import lecture_gardes as lg  # noqa: E402 - contrat avec l'etape A4 : les chemins s'evaluent tels quels

ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


I18N = '#define D_CMND_HOSTNAME "Hostname"\n#define D_CMND_TOPIC "Topic"\n#define D_PRFX_ESSAI "Es"\n' \
       '#define D_CMND_SO "SO"\n#define D_CMND_SETOPTION "SetOption"\n'
INO = r'''
#define D_CMND_LOCAL "Local"
const char kEssaiCommands[] PROGMEM = "|"  // No prefix
  "Synonyme|" D_CMND_HOSTNAME "|"
#ifdef USE_RIEN
  D_CMND_TOPIC "|"
#endif
  D_CMND_LOCAL "|Valeur|Option";
SO_SYNONYMS(kEssaiSynonyms, 151,);
void (* const EssaiCommand[])(void) PROGMEM = {
  &CmndHost,
#ifdef USE_RIEN
  &CmndTopique,
#endif
  &CmndLocal, &CmndValeur, &CmndOption };
const char kPrefCommands[] PROGMEM = D_PRFX_ESSAI "|" "|Code|";
void (* const PrefCommand[])(void) PROGMEM = { &CmndEs, &CmndCode };
const char kBrancheCommands[] PROGMEM = "|Un|"
#ifdef USE_RIEN
  "Deux|Trois|"
#else
  "Trois|"
#endif
  "Quatre";
void (* const BrancheCommand[])(void) PROGMEM = { &CmndUn,
#ifdef USE_RIEN
  &CmndDeux, &CmndTrois, &CmndQuatre,
#else
  &CmndTrois, &CmndQuatre,
#endif
  };
void CmndEs(void) { TasmotaGlobal.restart_flag = 2; }
void CmndQuatre(void)
{
  if (XdrvMailbox.payload == 1) TasmotaGlobal.restart_flag = 2;
}
void CmndHost(void) {
  if (XdrvMailbox.data_len > 0) {
    Response_P(PSTR("{\"a\":1}"));  // accolade dans une chaine
    TasmotaGlobal.restart_flag = 2;
  }
}
void CmndTopique(void) {
  if (strcmp(SettingsText(SET_MQTT_TOPIC), XdrvMailbox.data)) { TasmotaGlobal.restart_flag = 2; }
}
void CmndLocal(void) { TasmotaGlobal.restart_flag = 2; }
void CmndValeur(void) {
  if (Settings->valeur != XdrvMailbox.payload) {
    Settings->valeur = XdrvMailbox.payload;
    TasmotaGlobal.restart_flag = 2;
  }
}
void CmndOption(void) {
  switch (XdrvMailbox.payload) {
  case 1:
    TasmotaGlobal.restart_flag = 210 + XdrvMailbox.payload;
    break;
  }
}
void CmndCode(void) { TasmotaGlobal.restart_flag = 0; }
bool Xdrv99(uint32_t function) {
  DecodeCommand(kEssaiCommands, EssaiCommand, kEssaiSynonyms);
  DecodeCommand(kPrefCommands, PrefCommand);
  DecodeCommand(kBrancheCommands, BrancheCommand);
}
'''
BE = "tasmota.add_cmd('ReglageEssai', def () end)\ntasmota.add_cmd(\"Br2Essai\", f)\n"
DOC = ("Command|Parameters\n:---|:---\n"
       "Hostname<a class=\"cmnd\" id=\"hostname\"></a>|`<value>` = set hostname and restart\n"
       "Code<a class=\"cmnd\" id=\"code\"></a>|code sans rien\n"
       "Valeur<x\\><a class=\"cmnd\" id=\"valeur\"></a>|Set value. Causes a reboot\n"
       "Synonyme<a class=\"cmnd\" id=\"synonyme\"></a>|`1` = set it and restart\n"
       "Un<a class=\"cmnd\" id=\"un\"></a>|value kept after restart\n")


def faux_depot(dossier):
    (dossier / "tasmota" / "include").mkdir(parents=True)
    (dossier / "tasmota" / "include" / "i18n.h").write_text(I18N, encoding="utf-8")
    (dossier / "tasmota" / "xdrv_99_essai.ino").write_text(INO, encoding="utf-8")
    (dossier / "data" / "fs").mkdir(parents=True)
    (dossier / "data" / "fs" / "essai.be").write_text(BE, encoding="utf-8")
    return dossier


# Gardes : fichiers a part, `regles` compte les connues et les anomalies du depot de base.
INO_GARDES = r'''
#ifdef USE_SIMPLE
#define XDRV_98 98
const char kSimpleCommands[] PROGMEM = D_PRFX_ESSAI "|Simple";
#endif
const char kDansCommands[] PROGMEM = "|Libre|"
#ifdef USE_LIGNE
  "Gardee|"
#endif
  "Apres";
#if   defined(USE_A)  &&  defined(USE_B)
const char kComboCommands[] PROGMEM = "|Combo";
#endif
#ifndef USE_N
const char kNonCommands[] PROGMEM = "|Negatif";
#endif
const char kBrCommands[] PROGMEM = "|"
#ifdef USE_E
  "BrancheSi|"
#else
  "BrancheSinon|"
#endif
#if defined(E1)
  "EtapeUn|"
#elif defined(E2)
  "EtapeDeux|"
#else
  "EtapeTrois|"
#endif
  "FinBr";
#define USE_LOCALE
#ifdef USE_LOCALE
const char kLocaleCommands[] PROGMEM = "|Locale";
#endif
#ifndef FIRMWARE_MINIMAL
const char kMinCommands[] PROGMEM = "|HorsMinimal";
#endif
#ifdef USE_Z2
#ifdef USE_LOCALE
const char kLocale2Commands[] PROGMEM = "|LocaleGardee";
#endif
#endif
#ifdef USE_RG
const char kRegleCommands[] PROGMEM = "|Abonne|SeulRegle|AbonneB";
#endif
#ifdef USE_SC
const char kScrCommands[] PROGMEM = "Scr|Abonne|" D_CMND_MACRO_INCONNUE "|SeulScript";
#endif
#ifdef USE_SD
const char kScr2Commands[] PROGMEM = "AbonneB|Autre";
#endif
void Scr(void) {
  int c = GetCommandCode(command, sizeof(command), XdrvMailbox.topic + 1, kScrCommands);
  if (GetCommandCode(command, sizeof(command), topic, kScr2Commands) >= 0) { f(x, y); }
}
const char kIllisibleCommands[] PROGMEM = "|FragA|" D_CMND_MACRO_INCONNUE "|FragB";
const char kIllPrefCommands[] PROGMEM = "Pq|FragC|" D_CMND_MACRO_INCONNUE;
#ifdef USE_H
const char kGardeHCommands[] PROGMEM = "|FragA|FragB|HorsIllisible";
const char kGardePqCommands[] PROGMEM = "Pq|FragC";
#endif
#ifdef USE_J
#else
const char kSeulSinonCommands[] PROGMEM = "|SinonSeul";
#endif
#ifdef USE_K
const char kGardeKCommands[] PROGMEM = "|SinonSeul|HorsSinon";
#endif
#ifdef USE_EXT
#if USE_VAL > 2
const char kNicheCommands[] PROGMEM = "|Niche|"
#ifdef USE_LIGNE2
  "NicheLigne"
#endif
  ;
#endif
#endif
const char kDoubleCommands[] PROGMEM = "|"
#ifdef USE_D
  "Double|"
#else
  "Double|"
#endif
  "Fin";
#ifdef USE_W
const char kBisCommands[] PROGMEM = "|Bis|BisSi";
#else
const char kBisCommands[] PROGMEM = "|Bis|BisSinon";
#endif
#ifdef USE_M
const char kMemeCommands[] PROGMEM = "|Meme|SeulSi";
#else
const char kMemeCommands[] PROGMEM = "|Meme|" D_CMND_INCONNUE "|SeulSinon";
#endif
const char kMixteCommands[] PROGMEM = "|Mi"
#ifdef USE_X
  "xte|ApresMixte"
#endif
  ;
#ifdef USE_PRF
const char kPrefixeCommands[] PROGMEM = "Pf|" "|Xy|"
#ifdef USE_PL
  "Ligne"
#endif
  ;
#endif
#ifdef USE_Q
const char kPartageCommands[] PROGMEM = "|Partagee|DeuxFois";
#endif
#ifdef USE_B2
const char kBerryCommands[] PROGMEM = "|EnBerry";
#endif
#ifdef USE_SO
const char kSoCommands[] PROGMEM = "|SO77|SetOption78";
#endif
void Inc(void) { DecodeCommand(kIncCommands, IncCommand); DecodeCommand(kIncGardeCommands, IncGardeCommand); }
'''
INO_AUTRE_DRIVER = r'''
#ifdef USE_P
const char kPCommands[] PROGMEM = "|Partagee";
#endif
const char kLibreCommands[] PROGMEM = "|DeuxFois";
void Autre(void) { DecodeCommand(kPCommands, PCommand); DecodeCommand(kLibreCommands, LibreCommand); }
'''
INO_NON_INCLUSION = r'''
#ifndef USE_N2
#define XSNS_96 96
const char kPasCommands[] PROGMEM = "|PasInclusion";
#endif
void Pas(void) { DecodeCommand(kPasCommands, PasCommand); }
'''
H_INCLUSION = r'''
#ifndef _GARDES_H_
#define _GARDES_H_
const char kIncCommands[] PROGMEM = "|Incluse";
#ifdef USE_I
const char kIncGardeCommands[] PROGMEM = "|InclusGarde";
#endif
#endif
'''
INO_ELIFDEF = r'''
const char kEfCommands[] PROGMEM = "|"
#ifdef USE_F1
  "EfUn|"
#elifdef USE_F2
  "EfDeux|"
#endif
  "EfFin";
void Ef(void) { DecodeCommand(kEfCommands, EfCommand); }
'''
INO_NON_FERME = r'''
#ifdef USE_D2
const char kDesCommands[] PROGMEM = "|Desequilibre";
void Des(void) { DecodeCommand(kDesCommands, DesCommand); }
'''
INO_ENDIF_EN_TROP = r'''
#endif
#ifdef USE_D3
const char kTropCommands[] PROGMEM = "|EnTrop";
#endif
void Trop(void) { DecodeCommand(kTropCommands, TropCommand); }
'''
ATTENDU_GARDES = {
    # depot de base : garde dans la table, deux branches
    "TOPIC": [["defined(USE_RIEN)"]], "DEUX": [["defined(USE_RIEN)"]],
    "TROIS": [["!(defined(USE_RIEN))"], ["defined(USE_RIEN)"]],
    "ESSIMPLE": [["defined(USE_SIMPLE)"]],                     # le #define XDRV qui suit n'en fait pas une garde d'inclusion
    "GARDEE": [["defined(USE_LIGNE)"]],
    "COMBO": [["defined(USE_A) && defined(USE_B)"]],           # espaces normalises
    "NEGATIF": [["!defined(USE_N)"]],
    "BRANCHESI": [["defined(USE_E)"]], "BRANCHESINON": [["!(defined(USE_E))"]],
    "ETAPEUN": [["defined(E1)"]], "ETAPEDEUX": [["!(defined(E1))", "defined(E2)"]],
    "ETAPETROIS": [["!(defined(E1))", "!(defined(E2))"]],
    "NICHE": [["defined(USE_EXT)", "USE_VAL > 2"]],
    "NICHELIGNE": [["defined(USE_EXT)", "USE_VAL > 2", "defined(USE_LIGNE2)"]],
    "DOUBLE": [["!(defined(USE_D))"], ["defined(USE_D)"]],
    "BIS": [["!(defined(USE_W))"], ["defined(USE_W)"]], "BISSI": [["defined(USE_W)"]],
    # 2e emplacement illisible : sa garde de table vaut pour tous les noms, jamais de garde inventee
    "MEME": [["!(defined(USE_M))"], ["defined(USE_M)"]], "SEULSI": [["!(defined(USE_M))"], ["defined(USE_M)"]],
    "APRESMIXTE": [["defined(USE_X)"]],                        # MIXTE, a cheval sur deux piles : garde de la table, donc aucune
    "PF": [["defined(USE_PRF)"]], "PFXY": [["defined(USE_PRF)"]], "PFLIGNE": [["defined(USE_PRF)", "defined(USE_PL)"]],
    "PARTAGEE": [["defined(USE_P)"], ["defined(USE_Q)"]],      # deux drivers ; DEUXFOIS : une presence libre, aucune cle
    "PASINCLUSION": [["!defined(USE_N2)"]],
    "INCLUSGARDE": [["defined(USE_I)"]],                       # INCLUSE : garde d'inclusion du .h, aucune cle
    "LOCALEGARDEE": [["defined(USE_Z2)"]],                     # USE_LOCALE, pose par un .ino : condition retiree ; LOCALE : aucune cle
    # table lue par GetCommandCode : un chemin de plus, sans prefixe, macro inconnue toleree ; SEULSCRIPT n'est pas une commande connue
    "ABONNE": [["defined(USE_RG)"], ["defined(USE_SC)"]], "ABONNEB": [["defined(USE_RG)"], ["defined(USE_SD)"]],
    "SEULREGLE": [["defined(USE_RG)"]],
    # FRAGA, FRAGB, PQFRAGC : aussi dans une table illisible ; SINONSEUL : aussi dans une table du seul #else ; aucune cle
    "HORSILLISIBLE": [["defined(USE_H)"]], "HORSSINON": [["defined(USE_K)"]],
}


def avec_decode(texte):
    """Le texte, plus un DecodeCommand par table ; kScr* restent lues par le seul GetCommandCode."""
    tables = sorted(t for t in set(re.findall(r"char (k\w+)\[", texte)) if not t.startswith("kScr"))
    return texte + "bool Xdrv98(uint32_t function) {\n" + "".join(f"  DecodeCommand({t}, {t[1:]});\n" for t in tables) + "}\n"


def fichiers_gardes(dossier):
    for nom, texte in (("xdrv_98_gardes.ino", avec_decode(INO_GARDES)), ("xdrv_97_autre.ino", INO_AUTRE_DRIVER), ("xsns_96_pas.ino", INO_NON_INCLUSION),
                       ("xdrv_95_ferme.ino", INO_NON_FERME), ("xdrv_93_ef.ino", INO_ELIFDEF), ("xdrv_94_trop.ino", INO_ENDIF_EN_TROP), ("include/gardes.h", H_INCLUSION)):
        (dossier / "tasmota" / nom).write_text(texte, encoding="utf-8")
    (dossier / "data" / "fs" / "gardes.be").write_text("tasmota.add_cmd('EnBerry', def () end)\n", encoding="utf-8")
    return dossier


def regles_gardes():
    with tempfile.TemporaryDirectory() as t:
        d = ac.genere(fichiers_gardes(faux_depot(Path(t))))
        g, c = d.get("gardes", {}), d["connues"]
        for nom in sorted(set(g) | set(ATTENDU_GARDES)):
            verifie(g.get(nom), ATTENDU_GARDES.get(nom), f"gardes {nom}")
        # chacune : connue, mais sans garde (toujours compilee, Berry, SetOption, #if desequilibres, a cheval sur deux piles)
        for nom in ("HOSTNAME", "LIBRE", "APRES", "FIN", "FINBR", "MIXTE", "DEUXFOIS", "INCLUSE", "LOCALE", "HORSMINIMAL", "ENBERRY", "SETOPTION77",
                    "SETOPTION78", "DESEQUILIBRE", "ENTROP", "FRAGA", "FRAGB", "PQFRAGC", "SINONSEUL", "EFUN", "EFDEUX", "EFFIN"):
            verifie((nom in c, nom in g), (True, False), f"connue sans garde : {nom}")
        verifie(("SEULSCRIPT" in c, "SEULSCRIPT" in g, "AUTRE" in c, "SCR" in c), (False,) * 4, "table de GetCommandCode : connues inchangees")
        verifie("BISSINON" in c or "BISSINON" in g, False,"2e definition d'une table : nom hors de connues (limite existante), pas de garde")
        verifie(list(g), sorted(g), "gardes triees")
        fige = Path(t) / "fige.json"
        fige.write_text(json.dumps(d), encoding="utf-8")
        verifie(ac.verifie(Path(t), fige=fige), [], "gardes : fige conforme -> aucun ecart")
        d["gardes"] = {k: v for k, v in d.get("gardes", {}).items() if k != "GARDEE"}
        fige.write_text(json.dumps(d), encoding="utf-8")
        verifie(len(ac.verifie(Path(t), fige=fige)), 1, "gardes : cle retiree du fige -> 1 ecart")
    ctx = lg.Contexte({"USE_A": None}, definies=set())
    for expr, attendu in (("defined(USE_A)", True), ("!defined(USE_A)", False), ("!(defined(USE_A))", False), ("!(!defined(USE_A))", True),
                          ("defined(USE_B)", False), ("!(defined(USE_B))", True), ("defined(USE_A) && defined(USE_B)", False)):
        verifie(lg.evalue(expr, ctx, {}), attendu, f"lecture_gardes.evalue {expr}")


def regles():
    with tempfile.TemporaryDirectory() as t:
        d = ac.genere(faux_depot(Path(t)))
        c, r = d["connues"], d["redemarrent"]
        verifie(sorted(c), ["BR2ESSAI", "DEUX", "ES", "ESCODE", "HOSTNAME", "LOCAL", "OPTION", "QUATRE", "REGLAGEESSAI", "SYNONYME", "TOPIC",
                 "TROIS", "UN", "VALEUR"],
                "faux depot : noms des tables (macros, prefixe, #ifdef) et des add_cmd")
        verifie("data/fs/essai.be" in c.get("REGLAGEESSAI", ""), True, "faux depot : source d'une commande Berry")
        verifie(r.get("HOSTNAME", {}).get("quand"), "toujours", "condition sur l'argument seul -> toujours")
        verifie(r.get("LOCAL", {}).get("quand"), "toujours", "sans condition -> toujours")
        verifie(r.get("VALEUR", {}).get("quand"), "si-change", "comparaison au reglage (!=) -> si-change")
        verifie(r.get("TOPIC", {}).get("quand"), "si-change", "comparaison au reglage (strcmp) -> si-change")
        verifie("CmndTopique" in r.get("TOPIC", {}).get("source", ""), True, "pointeurs alignes malgre le #ifdef")
        verifie(r.get("ES", {}).get("quand"), "toujours", "nom vide = le prefixe seul ; « | » final ignore")
        verifie(r.get("QUATRE", {}).get("source", "").endswith("::CmndQuatre"), True, "#else : pointeurs de la 1re branche")
        verifie(d["anomalies"], [], "faux depot : aucune anomalie d'alignement")
        verifie(r.get("OPTION", {}).get("quand"), "toujours", "restart_flag = 210 + payload (Reset) -> toujours")
        verifie("ESCODE" in r or "SYNONYME" in r, False, "restart_flag = 0, synonyme sans SetOption : absents")
        avec_doc = ac.genere(Path(t), doc=DOC)
        verifie(sorted(avec_doc["doc"]), ["HOSTNAME", "SYNONYME", "UN", "VALEUR"], "doc : mentions restart/reboot relevees")
        verifie(avec_doc["redemarrent"].get("SYNONYME"), {"quand": "toujours", "source": "doc Commands.md seulement"},
                "doc seule (« and restart ») -> toujours, source doc seulement")
        verifie("UN" in avec_doc["redemarrent"], False, "doc « after restart » : pas un redemarrage")
        verifie("doc" in avec_doc["redemarrent"]["HOSTNAME"]["source"], True, "doc croisee : source gardee")
        verifie(avec_doc["redemarrent"]["VALEUR"]["quand"], "si-change", "doc croisee : classement du code garde")
        fige = Path(t) / "fige.json"
        fige.write_text(json.dumps(avec_doc), encoding="utf-8")
        verifie(ac.verifie(Path(t), fige=fige), [], "faux depot : fige conforme -> aucun ecart")
        (Path(t) / "tasmota" / "xdrv_99_essai.ino").write_text(INO.replace("void CmndLocal(void) { Tas", "void CmndLocal(void) { //"), encoding="utf-8")
        verifie(len(ac.verifie(Path(t), fige=fige)), 1, "code change (restart retire) -> 1 ecart")


def reel():
    d = ac.charge(RACINE)
    c, r = d["connues"], d["redemarrent"]
    for nom in ("HOSTNAME", "TIMER", "ADCPARAM", "WEBSENSOR", "SETOPTION146", "REGLAGELOG", "IPADDRESS"):
        verifie(nom in c, True, f"connue : {nom}")
    verifie("data/fs" in c.get("REGLAGELOG", ""), True, "REGLAGELOG vient de data/fs")
    verifie(r.get("HOSTNAME", {}).get("quand"), "toujours", "HOSTNAME redemarre toujours (cas vecu)")
    verifie("TELEPERIOD" in r, False, "TELEPERIOD absente de redemarrent")
    for nom in ("RESET", "UPGRADE", "UPLOAD"):
        verifie(r.get(nom, {}).get("quand"), "toujours", f"{nom} redemarre toujours")
    verifie("BRRESTART" in r, False, "BRRESTART absente (relance Berry, pas la carte)")
    verifie(r.get("WIFITEST", {}).get("quand"), "si-change", "WIFITEST : une fois, en gestionnaire Wi-Fi seulement")
    for nom in ("SETOPTION55", "SETOPTION115"):
        verifie("seulement si la valeur est 0" in r.get(nom, {}).get("source", ""), True, f"{nom} : condition dans la source")
    g = d.get("gardes", {})
    verifie(bool(g.get("ZBSEND")) and all("defined(USE_ZIGBEE)" in ch for ch in g["ZBSEND"]), True, "ZBSEND gardee par USE_ZIGBEE")
    verifie(bool(g.get("I2CSCAN")) and all("defined(USE_I2C)" in ch for ch in g["I2CSCAN"]), True, "I2CSCAN gardee par USE_I2C (dans la table)")
    for nom in ("HOSTNAME", "RESTART", "UPGRADE", "SETOPTION146", "REGLAGELOG"):
        verifie(nom in g, False, f"{nom} sans garde")
    verifie([n for n, v in g.items() if not v or [] in v], [], "aucune garde vide (A4 alerterait a coup sur)")
    for nom in ("SUBSCRIBE", "UNSUBSCRIBE"):                   # aussi dans kScriptCommands, lue par GetCommandCode (xdrv_10_scripter.ino)
        verifie(nom not in g or any("defined(USE_SCRIPT)" in ch for ch in g[nom]), True, f"{nom} : chemin par USE_SCRIPT, ou pas de cle")
    for macro in ("USE_MQTT_FILE", "USE_I2S_MP3", "USE_TIMEPROP"):   # le preprocesseur de A4 les croirait absentes : FileUpload, I2SPlay en fausse alerte
        verifie(any(macro in x for v in g.values() for ch in v for x in ch), False, f"aucune condition sur {macro} (posee par un .ino)")
    verifie(set(g) <= set(c), True, "gardes : que des commandes connues")
    verifie(ac.verifie(RACINE), [], "fige conforme au code du fork")
    brut = json.loads((RACINE / ac.FIGE).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as t:
        ampute = Path(t) / "fige.json"
        del brut["connues"]["TIMER"]
        ampute.write_text(json.dumps(brut), encoding="utf-8")
        verifie(len(ac.verifie(RACINE, fige=ampute)), 1, "temoin : fige ampute d'une commande -> 1 ecart")
        brut["connues"]["TIMER"] = "x"
        brut["redemarrent"]["HOSTNAME"]["quand"] = "si-change"
        ampute.write_text(json.dumps(brut), encoding="utf-8")
        verifie(len(ac.verifie(RACINE, fige=ampute)), 2, "temoin : fige faux (source, classement) -> 2 ecarts")
        brut["connues"]["TIMER"] = c["TIMER"]
        brut["redemarrent"]["HOSTNAME"]["quand"] = "toujours"
        brut.get("gardes", {}).pop("ZBSEND", None)
        ampute.write_text(json.dumps(brut), encoding="utf-8")
        verifie(len(ac.verifie(RACINE, fige=ampute)), 1, "temoin : --verifier voit une garde retiree -> 1 ecart")


MUTANTS = {   # regle de protection -> (texte du module, mutation, resultat faux attendu sur le faux depot)
    "classement : comparaison ignoree": ("if not any(COMPARE.search(c) for c in conds):", "if True:",
                                         lambda d: d["redemarrent"]["VALEUR"]["quand"] == "toujours"),
    "detection : restart_flag = 2 seul": (r'REDEMARRE = r"restart_flag\s*=\s*[1-9][^;]*;"',
                                          r'REDEMARRE = r"restart_flag\s*=\s*2\s*;"',
                                          lambda d: "OPTION" not in d["redemarrent"]),
    "alignement : toutes les branches": ('lignes.append("" if d or not all(pile) else ligne)',
                                         'lignes.append("" if d else ligne)', lambda d: bool(d["anomalies"])),
    "doc seule ignoree": ("elif nom in connues and nom not in EXCLUES", "elif False",
                          lambda d: "SYNONYME" not in d["redemarrent"]),
    "verifie muet": ("    return ecarts\n", "    return []\n", ("connues", "UN")),
    "gardes : #else non inverse": ('prec.append(f"!({cour})")', "prec.append(cour)",
                                   lambda d: d["gardes"]["TROIS"] == [["defined(USE_RIEN)"]]),
    "gardes : garde de ligne ignoree": ("piles_nom.pop() if len(piles_nom) == 1 else table", "table", lambda d: "TOPIC" not in d["gardes"]),
    "gardes : chemins d'une table non reunis": ("res.setdefault(nom, set()).add(chemin)", "res[nom] = {chemin}",
                                                lambda d: len(d["gardes"]["DOUBLE"]) == 1),
    "gardes : chemins de deux tables non reunis": ("globales)).items():\n                chemins.setdefault(nom, set()).update(ch)", "globales)).items():\n                chemins[nom] = ch",
                                                   lambda d: "DEUXFOIS" in d["gardes"] and len(d["gardes"]["PARTAGEE"]) == 1),
    "gardes : macro d'un .ino gardee": ('if not locales & set(re.findall(r"\\w+", c))', "", lambda d: "LOCALE" in d["gardes"]),
    "gardes : firmware minimal garde": ('locales |= {"FIRMWARE_MINIMAL", "FIRMWARE_SAFEBOOT"}', "pass", lambda d: "HORSMINIMAL" in d["gardes"]),
    "gardes : table de GetCommandCode ignoree": (r'r"\bGetCommandCode\(', r'r"\bGetCommandCodeX\(', lambda d: d["gardes"].get("ABONNE") == [["defined(USE_RG)"]]),
    "gardes : table illisible sans chemin": ("chemins.setdefault(nom, set()).add(())", "pass", lambda d: "FRAGA" in d["gardes"] and "SINONSEUL" in d["gardes"]),
    "gardes : #elifdef ignore": (' or mot in ("elifdef", "elifndef")', "", lambda d: d["gardes"].get("EFDEUX") == [["defined(USE_F1)"]]),
    "gardes : presence libre oubliee": (" and () not in ch", "", lambda d: "DEUXFOIS" in d["gardes"]),
    "gardes : garde d'inclusion gardee": ("pile[-1][1] = None", "pass", lambda d: "INCLUSE" in d["gardes"]),
    "gardes : emplacement illisible ignore": ("res[n].add(table)", "pass", lambda d: d["gardes"]["SEULSI"] == [["defined(USE_M)"]]),
    "gardes : homonyme Berry garde": (" and n not in berry", "", lambda d: "ENBERRY" in d["gardes"]),
    "gardes : SetOption gardee": (' and not re.fullmatch(r"SETOPTION\\d*", n)', "", lambda d: "SETOPTION77" in d["gardes"]),
    "gardes : #if non ferme lu quand meme": ("return res if equilibre and not pile else [()] * len(res)", "return res", lambda d: "DESEQUILIBRE" in d["gardes"]),
    "gardes : verifie ne les compare pas": ('for cle in ("connues", "redemarrent", "gardes"):', 'for cle in ("connues", "redemarrent"):',
                                            ("gardes", "TOPIC")),
}


def temoins():
    """Chaque regle a son mutant : copie du module modifiee, chargee a part ; son resultat doit etre faux."""
    source = Path(ac.__file__).read_text(encoding="utf-8")
    for libelle, (texte, mutation, faux) in MUTANTS.items():
        with tempfile.TemporaryDirectory() as t:
            verifie(texte in source, True, f"temoin {libelle} : texte a muter present")
            copie = Path(t) / "autoexec_mutant.py"
            copie.write_text(source.replace(texte, mutation, 1), encoding="utf-8")
            spec = importlib.util.spec_from_file_location("autoexec_mutant", copie)
            mutant = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mutant)
            depot = fichiers_gardes(faux_depot(Path(t) / "depot"))
            d = mutant.genere(depot, doc=DOC)
            if isinstance(faux, tuple):               # verifie : un fige ampute doit donner un ecart
                del d[faux[0]][faux[1]]
                (Path(t) / "fige.json").write_text(json.dumps(d), encoding="utf-8")
                faux = lambda d: mutant.verifie(depot, fige=Path(t) / "fige.json") == []
            verifie(faux(d), True, f"temoin {libelle} : le mutant donne un resultat faux")


if __name__ == "__main__":
    regles()
    regles_gardes()
    temoins()
    reel()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1 if ECHECS else 0)

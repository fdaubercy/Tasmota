#!/usr/bin/env python3
"""Banc de autoexec_commandes.py : commandes connues et commandes qui redemarrent (plan autoexec-bat, A1).

Sans reseau : le fige est compare au code C du fork et aux .be de data/fs ; la doc n'est jamais telechargee.
Faux depot en dossier temporaire pour les regles de lecture (macros, prefixe, #ifdef, synonymes, classement).
Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_autoexec_commandes.py
"""
import json
import sys
import tempfile
from pathlib import Path

import autoexec_commandes as ac

RACINE = Path(__file__).resolve().parents[3]
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
void CmndOption(void) { TasmotaGlobal.restart_flag = 211; }
void CmndCode(void) { }
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
       "Valeur<x\\><a class=\"cmnd\" id=\"valeur\"></a>|Set value. Causes a reboot\n")


def faux_depot(dossier):
    (dossier / "tasmota" / "include").mkdir(parents=True)
    (dossier / "tasmota" / "include" / "i18n.h").write_text(I18N, encoding="utf-8")
    (dossier / "tasmota" / "xdrv_99_essai.ino").write_text(INO, encoding="utf-8")
    (dossier / "data" / "fs").mkdir(parents=True)
    (dossier / "data" / "fs" / "essai.be").write_text(BE, encoding="utf-8")
    return dossier


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
        verifie("OPTION" in r or "ESCODE" in r or "SYNONYME" in r, False, "restart_flag = 211, corps vide, synonyme : absents")
        avec_doc = ac.genere(Path(t), doc=DOC)
        verifie(sorted(avec_doc["doc"]), ["HOSTNAME", "VALEUR"], "doc : mentions restart/reboot relevees")
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


if __name__ == "__main__":
    regles()
    reel()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1 if ECHECS else 0)

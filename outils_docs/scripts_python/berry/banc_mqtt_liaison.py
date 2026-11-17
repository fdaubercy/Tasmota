"""Banc des garde-fous de la voie MQTT (data/fs/mqttLiaisonFonctions.be, plan tasks/plans/voie-mqtt.md A3).

UTILISATION
    python outils_docs/scripts_python/berry/banc_mqtt_liaison.py [--sans-mutants]
Depuis n'importe quel dossier. Code de sortie 0 = vert : le vrai module passe banc_mqtt_liaison.be ET chaque mutant
(copie du module avec un garde-fou retire) le fait echouer ; sans ces temoins, un vert ne prouverait rien.
Ne teste pas le vrai MQTT : le module est pur (bouchons : bouchons_berry/liaison_mqtt/).
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from banc_coprocesseur import trouve_berry, trouve_racine  # noqa: E402  (meme dossier : module voisin)

# (nom, texte du module, remplacement) : chaque mutant retire un garde-fou que le banc doit voir.
# Les mutants du driver (controleMqttLiaison.be) sont dans MUTANTS_DRIVER, meme forme.
MUTANTS = [
    ("limiteur par element retire (G4)", "if size(self.emis[cle]) >= self.max_element", "if false"),
    ("coupe-circuit global retire (G5)", "if size(self.totaux) >= self.max_total", "if false"),
    ("ordre identique a l'etat connu envoye (G3)", "if a == nil && self.etats.find(cle) == valeur", "if false"),
    ("accuse jamais reconnu (retour = evenement)", "if valeur == a[\"valeur\"]", "if false"),
    ("renvois sans limite", "if a[\"essais\"] >= self.essais_max", "if false"),
    ("ancien etat repete pris pour un evenement", "if ancien == valeur    return \"inchange\"    end              # ancien",
     "if false    return \"inchange\"    end              # ancien"),
    ("doublon d'ordre en attente renvoye", "if a != nil && a[\"valeur\"] == valeur    return \"attente\"    end", ""),
    ("quarantaine jamais levee", "if fin - t > 0    return \"quarantaine\"    end", "if true    return \"quarantaine\"    end"),
    ("coupe-circuit jamais referme", "if t - self.coupe_jusqua >= 0", "if false"),
    ("renvoi bloque : echec sans abandon de l'ordre", "elif self.bloque(cle, t) != nil", "elif false"),
    ("cle ou valeur invalide acceptee", "if type(cle) == \"string\" && size(cle) > 0 && valeur != nil    return true    end", "return true"),
    ("valeur non convertie en texte (demande)", "        valeur = str(valeur)                       # 1 et", "        # 1 et"),
    ("1er retour sans etat connu pris pour un evenement", "if !connu    return \"initial\"    end                         # 1er", "# 1er"),
    ("plafond de renvois par appel retire", "elif maxi != nil && size(renvoyer) >= maxi", "elif false"),
    ("etat connu jamais perime (G3)", "&& t - self.etats_t.find(cle, t - self.age_etat - 1) <= self.age_etat", ""),
    ("age de l'etat non rafraichi par le retour", "self.etats_t[cle] = t", "self.etats_t[cle] = 0"),
]
MUTANTS_DRIVER = [
    ("ordre publie sans accord des garde-fous", "if code == \"envoyer\"", "if true"),
    ("reseau ou broker non verifie avant un ordre", "self.en_ligne.find(nom) == false || !self.peut_emettre()", "self.en_ligne.find(nom) == false"),
    ("esclave Offline (LWT) pas refuse", "self.en_ligne.find(nom) == false || !self.peut_emettre()", "!self.peut_emettre()"),
    ("garde d'activation retiree", "find(\"activation\", \"OFF\") == \"ON\"", "find(\"activation\", \"OFF\") != \"JAMAIS\""),
    ("esclave inactif pris en compte", "if e.find(\"activation\", \"OFF\") != \"ON\"    continue    end", "if false    continue    end"),
    ("retour d'un esclave non declare accepte", "if nom == nil    return false    end", "if false    return false    end"),
    ("liste blanche des commandes retiree", "if !self.COMMANDES.contains(base)    return nil    end", "if false    return nil    end"),
    ("Power0 accepte", "if indice == \"0\"    return nil    end", "if false    return nil    end"),
    ("TOGGLE pris pour ON", "|| v == \"true\"        v = \"ON\"", "|| v == \"true\" || v == \"toggle\"        v = \"ON\""),
    ("Dimmer mal forme accepte", "if indice != \"\" || !self.chiffres(v)    return nil    end", "if false    return nil    end"),
    ("Power sans indice non range sous POWER1", "if indice == \"\"    c = \"POWER1\"    end", "if false    c = \"POWER1\"    end"),
    ("retour POWER non range sous POWER1", "if e == \"POWER\"    e = \"POWER1\"    end", "if false    e = \"POWER1\"    end"),
    ("plafond de renvois par passage porte a 500", "static RENVOIS_PAR_PASSAGE = 5 ", "static RENVOIS_PAR_PASSAGE = 500 "),
    ("nom d'esclave avec slash accepte", "|| string.find(nom, \"/\") >= 0", "|| false"),
    ("topic en double accepte", "elif self.par_topic.contains(topic)", "elif false"),
    ("topic avec joker accepte", "string.find(topic, \"+\") >= 0 || string.find(topic, \"#\") >= 0", "false"),
    ("renvoi jamais publie", "if topic != nil    mqtt.publish(\"cmnd/\" + topic + \"/\" + e[0]", "if false    mqtt.publish(\"cmnd/\" + topic + \"/\" + e[0]"),
    ("valeur nulle transmise aux garde-fous", "if v != nil && type(v) != \"instance\"", "if type(v) != \"instance\""),
    ("SENSOR jamais traite", "elif suffixe == \"SENSOR\"", "elif false"),
    ("message d'erreur SENSOR mal forme perdu", "SENSOR de \" + nom + \" mal formé", "SENSOR de \" + nom + \" ok"),
    ("element d'un esclave non declare alimente", "if !self.esclaves.contains(nom)    continue    end", "if false    continue    end"),
    ("declencheur sans # (famille non reconnue)", "string.replace(chemin, \".\", \"#\")", "chemin"),
    ("evenement de bouton jamais traite", "elif isinstance(v, map)                 self.evenement(nom, k, v)", "elif false                 self.evenement(nom, k, v)"),
    ("action non texte acceptee", "if type(action) != \"string\"    return    end", "if false    return    end"),
    ("evenement livre a un element qui n'est pas un bouton", "if e[3] != cle || (e[1] != \"boutons\" && e[1] != \"capteurs\" && e[1] != \"interrupteurs\")    continue    end", "if e[3] != cle    continue    end"),
    ("declencheur impose ignore", "type(decl) == \"string\" ? decl :", "false ? decl :"),
    ("LWT ignore", "self.en_ligne[nom] = (s == \"Online\")", "self.en_ligne[nom] = true"),
]


def lance(berry, racine, sources):
    r = subprocess.run([str(berry), str(Path(__file__).with_suffix(".be")), str(sources)], cwd=str(racine),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser(description="Banc de data/fs/mqttLiaisonFonctions.be")
    ap.add_argument("--sans-mutants", action="store_true")
    args = ap.parse_args()
    racine = trouve_racine()
    berry = trouve_berry(racine)
    sortie = lance(berry, racine, "data/fs")
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    vert = "BANC_MQTT_LIAISON: OK" in sortie
    if not args.sans_mutants:
        fichiers = {nom: (racine / "data" / "fs" / nom).read_text(encoding="utf-8")
                    for nom in ("mqttLiaisonFonctions.be", "controleMqttLiaison.be")}
        for fichier, mutants in (("mqttLiaisonFonctions.be", MUTANTS), ("controleMqttLiaison.be", MUTANTS_DRIVER)):
          for nom, avant, apres in mutants:
            source = fichiers[fichier]
            if source.count(avant) != 1:
                print(f"KO   mutant '{nom}' : texte a muter introuvable ({fichier} modifie ?)")
                vert = False
                continue
            with tempfile.TemporaryDirectory() as tmp:
                for autre, texte in fichiers.items():          # les DEUX modules, dont un seul est mute
                    (Path(tmp) / autre).write_text(source.replace(avant, apres) if autre == fichier else texte, encoding="utf-8")
                rouge = "BANC_MQTT_LIAISON: OK" not in lance(berry, racine, Path(tmp).as_posix())   # ECHEC ou plantage
            print(("OK   " if rouge else "KO   ") + f"mutant '{nom}' : banc rouge")
            vert = vert and rouge
    print("\n" + ("VERT" if vert else "ROUGE"))
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())

"""Sonde Chrome de l'onglet « Sauvegarde configuration » de la page Build et televersement (build_page_sauvegarde.py).

UTILISATION (a la main ; Python de PlatformIO ; decode-config installe par decode_config.py)
    python outils_docs/scripts_python/outils_pc/test_build_page_sauvegarde_chrome.py [--capture DOSSIER]
Code de sortie 0 = vert. Lent : chaque lecture de sauvegarde lance decode-config.

Montage de test_build_page_chrome.py (vrai build_web.py dans un processus fils, depot d'essai TEMPORAIRE) + deux
sauvegardes fabriquees (test_build_sauvegarde.dmp, aucun vrai mot de passe). Aucune carte n'est jointe.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import build_sauvegarde as bs
import test_build_page_chrome as s
from test_build_sauvegarde import dmp

A = s.A
ETAT = """(() => { const t = id => document.getElementById(id);
  return {vue: t('vue-sauvegarde').hidden, build: t('vue-build').hidden, env: t('s-env').value,
          lignes: [...document.querySelectorAll('#s-liste tr.l')].map(l => l.children[3].textContent),
          choisie: document.querySelectorAll('#s-liste tr.choisie').length,
          themes: [...document.querySelectorAll('#s-params .s-theme')].map(d => [d.querySelector('summary').firstChild.textContent, d.open]),
          params: [...document.querySelectorAll('#s-params .s-p')].map(p => p.querySelector('code').textContent),
          modifs: [...document.querySelectorAll('#s-params .s-p.modif code')].map(c => c.textContent),
          ecarts: [...document.querySelectorAll('#s-params .s-p.ecart code')].map(c => c.textContent),
          copier: t('s-copier').hidden ? '' : t('s-copier').textContent, texte_ecarts: t('s-ecarts').textContent,
          messages: t('s-messages').textContent, fichiers: t('s-params').textContent.includes('/.drvset003 (536 o)'),
          secret: document.body.textContent.includes('secret')}; })()"""


def clic(cdp, selecteur):
    return cdp.js(f"(() => {{ const e = document.querySelector({json.dumps(selecteur)}); if (!e) return 'absent'; e.click(); return true; }})()")


def saisit(cdp, selecteur, valeur):
    return cdp.js(f"""(() => {{ const e = document.querySelector({json.dumps(selecteur)}); if (!e) return 'absent';
      e.value = {json.dumps(valeur)}; e.dispatchEvent(new Event('input')); e.dispatchEvent(new Event('change')); return true; }})()""")


def etat(cdp):
    time.sleep(0.3)
    return cdp.js(ETAT)


def sonde(m, capture):
    cdp = m.cdp
    dossier = bs.dossier(m.depot, A)
    dossier.mkdir(parents=True)
    for nom, donnees, origine in (("20261101-100000_manuelle.dmp", dmp(), "manuelle"),
                                  ("20261102-100000_avant-flash.dmp", dmp(textes={8: "CARTE-AVANT-FLASH"}), "avant-flash")):
        (dossier / nom).write_bytes(donnees)
        bs._fiche(dossier / nom, donnees, origine, "192.168.0.99")
    m.ouvre()
    clic(cdp, "#onglet-sauvegarde")
    saisit(cdp, "#s-env", A)
    s.attend(cdp, "document.querySelectorAll('#s-liste tr.l').length === 2", 10)
    s.attend(cdp, "document.querySelectorAll('#s-params .s-theme').length > 0", 90)
    e = etat(cdp)
    s.verifie((e["vue"], e["build"], e["env"]), (False, True, A), "onglet : vue affichee, Build masque, env choisi")
    s.verifie((e["lignes"], e["choisie"]), (["avant flash", "manuelle"], 1), "historique : plus recente d'abord, choisie")
    s.verifie(cdp.js("document.getElementById('s-restaurer').textContent"), "Restaurer : 02/11/2026 10:00 · avant flash",
              "restaurer : le bouton nomme la sauvegarde choisie")
    cdp.js("[...document.querySelectorAll('#s-liste tr.l')].find(t => t.textContent.includes('manuelle')).click()")
    s.attend(cdp, "document.getElementById('s-restaurer').textContent.includes('manuelle')", 5)
    s.verifie(etat(cdp)["choisie"], 1, "restaurer : clic sur une autre ligne -> elle devient la sauvegarde a restaurer")
    cdp.js("[...document.querySelectorAll('#s-liste tr.l')].find(t => t.textContent.includes('avant flash')).click()")
    s.attend(cdp, "document.getElementById('s-restaurer').textContent.includes('avant flash')", 5)
    s.verifie(any(t[0] == "Réseau et Wi-Fi" for t in e["themes"]) and not any(t[1] for t in e["themes"]), True,
              "parametres : themes en francais, replies")
    s.verifie((e["fichiers"], e["secret"]), (True, False), "parametres : fichier .drvset003 cite, aucun mot de passe en clair")
    s.verifie((cdp.js("document.getElementById('s-liaison').value"), cdp.js("document.querySelectorAll('#s-params .s-demarre').length")),
              ("http", 0), "liaison HTTP par defaut ; env d'essai sans autoexec ni persist : aucune marque de demarrage")

    saisit(cdp, "#s-filtre", "CARTE-AVANT")            # valeur du seul hostname de la plus recente (le filtre cherche aussi les valeurs)
    e = etat(cdp)
    s.verifie((e["params"], [t[1] for t in e["themes"]]), (["hostname"], [True]), "filtre : un parametre, theme ouvert")
    saisit(cdp, "#s-params .s-p textarea[aria-label='hostname']", "CARTE-SONDE")
    e = etat(cdp)
    s.verifie((e["modifs"], e["copier"]), (["hostname"], "Enregistrer la copie (1 modifié)"), "modification : surlignee, bouton de copie")
    clic(cdp, "#s-copier")
    s.attend(cdp, "document.getElementById('s-messages').textContent.includes('Copie enregistrée')", 120)
    s.attend(cdp, "document.querySelectorAll('#s-liste tr.l').length === 3", 10)
    e = etat(cdp)
    s.verifie(e["lignes"][0], "modifiée", "copie : nouvelle sauvegarde en tete de l'historique")
    s.verifie(len(list(dossier.glob("*.dmp"))), 3, "copie : fichier ecrit, originale gardee")

    s.attend(cdp, "document.querySelectorAll('#s-params .s-theme').length > 0", 90)
    saisit(cdp, "#s-filtre", "")
    cdp.js(f"(() => {{ const s = document.getElementById('s-autre'); s.value = [...s.options].find(o => o.textContent.includes('manuelle')).value; }})()")
    clic(cdp, "#s-comparer")
    s.attend(cdp, "document.getElementById('s-ecarts').textContent.includes('écart')", 120)
    e = etat(cdp)
    s.verifie((e["texte_ecarts"], e["ecarts"]), ("1 écart : hostname", ["hostname"]), "comparer : ecart annonce et surligne")

    saisit(cdp, "#s-filtre", "flag3")                      # objet de 30 cles : plus long que sa zone
    champ = "#s-params textarea[aria-label='flag3']"
    haut = lambda: cdp.js(f"document.querySelector({json.dumps(champ)}).offsetHeight")
    h1 = haut()
    s.verifie(h1 > 40, True, f"valeur longue : affichee sur plusieurs lignes ({h1} px)")
    s.verifie(cdp.js("document.querySelectorAll('#s-params .s-json').length"), 1, "valeur JSON : une icone de vue formatee")
    clic(cdp, "#s-params .s-json")
    time.sleep(0.3)
    s.verifie((cdp.js(f"document.querySelector({json.dumps(champ)}).value.includes('\\n  \"')"), haut() > h1,
               cdp.js("document.querySelectorAll('#s-params .s-p.modif').length")), (True, True, 0),
              "icone : vue formatee, plus haute, pas une modification")
    clic(cdp, "#s-params .s-json")
    time.sleep(0.3)
    s.verifie(cdp.js(f"document.querySelector({json.dumps(champ)}).value.includes('\\n')"), False, "icone : retour sur une ligne")
    saisit(cdp, "#s-filtre", "")
    clic(cdp, "#s-restaurer")                              # env sans adresse : rien n'est demande a une carte
    time.sleep(0.5)
    s.verifie("Adresse de la carte inconnue" in etat(cdp)["messages"], True, "restaurer sans adresse : refuse avec le motif")
    # -- suppression : cases de l'historique, confirmation
    s.verifie(cdp.js("document.getElementById('s-supprimer').hidden"), True, "suppression : bouton cache sans case cochee")
    cdp.js("(() => { const l = [...document.querySelectorAll('#s-liste tr.l')].find(t => t.textContent.includes('avant flash')); l.querySelector('input').click(); })()")
    s.verifie((cdp.js("document.getElementById('s-supprimer').textContent"), etat(cdp)["choisie"]),
              ("Supprimer la sélection (1)", 1), "suppression : une case, la ligne choisie ne change pas")
    cdp.js("window.confirm = () => true")
    clic(cdp, "#s-supprimer")
    s.attend(cdp, "document.getElementById('s-messages').textContent.includes('supprimée')", 20)
    s.attend(cdp, "document.querySelectorAll('#s-liste tr.l').length === 2", 10)
    s.verifie((sorted(p.name for p in dossier.iterdir()), "avant flash" in etat(cdp)["lignes"]),
              (sorted(n for f in dossier.glob("*.dmp") for n in (f.name, f.with_suffix(".json").name)), False),
              "suppression : .dmp et fiche effaces, liste relue")
    s.verifie(any("avant-flash" in p.name for p in dossier.iterdir()), False, "suppression : plus de fichier « avant flash »")
    if capture:
        cdp.capture(Path(capture) / "build-sauvegarde.png")
    m.ouvre()
    s.attend(cdp, "!document.getElementById('vue-sauvegarde').hidden", 10)
    s.verifie(True, True, "rechargement : l'onglet est rouvert")
    s.verifie(cdp.erreurs(), [], "aucune erreur JS")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de l'onglet Sauvegarde configuration de la page build.")
    options.add_argument("--capture", help="dossier ou ecrire les captures PNG")
    args = options.parse_args()
    m = None
    try:
        m = s.Montage()
        m.demarre(False)
        sonde(m, args.capture)
    except FileNotFoundError as erreur:
        print(f"BLOQUE : {erreur}")
        return 3
    except Exception as erreur:                              # noqa: BLE001
        s.verifie(repr(erreur), "pas d'exception de la sonde", "sonde : deroulement")
    finally:
        if m:
            m.ferme()
    print("\n" + ("VERT" if not s.ECHECS else f"ROUGE : {len(s.ECHECS)} echec(s) : {s.ECHECS}"))
    return 1 if s.ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())

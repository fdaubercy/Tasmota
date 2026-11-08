r"""Essai de charge de la carte Serveur Debits de PAC (plan debitmetres-chauffage, A6) : un second ESP32 envoie des
impulsions sur les 6 entrees, ce script compte ce que la carte a recu et juge chaque palier.

    python essai_charge_debits.py --generateur 192.168.0.60 --carte 192.168.0.50 [--duree 120] [--paliers 11,55,275,1000,2000]
    python essai_charge_debits.py --test        (verifie le jugement, sans reseau)

MONTAGE (a faire avant, cartes hors tension)
  Generateur : n'importe quel ESP32 sous Tasmota standard (pas le framework du depot). Modele : 6 GPIO en PWM1 a PWM6,
  puis dans sa console : `SetOption15 0` (PWM pilotees par Pwm<n>, pas par la lumiere) et `PwmRange 1023`.
  Cablage : PWM1 -> GPIO4 (voie 1), PWM2 -> GPIO5 (voie 2), PWM3 -> GPIO6, PWM4 -> GPIO7, PWM5 -> GPIO15, PWM6 -> GPIO16
  de la carte testee, MASSES RELIEES, debitmetres debranches. Les deux cartes en 3,3 V : aucun pont diviseur.

CE QUE FAIT LE SCRIPT, par palier de frequence f (Hz)
  1. Generateur : `PwmFrequency f` (toutes les sorties, support_pwm.ino::CmndPwmfrequency, 2 a 50 000 Hz sur ESP32),
     puis Pwm1..6 a 512 (rapport cyclique 50 %).
  2. Attente de 2 fenetres de mesure (stabilisation), puis `Status 10` de la carte : compteurs C1-C4 (voies 3-6).
  3. Attente de --duree s, nouveau `Status 10` : impulsions comptees contre f x duree reelle (horloge du PC entre les
     deux lectures) ; voies 1-2 : Rate du FlowRateMeter x 0,12 = frequence vue (debitsFonctions.HZ_PAR_RATE).
  4. `ReglageDebits` : duree de la derniere ecriture de l'ecran (ecran_ms), a comparer au palier sans impulsion.
  Verdict d'une voie : ecart < 0,5 % (critere du plan). Le premier palier (0 Hz, sorties a 0) donne la reference de l'ecran.
  A la fin, les sorties du generateur sont remises a 0, meme sur Ctrl+C.

Lecture seule cote carte testee (Status 10, ReglageDebits sans argument) ; seul le generateur recoit des ordres.
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

ECART_MAX = 0.005           # 0,5 % : critere de l'etape A6 du plan
HZ_PAR_RATE = 0.12          # Rate du FlowRateMeter a calibrage 1000 = f / 0,12 (debitsFonctions.be)
CLES_FLOWRATE = ("Débit", "Flowrate")
FENETRE_S = 10              # fenetre de mesure par defaut de la carte (stabilisation = 2 fenetres)


def commande(ip, cmd, delai=10):
    """Commande Tasmota par HTTP, reponse JSON (dict)."""
    url = f"http://{ip}/cm?cmnd={urllib.parse.quote(cmd)}"
    req = urllib.request.Request(url, headers={"Referer": f"http://{ip}/"})
    with urllib.request.urlopen(req, timeout=delai) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def releve(ip):
    """(compteurs C1-C4 ou None, Rate des 2 FlowRateMeter ou None, instant PC) d'apres Status 10."""
    t = time.monotonic()
    s = commande(ip, "Status 10").get("StatusSNS", {})
    c = s.get("COUNTER", {})
    compteurs = [c.get(f"C{i}") for i in range(1, 5)]
    rates = None
    for cle in CLES_FLOWRATE:
        if isinstance(s.get(cle), dict):
            r = s[cle].get("Rate")
            rates = r if isinstance(r, list) else [r]
    return compteurs, rates, t


def juge(f, avant, apres, rates):
    """Verdicts des 6 voies pour un palier a f Hz : [(voie, frequence vue, ecart relatif ou None, ok)].
    avant, apres : (compteurs, instant) ; rates : Rate du FlowRateMeter (voies 1-2)."""
    res = []
    for i in range(2):
        r = rates[i] if rates and i < len(rates) and rates[i] is not None else None
        vue = r * HZ_PAR_RATE if r is not None else None
        res.append((i + 1, vue))
    duree = apres[1] - avant[1]
    for i in range(4):
        a, b = avant[0][i], apres[0][i]
        vue = (b - a) / duree if a is not None and b is not None and b >= a and duree > 0 else None
        res.append((i + 3, vue))
    out = []
    for voie, vue in res:
        if f == 0:
            out.append((voie, vue, None, vue is not None and vue == 0))
        elif vue is None:
            out.append((voie, None, None, False))
        else:
            e = (vue - f) / f
            out.append((voie, vue, e, abs(e) < ECART_MAX))
    return out


def regle_generateur(ip, f):
    """f = 0 : sorties a 0 ; sinon frequence f et rapport cyclique 50 % sur les 6 sorties."""
    if f > 0:
        commande(ip, f"PwmFrequency {f}")
    commande(ip, "Backlog " + "; ".join(f"Pwm{n} {512 if f > 0 else 0}" for n in range(1, 7)))


def essai(gen, carte, paliers, duree):
    lignes = []
    try:
        for f in [0] + paliers:
            regle_generateur(gen, f)
            print(f"--- palier {f} Hz : stabilisation {2 * FENETRE_S} s, puis {duree} s de comptage")
            time.sleep(2 * FENETRE_S)
            c0, _, t0 = releve(carte)
            time.sleep(duree)
            c1, rates, t1 = releve(carte)
            ecran = commande(carte, "ReglageDebits").get("ReglageDebits", {}).get("ecran_ms")
            for voie, vue, e, ok in juge(f, (c0, t0), (c1, t1), rates):
                txt = "-" if vue is None else f"{vue:.2f} Hz"
                ecart = "" if e is None else f" ecart {e * 100:+.2f} %"
                print(f"  voie {voie} : {txt}{ecart}  {'OK' if ok else 'ECHEC'}")
                lignes.append((f, voie, ok))
            print(f"  ecran : derniere ecriture {ecran} ms")
    finally:
        regle_generateur(gen, 0)
        print("generateur remis a 0")
    echecs = [(f, v) for f, v, ok in lignes if not ok]
    print("ESSAI_CHARGE:", "VERT" if not echecs else f"ROUGE {echecs}")
    return 0 if not echecs else 1


def test():
    """Jugement contre des releves construits a la main (pas de reseau)."""
    ok = True
    def verifie(nom, cond):
        nonlocal ok
        print(("  OK    " if cond else "  ECHEC ") + nom)
        ok = ok and cond
    v = juge(275, ([0, 100, 0, 0], 0.0), ([33000, 33100, 32700, 0], 120.0), [2291.67, None])
    verifie("voie 1 : Rate 2291,67 = 275 Hz, OK", v[0][3] and abs(v[0][1] - 275) < 0.01)
    verifie("voie 2 : FlowRateMeter absent -> ECHEC", not v[1][3] and v[1][1] is None)
    verifie("voie 3 : 33000 impulsions en 120 s = 275 Hz, OK", v[2][3])
    verifie("voie 5 : 32700 en 120 s = -0,91 %, ECHEC", not v[4][3] and abs(v[4][2] + 0.00909) < 1e-4)
    verifie("voie 6 : aucune impulsion a 275 Hz -> ECHEC", not v[5][3])
    z = juge(0, ([5, 5, 5, 5], 0.0), ([5, 5, 5, 6], 60.0), [0, 0])
    verifie("palier 0 Hz : voies muettes OK, impulsion parasite voie 6 -> ECHEC", all(x[3] for x in z[:5]) and not z[5][3])
    r = juge(11, ([4000000000, 0, 0, 0], 0.0), ([10, 0, 0, 0], 60.0), None)
    verifie("compteur repasse a zero : voie 3 sans verdict -> ECHEC", r[2][1] is None and not r[2][3])
    print("TEST_ESSAI_CHARGE:", "VERT" if ok else "ROUGE")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="Essai de charge de la carte Serveur Debits de PAC (voir l'en-tete).")
    ap.add_argument("--generateur", help="IP de l'ESP32 generateur (Tasmota standard, PWM1-6)")
    ap.add_argument("--carte", help="IP de la carte testee (192.168.0.50)")
    ap.add_argument("--duree", type=int, default=120, help="duree de comptage par palier, s (defaut 120)")
    ap.add_argument("--paliers", default="11,55,275,1000,2000", help="frequences en Hz, separees par des virgules")
    ap.add_argument("--test", action="store_true", help="verifie le jugement sans reseau")
    a = ap.parse_args()
    if a.test:
        return test()
    if not a.generateur or not a.carte:
        ap.error("--generateur et --carte sont obligatoires (ou --test)")
    paliers = [int(x) for x in a.paliers.split(",") if x.strip()]
    if any(not 2 <= f <= 50000 for f in paliers):
        ap.error("paliers : 2 a 50 000 Hz (PwmFrequency sur ESP32)")
    return essai(a.generateur, a.carte, paliers, a.duree)


if __name__ == "__main__":
    sys.exit(main())

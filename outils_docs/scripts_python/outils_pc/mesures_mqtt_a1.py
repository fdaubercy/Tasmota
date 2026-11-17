"""Mesures preparatoires de la voie MQTT (plan tasks/plans/voie-mqtt.md, action A1).

LECTURE SEULE sur les cartes : seules des commandes d'interrogation sont envoyees (Status, SetOption73,
SetOption114, MqttRetry, MqttTimeout). Aucun ordre de relais, aucune ecriture de persist.
Broker lu dans tasmota/user_config_override.h (comme le sniffeur MQTT) ; le mot de passe n'est jamais affiche.

Sous-commandes :
    rtt   --topic jardin/cuve --n 20          aller-retour d'une commande (Status 10) : min / mediane / max / pertes
    tas   --topic jardin/cuve --duree 3600    tas libre (Status 4) toutes les --pas s, pente en Ko/h, CSV
    so    --topic jardin/projecteur_led       SetOption73, SetOption114, MqttRetry, MqttTimeout de la carte
    veille --url http://IP:PORT               broker coupe A LA MAIN : interroge la carte en HTTP (Status 11),
                                              signale latence > 1 s et redemarrage (uptime qui diminue)
    --autotest                                controle des calculs (aucun reseau)

Pas d'ecriture dans le depot : les CSV vont dans %LOCALAPPDATA%\\outils_tasmota\\mesures_mqtt\\.
Ne pas lancer pendant un build n'est pas necessaire (aucun pio), mais ne pas couper le broker sans prevenir.
"""

import argparse
import json
import os
import statistics
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client_mqtt import ClientMQTT                      # noqa: E402
from sniffeur_mqtt import lit_config_broker             # noqa: E402

DOSSIER = os.path.join(os.environ.get("LOCALAPPDATA", "."), "outils_tasmota", "mesures_mqtt")


def resume(durees, envoyes):
    """min / mediane / max (secondes) et nombre de pertes."""
    if not durees:
        return {"n": envoyes, "recus": 0, "pertes": envoyes}
    return {"n": envoyes, "recus": len(durees), "pertes": envoyes - len(durees), "min": min(durees),
            "mediane": statistics.median(durees), "max": max(durees)}


def pente_par_heure(points):
    """Regression lineaire (t en s, valeur en Ko) -> variation en Ko par heure. None si < 2 points."""
    if len(points) < 2:
        return None
    t0 = points[0][0]
    xs, ys = [p[0] - t0 for p in points], [p[1] for p in points]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    return None if den == 0 else 3600 * sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def connecte(args):
    config = lit_config_broker()
    hote = args.hote or config.get("MQTT_HOST")
    if not hote:
        sys.exit("broker introuvable : passer --hote (MQTT_HOST absent de user_config_override.h)")
    client = ClientMQTT(hote, args.port or config.get("MQTT_PORT", 1883), "mesures-a1-%d" % os.getpid(),
                        config.get("MQTT_USER", ""), config.get("MQTT_PASS", ""))
    client.connecte()
    return client


def interroge(client, topic, commande, charge="", delai=5.0):
    """Publie cmnd/<topic>/<commande> et rend (JSON de la reponse, duree en s), ou (None, None) sans reponse.
    Le topic de reponse est stat/<topic>/RESULT ou stat/<topic>/STATUS<n> selon la commande."""
    debut = time.time()
    client.publie("cmnd/%s/%s" % (topic, commande), charge)
    while time.time() - debut < delai:
        client.entretient()
        message = client.recoit()
        if message is None or not message.topic.startswith("stat/%s/" % topic):
            continue
        try:
            return json.loads(message.payload.decode("utf-8", "replace")), message.instant - debut
        except ValueError:
            continue
    return None, None


def attend(client, secondes):
    """Pause qui garde la liaison en vie (keepalive de 30 s : un sleep de 60 s ferait couper par le broker)."""
    fin = time.time() + secondes
    while time.time() < fin:
        client.entretient()
        client.recoit()


def cmd_rtt(args):
    client = connecte(args)
    client.abonne(["stat/%s/#" % args.topic])
    durees = []
    for i in range(args.n):
        reponse, duree = interroge(client, args.topic, "Status", "10")
        if reponse is not None:
            durees.append(duree)
        print("%2d/%d : %s" % (i + 1, args.n, "%.0f ms" % (duree * 1000) if duree is not None else "PAS DE REPONSE"))
        attend(client, 1.0)
    r = resume(durees, args.n)
    print(json.dumps({k: (round(v * 1000) if k in ("min", "mediane", "max") else v) for k, v in r.items()}),
          "(durees en ms ; critere du plan : max < 1000 ms)")


def cmd_tas(args):
    client = connecte(args)
    client.abonne(["stat/%s/#" % args.topic])
    os.makedirs(DOSSIER, exist_ok=True)
    chemin = os.path.join(DOSSIER, "tas_%s_%d.csv" % (args.topic.replace("/", "_"), time.time()))
    points, fin = [], time.time() + args.duree
    with open(chemin, "w", encoding="utf-8") as f:
        f.write("t;heap_ko;psram_libre_ko\n")
        while time.time() < fin:
            reponse, _ = interroge(client, args.topic, "Status", "4")
            mem = (reponse or {}).get("StatusMEM", {})
            if "Heap" in mem:
                points.append((time.time(), float(mem["Heap"])))
                f.write("%d;%s;%s\n" % (time.time(), mem["Heap"], mem.get("PsrFree", "")))
                f.flush()
                print("%s Ko libres" % mem["Heap"])
            else:
                print("pas de reponse Status 4")
            attend(client, args.pas)
    p = pente_par_heure(points)
    print("pente : %s Ko/h sur %d points (critere : ~0) ; CSV : %s" % ("n/a" if p is None else "%.2f" % p, len(points), chemin))


def cmd_so(args):
    client = connecte(args)
    client.abonne(["stat/%s/#" % args.topic])
    for commande in ("SetOption73", "SetOption114", "MqttRetry", "MqttTimeout"):
        reponse, _ = interroge(client, args.topic, commande)
        print(commande, "->", json.dumps(reponse) if reponse is not None else "PAS DE REPONSE")


def cmd_veille(args):
    adresse = args.url.rstrip("/") + "/cm?cmnd=Status%2011"
    dernier = None
    print("Interrogation toutes les 2 s. Couper le broker a la main, Ctrl+C pour finir.")
    try:
        while True:
            debut = time.time()
            try:
                with urllib.request.urlopen(adresse, timeout=10) as r:
                    uptime = json.loads(r.read().decode("utf-8", "replace"))["StatusSTS"]["UptimeSec"]
                duree = time.time() - debut
                alerte = ""
                if dernier is not None and uptime < dernier:
                    alerte = "  <<< REDEMARRAGE"
                elif duree > 1.0:
                    alerte = "  <<< LATENCE > 1 s (loop() bloque ?)"
                dernier = uptime
                print("%s uptime %d s, reponse %.0f ms%s" % (time.strftime("%H:%M:%S"), uptime, duree * 1000, alerte))
            except Exception as erreur:              # carte muette, mot de passe web, etc. : a lire, pas a masquer
                print("%s ERREUR : %s" % (time.strftime("%H:%M:%S"), type(erreur).__name__))
            time.sleep(2.0)
    except KeyboardInterrupt:
        pass


def autotest():
    r = resume([0.1, 0.2, 0.9], 4)
    assert r["pertes"] == 1 and r["max"] == 0.9 and r["mediane"] == 0.2
    assert resume([], 3)["pertes"] == 3
    assert abs(pente_par_heure([(0, 100.0), (1800, 99.0), (3600, 98.0)]) + 2.0) < 1e-9     # -2 Ko/h
    assert abs(pente_par_heure([(0, 50.0), (60, 50.0), (120, 50.0)])) < 1e-9                # plat
    assert pente_par_heure([(0, 1.0)]) is None
    print("autotest OK")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--autotest", action="store_true")
    sp = p.add_subparsers(dest="cmd")
    for nom, fn in (("rtt", cmd_rtt), ("tas", cmd_tas), ("so", cmd_so)):
        s = sp.add_parser(nom)
        s.add_argument("--topic", required=True)
        s.add_argument("--hote")
        s.add_argument("--port")
        if nom == "rtt":
            s.add_argument("--n", type=int, default=20)
        if nom == "tas":
            s.add_argument("--duree", type=int, default=3600)
            s.add_argument("--pas", type=int, default=60)
        s.set_defaults(fn=fn)
    s = sp.add_parser("veille")
    s.add_argument("--url", required=True)
    s.set_defaults(fn=cmd_veille)
    args = p.parse_args()
    if args.autotest:
        return autotest()
    if not args.cmd:
        p.error("sous-commande requise (rtt, tas, so, veille) ou --autotest")
    args.fn(args)


if __name__ == "__main__":
    main()

"""Banc de genere_brochage_excel.py, sans Excel : lecture des usages d'un persist et texte de chaque broche.

Lancer : python outils_docs/scripts_python/outils_pc/test_genere_brochage.py  (code 0 = vert)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genere_brochage_excel import CARTES, DEPOT, noms_composants, usages_persist, texte_broche

NOMS = noms_composants(DEPOT)
S3 = CARTES["esp32s3-devkitc1"]
PERSIST = {
    "template": {"GPIO": [1, 1, 1, 1, 3232, 1, 1, 1, 608, 640] + [1] * 28},   # GPIO4 RXD, 8 SCL, 9 SDA
    "drivers": {"ModBus": {"activation": "ON", "name": "ModBus RS485",
                           "env": {"RX": {"activation": "ON", "nom": "Série Rx", "pin": 4}}},
                "I2S": {"activation": "OFF", "name": "Bus I2S",                 # bloc coupe : ignore
                        "env": {"dout": {"activation": "ON", "nom": "I2S DOut", "pin": 9}}},
                "leds": {"name": "Leds", "env": {"led1": {"pin": 39, "type": 288},
                                                 "led2": {"pin": 0, "type": 289}}}},
    "modules": {"m": {"activation": "ON", "name": "Cuve",
                      "env": {"c1": {"activation": "OFF", "nom": "Compteur 1", "pin": 4},   # entree coupee : ignoree
                              "t1": {"activation": "ON", "nom": "Sonde", "pin": 39, "type": 1312}}}},
}
erreurs = []


def verifie(nom, obtenu, attendu):
    if obtenu != attendu:
        erreurs.append(f"{nom} : obtenu {obtenu!r}, attendu {attendu!r}")


u = usages_persist(PERSIST, NOMS, S3)
verifie("GPIO4 = ModBus seul (compteur OFF ignore)", [t for t, _ in u[4]], ["ModBus RS485 : Série Rx"])
verifie("famille ModBus", u[4][0][1], "modbus")
verifie("GPIO9 : bloc I2S OFF ignore, gabarit I2C_SDA repris", [t for t, _ in u[9]], ["Tasmota : I2C_SDA 1"])
verifie("GPIO39 : deux usages actifs", len(u[39]), 2)
verifie("texte LED1 decode", u[39][0][0], "Leds : led1 (LED1 1)")
t, fam, conflit = texte_broche("39", u, S3)
verifie("conflit signale sur GPIO39", conflit, True)
t, fam, conflit = texte_broche("0", u, S3)
verifie("broche BOOT utilisee : avertissement court", t, "Leds : led2 (LED1 2)  ⚠ BOOT")
verifie("broche libre", texte_broche("15", u, S3), ("libre", "libre", False))
verifie("masse", texte_broche("GND", u, S3), ("Masse", "gnd", False))

# temoin : sans le filtre d'activation, le compteur OFF apparaitrait sur GPIO4
PERSIST["modules"]["m"]["env"]["c1"]["activation"] = "ON"
verifie("temoin : compteur ON -> conflit sur GPIO4", len(usages_persist(PERSIST, NOMS, S3)[4]), 2)

# classeur du 7B : une ligne par GPIO sans doublon, GPIO6 seule libre, dalle RGB, EXIO5 a 0 (USB)
from genere_brochage_7b import GPIO as G7, EXIO as E7
verifie("7B : GPIO uniques", len({g[0] for g in G7}), len(G7))
verifie("7B : GPIO6 seule libre", [g[0] for g in G7 if g[3] == "libre"], [6])
verifie("7B : 20 broches de dalle RGB", sum(1 for g in G7 if g[3] == "ecran"), 20)
verifie("7B : 8 EXIO, EXIO5 a 0", ([e[0] for e in E7], [e[2] for e in E7 if e[0] == 5]), (list(range(8)), [0]))

for e in erreurs:
    print("ROUGE", e)
print("VERT" if not erreurs else f"{len(erreurs)} echec(s)")
sys.exit(1 if erreurs else 0)

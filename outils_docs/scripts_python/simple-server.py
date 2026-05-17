#!/usr/bin/env python3
# coding=utf-8

"""
Usage:
        ./outils_docs/scripts_python/simple-server.py -i <ip_address>:<port> -d <serveur_directory>

Example:
        ./outils_docs/scripts_python/simple-server.py -i 192.168.0.3:80 -d outils_docs/
        ./outils_docs/scripts_python/simple-server.py -i 192.168.0.3:80
        ./outils_docs/scripts_python/simple-server.py

Remarques:
        - Le dossier par défaut est 'build_output/'
        - L'adresse IP par défaut est '127.0.0.1:80' ==> la connexion n'est possible que depuis la machine locale
        - Pour une connexion depuis d'autres machines, indiquer l'adresse IP locale de la machine hébergeant le serveur
        - Attention aux droits d'accès des dossiers et fichiers:
                sudo chmod -R 755 <dossier>
                modifier les groupes et propriétaires si nécessaire
        - Le serveur doit être démarré avec des droits administrateurs: utiliser la commande sudo chown pour changer le propriétaire du script si nécessaire:
                ex: sudo chown <user>:<groupe> outils_docs/scripts_python/simple-server.py
        - Pour utiliser un autre port (ex: 8080), il faut aussi modifier l'adresse IP en conséquence.
        - Pour arrêter le serveur, faire Ctrl+C dans le terminal
"""

import os
import sys
import argparse
from colorama import Fore, Back, Style
import subprocess

# Serveur de fichiers OTA
# sudo python3 -m http.server -b 192.168.0.3 80 -d outils_docs/
def esp32_creer_server(args):
        print(args.dossier)
        if (not(args.dossier) or args.dossier == 'build_output/'):
                print(Fore.YELLOW + f"Le dossier de localisation des firmwares par défaut est: '{args.dossier}'")

        # Lance la commande python
        try:
                print(f"Le serveur de fichiers OTA pour les mises à jour Tasmota est démarré à l'adresse suivante: http://{args.adresse_ip}/")
                CMD = f"python -m http.server -b {args.adresse_ip.split(':')[0]} {args.adresse_ip.split(':')[1]} -d {args.dossier}"
                subprocess.run(CMD, shell=True, check=True)
        except subprocess.CalledProcessError as e:
                print(f"La commande a échoué avec le code de retour {e.returncode}")
        
if __name__ == '__main__': 
        parser = argparse.ArgumentParser(prog='simple-server', description='Démarre un serveur OTA', epilog='A bientôt !')

        parser.add_argument('-i', '--adresse_ip', type=str, default='127.0.0.1:80', help='Adresse IP du serveur OTA')
        parser.add_argument('-d', '--dossier', type=str, default='build_output/', help='Dossier sur le serveur')
        
        args = parser.parse_args()               
        esp32_creer_server(args)

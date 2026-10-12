import sys
import socket
from tqdm import tqdm
import time
import argparse

# Librairies nécessaire :
# pip install tqdm : https://pypi.org/project/tqdm/#manual

# Fournit une aide
parser=argparse.ArgumentParser(description="Script permettant d'uploader un fichier en udp par python !")

# Ajoute les arguments nécessaires en ligne de commande
parser.add_argument("-ipDest", type=str)            #IP de destination
parser.add_argument("-portDest", type=int)          #port de destination
parser.add_argument("-fonction", type=str)          #fonction à executer (envoi de message / envoi de fichier)
parser.add_argument("-msg", type=str)               #port de destination
parser.add_argument("-file", type=str)              #chemion absolu du fichier à lire
args=parser.parse_args()

# Fonction qui gère l'envoi du message
def send_msg_udp_request(server_ip, server_port, msg):
    client = None
    
    try:
        if server_port and server_ip and msg != "":
            print ("Connection UDP en cours ...")
            
            # Montre une barre de progression rouge dès le demarrage de l'envoi
            for _ in tqdm(range(10), desc="Envoi en cours", ascii=True, colour='#9b9796'):
                time.sleep(0.1)
            
            # connexion UDP
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client.settimeout(1.0)
            try:
                client.connect((server_ip, server_port))
                client.settimeout(None)
                
                # Envoi le message
                client.settimeout(3.0)
                try:
                    client.sendto(msg.encode(), (server_ip, server_port))
                    print("Envoi du message complété.")
                    
                    # Récupère la réponse
                    client.settimeout(3.0)
                    try:
                        data, addr = client.recvfrom(1024)
                        client.settimeout(None)
                        
                        print("Response reçue de l'hôte", addr, ":")
                        print(data.decode())
                    except Exception as e:
                        print("Erreur de réception: ", "aucun message reçu !")
                    
                    client.close()
                except Exception as e:
                    print("Erreur: ", e)
            except Exception as e:
                print("Erreur de connexion: ", e)
    except Exception as e:
        # if e == "timed out":
            print("Erreur de connexion: Aucune réponse reçue.", e)

# Fonction qui gère l'envoi d'un fichier
def send_file_udp_request(server_ip, server_port, file):
    client = None
    
    try:
        if server_port and server_ip and file != "":
            print ("Connection UDP en cours ...")

            # Montre une barre de progression rouge dès le demarrage de l'envoi
            for _ in tqdm(range(10), desc="Envoi en cours", ascii=True, colour='#9b9796'):
                time.sleep(0.1)
                
            # connexion UDP
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client.settimeout(1.0)
            try:
                client.connect((server_ip, server_port))
                client.settimeout(None)
                
                # Envoi le message
                # client.settimeout(3.0)
                try:
                    # Lecture du fichier
                    with open(file) as lines:
                        i = 1
                        for line in lines:
                            line = line.rstrip('\n') # On retire le saut de ligne
                            
                            print(i, ':', line)
                            client.sendto(line.encode(), (server_ip, server_port))
                            
                            i += 1
                        # client.sendto(msg.encode(), (server_ip, server_port))
                        # print("Envoi du message complété.")
                    
                    # Récupère la réponse
                    # client.settimeout(3.0)
                    # try:
                    #     data, addr = client.recvfrom(1024)
                    #     client.settimeout(None)
                        
                    #     print("Response reçue de l'hôte", addr, ":")
                    #     print(data.decode())
                    # except Exception as e:
                    #     print("Erreur de réception: ", "aucun message reçu !")
                    
                    # client.close()
                except Exception as e:
                    print("Erreur: ", e)
            except Exception as e:
                print("Erreur de connexion: ", e)
    except Exception as e:
        # if e == "timed out":
            print("Erreur de connexion: Aucune réponse reçue.", e)
               
# Fonction principale        
def main():
    try:
        if args.ipDest:
            print ("IP de la cible:", args.ipDest)
        else:
            args.ipDest = input("Entrez l'IP de l'hôte: ")
        
        if args.portDest:
            print ("Port UDP à utiliser:", args.portDest)
        else:
            args.portDest = input("Entrez le port à utiliser pour la connexion UDP: ")
            
        if args.fonction:
            print ("Fonction à executer:", args.fonction)
        else:
            args.fonction = input("Entrez la fonction à executer (1: Envoyer un message / 2: Envoyer un fichier): ")
        
        # Envoi d'un message en UDP
        if args.fonction == '1':
            if args.msg:
                print ("Message à envoyer:", args.msg)
            else:
                args.msg = input("Entrez le message à envoyer: ")
                
            send_msg_udp_request(args.ipDest, args.portDest, args.msg)
        # Envoi d'un fichier en UDP
        else:   
            if args.file:
                print ("Chemin du fichier à lire:", args.file)
            else:
                args.file = input("Entrez le chemin du fichier à lire: ")
                
            send_file_udp_request(args.ipDest, args.portDest, args.file)
        
    except ValueError:
        print("Port invalide. Entrez un entier pour définir le port.")
    except KeyboardInterrupt:
        print("\nProcédure interrompu par l'utilisateur.")

if __name__ == "__main__":
    main()
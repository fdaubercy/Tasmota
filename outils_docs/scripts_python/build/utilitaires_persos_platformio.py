import os
from pathlib import Path
import subprocess
import shutil
import datetime
import sys
from colorama import Fore, Back, Style

# Pour test
""" 
print("Path at terminal when executing this file")
print(os.getcwd() + "\n")

print("This file path, relative to os.getcwd()")
print(__file__ + "\n")

print("This file full path (following symlinks)")
full_path = os.path.realpath(__file__)
print(full_path + "\n")

print("This file directory and name")
path, filename = os.path.split(full_path)
print(path + ' --> ' + filename + "\n")

print("This file directory only")
print(os.path.dirname(full_path)) 
"""

def main():
    # Chemin absolu du dossier courant
    # print(os.getcwd()) 
    
    # Chemin absolu du dossier parent du script
    dossier_scripts = Path(__file__).parent

    print("Que voulez-vous faire ?")
    print("     >1. Recharger l'environnement de travail PlatformIO")
    print("     >2. Lancer la compilation des projets paramétrés dans platformio_override.ini")
    print("     >3. Lancer la compilation & l'upload des projets paramétrés dans platformio_override.ini")
    print("     >4. Sauvegarder certains fichiers personnels du dépôt Git dans un dossier")
    print("     >5. Synchronisation du dépôt Git avec Github")
    print("     >6. Récupérer les fichiers d'un dossier de sauvegarde")
    print("     >7. Lancer un serveur web local")
    
    choice = input("Entrez le numéro de votre choix: ")
    if choice == '1':
        reload_platformio()
    elif choice == '2':
        compile_all_projets()
    elif choice == '3':
        compile_upload_all_projets()
    elif choice == '4':
        sauvegarde_files_perso_platformio()
    elif choice == '5':
        sychronise_avec_github()
    elif choice == '6':
        restore_backup()
    elif choice == '7':
        serveur_web_local()
    else:
        print("Choix invalide. Veuillez réessayer !")
        
# exemple de script pio pour lancer la compilation du projet et son upload sur le port sélectionné
# os.system('pio run -t erase_upload -e tasmota32s3-maitre --upload-port COM3')

def serveur_web_local():
    print("Lancement du serveur web local par python sur le port 80...")
    print("Lien vers le serveur web: http://localhost:80")
    # os.system('pip install netifaces flask')
    os.system('python -m http.server 80')
        
# Recharge l'environnement de travail PlatformIO
# en initialisant le projet PlatformIO et en nettoyant
def reload_platformio():
    print("Rechargement de l'environnement de travail PlatformIO...")
    os.system('platformio init --ide vscode')
    
    print("Nettoyage de travail PlatformIO...")
    os.system('pio run -t clean')
    print("Environnement de travail PlatformIO rechargé avec succès.")
    
# Démarre la compilation des projets PlatformIO décommentés dans 'platformio_override.ini'
def compile_all_projets():
    print("Compilation des projets PlatformIO...")
    os.system('pio run')
    
# Démarre la compilation des projets PlatformIO décommentés dans 'platformio_override.ini'
def compile_upload_all_projets():
    print("Compilation & Upload des projets PlatformIO...")
    os.system('pio run -t erase_upload')
    
# Sauvegarde certains fichiers définis dans un fichier text
# dans un dossier du disque dur: "nom_depot-%date_jour-backup%"
def sauvegarde_files_perso_platformio():
    try:
        # Importer la fonction
        from backup import sauvegarder_fichiers
        
        # Fichiers à sauvegarder
        fichiers = [
            "./data*",
            "./config.json",
            "./logs/*.log"
        ]
        
        # Lancer la sauvegarde
        print("Démarrage de la sauvegarde...")
        rapport = sauvegarder_fichiers(fichiers, "./backups")
        
        # Vérifier le résultat
        if rapport['erreurs']:
            print(f"⚠️  Sauvegarde terminée avec {len(rapport['erreurs'])} erreur(s)")
            for erreur in rapport['erreurs']:
                print(f"  - {erreur}")
            return False
        else:
            print(f"✓ Sauvegarde réussie : {len(rapport['succès'])} élément(s)")
            print(f"  Dossier: {rapport['dossier_backup']}")
            return True
            
    except ImportError:
        print("Erreur: impossible d'importer le module backup.py")
        return False
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return False
    
# Synchronisation du dépôt Git avec Github
def sychronise_avec_github():
    print("Synchronisation sur dépôt Github ...")
    # os.system('git add .')
    # os.system('git commit -m "Sauvegarde des fichiers du dépôt Git"')
    # os.system('git push')
    print("Synchronisation sur dépôt Github avec succès.")
    
# Restauration dans le dépôt local des fichiers sauvegardés
# dans un dossier du disque dur: "nom_depot-%date_jour-backup%"
def restore_backup():
    backup_folder = input("Entrez le chemin du dossier de sauvegarde: ")
    destination_folder = input("Entrez le chemin du dossier de destination: ")

    if os.path.exists(backup_folder) and os.path.isdir(backup_folder):
        print("Récupération des fichiers du dossier de sauvegarde...")
        for item in os.listdir(backup_folder):
            s = os.path.join(backup_folder, item)
            d = os.path.join(destination_folder, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        print("Fichiers récupérés avec succès.")
    else:
        print("Le dossier de sauvegarde n'existe pas ou n'est pas un dossier valide.")

if __name__ == "__main__":
    main()

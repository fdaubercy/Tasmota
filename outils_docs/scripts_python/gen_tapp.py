import os
import sys
import argparse
import os.path
import zipfile 
import shutil
from colorama import Fore, Back, Style

parser = argparse.ArgumentParser(prog='gen_tapp', description='Génère le fichier *.tapp', epilog='A bientôt !')

parser.add_argument('-d', '--dossier', type=str, help='Dossier contenant les scripts berry à zipper & l\'archive *.tapp')
parser.add_argument('-v', '--verbose', help='Augmente le niveau de logs', action='store_true')
args = parser.parse_args()

def main():
    # Le dossier contenant les scripts berry à zipper
    # if (args.dossier):
    #     folder = args.dossier
    # else:   
    #     folder = "raw"
    #     print(Fore.YELLOW + f"Le dossier de localisation des fichiers compressés par défaut est: '{folder}'")
        
    # Détermine le nom de l'archive
    try:
        file_name = input(Fore.WHITE + "Entrez le nom de l'archive à créer (optionnel): ")
        try:
            if file_name == '':
                raise ValueError('No name provided')
            # print(f"Next year, you'll be {age + 1}.")
        except ValueError as e:
            file_name = 'archive.tapp'
            
            # Corrige le nom si nécessaire
            if not file_name.endswith(('.tapp')):
                file_name += '.tapp'
                
            print(Fore.YELLOW + f"Vous n'avez pas renseigné le nom de l'archive, le nom par défaut '{file_name}' sera utilisé.")
    except Exception as outer_error:
        print(f"Erreur: {outer_error}")
        
    # Corrige le nom si nécessaire
    if not file_name.endswith(('.tapp')):
        file_name += '.tapp'
    
    # # L'archive 'tapp' à créer dans le dossier 'raw'
    # file_name = os.path.normpath(os.path.join(folder, file_name))
    
    # # On crée le dossier s'il n'existe pas
    # if not os.path.exists(folder):
    #     os.makedirs(folder)
    #     print(Fore.YELLOW + f"Le dossier '{folder}' n'existait pas, il a été créé.")
    
    # Supprime le fichier / dossier indiqué
    if os.path.exists(file_name):
        os.remove(file_name)
        
    # Détermine le dossier contenant les fichiers à zipper
    try:
        folder_origine = input(Fore.WHITE + "Entrez le chemin relatif des dossiers à compresser: ")
        try:
            if folder_origine == '':
                raise ValueError('No name provided')

        except ValueError as e:
            print(Fore.RED + f"Vous n'avez pas renseigné le chemin du dossier contenant les fichiers à compresser.")
            return
    except Exception as outer_error:
        print(Fore.RED + f"Erreur: {outer_error}")
        return
    
    # Le dossier de création de l'archive est celui des fichiers à zipper
    folder = folder_origine
    file_name = os.path.normpath(os.path.join(folder, file_name))
        
    # Crée le fichier zip
    with zipfile.ZipFile(file_name, "w", zipfile.ZIP_DEFLATED) as zfile:
        # Liste les fichiers dans le dossier 'raw'
        for root, _, files in os.walk(folder):
            for file in files:
                # Evite le fichier d'archive lui même
                if file.endswith(('.tapp')):
                    continue
            
                # Ajoute le fichier au zip
                filename = os.path.join(root, file)
                zfile.write(filename, os.path.relpath(filename, folder))
    print(Fore.GREEN + f"La création du fichier '{file_name}' dans le dossier '{os.path.normpath(folder + "/")}' s'est terminée avec succès.")

    # Ouvre le 'Zip' pour tester son contenu
    if args.verbose:
        with zipfile.ZipFile(file_name, 'r') as zipArchive:
            print(Fore.GREEN + f"Il contient les fichier suivants: '{zipArchive.namelist()}'")
    
if __name__ == '__main__': main()
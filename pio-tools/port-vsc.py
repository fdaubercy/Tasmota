env = DefaultEnvironment()

import os
import glob as fileglob

if os.environ.get("PLATFORMIO_CALLER") == "vscode":
    print("PIO appelé depuis l'extension VS Code")
    import platform
    import json

    # Vérifier si pioarduino IDE >= 1.3.6 est installé (gère le port nativement)
    os_name = platform.system()
    if os_name == "Windows":
        ext_base = os.path.join(os.environ.get("USERPROFILE", ""), ".vscode", "extensions")
    else:
        ext_base = os.path.expanduser("~/.vscode/extensions")

    skip = False
    for ext_dir in fileglob.glob(os.path.join(ext_base, "pioarduino.pioarduino-ide-*")):
        try:
            ver_str = os.path.basename(ext_dir).split("pioarduino.pioarduino-ide-")[1]
            ver_parts = tuple(int(x) for x in ver_str.split(".")[:3])
            if ver_parts >= (1, 3, 6):
                print("pioarduino IDE %s détecté, port géré par l'extension" % ver_str)
                skip = True
                break
        except (IndexError, ValueError):
            pass

    if not skip:
        import sqlite3
        from platformio.project.helpers import get_project_dir

        print("Plateforme OS :", os_name)
        os_paths = {
            "Darwin": "~/Library/Application Support/Code/User/globalStorage/state.vscdb",
            "Linux": "~/.config/Code/User/globalStorage/state.vscdb",
            "Windows": r"%APPDATA%\Code\User\globalStorage\state.vscdb"
        }
        project_path = get_project_dir()

        try:
            db_path = os.path.expanduser(os.path.expandvars(os_paths[os_name]))
        except KeyError:
            print("OS inconnu : " + os_name)

        # Si la base de données n'est pas trouvée, vérifier si on tourne dans WSL
        # et essayer de trouver la base de données dans le système de fichiers Windows
        if not os.path.exists(db_path) and os_name == "Linux":
            try:
                db_path = os.path.expanduser(os.path.expandvars(os_paths["Windows"]))
                print("Windows exécutant PIO dans WSL")
            except KeyError:
                pass

        # On continue seulement si la base de données est trouvée
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            for key in ['pioarduino.pioarduino-ide', 'platformio.platformio-ide']:
                cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    data = json.loads(row[0])
                    projects = data.get("projects", {})
                    project = projects.get(project_path)
                    if project and "customPort" in project:
                        print("Port USB défini dans VSC :", project["customPort"])
                        env["UPLOAD_PORT"] = project["customPort"]
                        break
            conn.close()

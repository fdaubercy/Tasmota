import socket
import struct
import threading
import tkinter as tk
from tkinter import scrolledtext, simpledialog, colorchooser, messagebox
import os
import re

# ---------------------- Paramètres par défaut ----------------------
# Ces valeurs seront réécrites automatiquement dans ce fichier lors du bouton "Mettre à jour"
DEFAULT_MODE = "MULTICAST"
DEFAULT_MULTICAST_GROUP = '192.168.0.43'
DEFAULT_UNICAST_IP = '192.168.1.10'
DEFAULT_PORT = 2000
LOCAL_IP = "192.168.0.3"

# ---------------------- Pseudo ----------------------
root = tk.Tk()
root.withdraw()
USERNAME = simpledialog.askstring("Pseudo", "Entrez votre pseudo :")
if not USERNAME:
    USERNAME = f"User_{LOCAL_IP}"
root.deiconify()

# ---------------------- Centrer la fenêtre ----------------------
window_width = 1500
window_height = 700
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width - window_width) // 2
y = (screen_height - window_height) // 2
root.geometry(f"{window_width}x{window_height}+{x}+{y}")
root.title("Chat UDP Multicast / Unicast")

# ---------------------- Couleurs ----------------------
bg_color = "#2e2e2e"
msg_bg_color = "#444444"
fg_color = "white"
my_msg_color = "white"
other_msg_color = "#ffff66"

# ---------------------- Frame principale ----------------------
frame = tk.Frame(root, bg=bg_color)
frame.pack(fill=tk.BOTH, expand=True)

# ---------------------- Frame paramètres ----------------------
param_frame = tk.Frame(frame, bg=bg_color)
param_frame.pack(fill=tk.X, padx=10, pady=5)

mode_label = tk.Label(param_frame, text="Mode :", bg=bg_color, fg=fg_color)
mode_label.pack(side=tk.LEFT, padx=5)

mode_var = tk.StringVar(value=DEFAULT_MODE)
mode_menu = tk.OptionMenu(param_frame, mode_var, "MULTICAST", "UNICAST")
mode_menu.pack(side=tk.LEFT, padx=5)

ip_label = tk.Label(param_frame, text="IP :", bg=bg_color, fg=fg_color)
ip_label.pack(side=tk.LEFT, padx=5)
ip_entry = tk.Entry(param_frame, width=15, bg=msg_bg_color, fg=fg_color)
ip_entry.pack(side=tk.LEFT, padx=5)
ip_entry.insert(0, DEFAULT_MULTICAST_GROUP if DEFAULT_MODE == "MULTICAST" else DEFAULT_UNICAST_IP)

port_label = tk.Label(param_frame, text="Port :", bg=bg_color, fg=fg_color)
port_label.pack(side=tk.LEFT, padx=5)
port_entry = tk.Entry(param_frame, width=6, bg=msg_bg_color, fg=fg_color)
port_entry.pack(side=tk.LEFT, padx=5)
port_entry.insert(0, str(DEFAULT_PORT))

update_button = tk.Button(param_frame, text="Mettre à jour")
update_button.pack(side=tk.LEFT, padx=5)

# ---------------------- Frame chat ----------------------
chat_frame = tk.Frame(frame, bg=bg_color)
chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

chat_area = scrolledtext.ScrolledText(chat_frame, width=180, height=25, state='disabled',
                                      bg=msg_bg_color, fg=fg_color, font=("Arial", 11))
chat_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

entry = tk.Entry(chat_frame, width=100, bg=msg_bg_color, fg=fg_color, font=("Arial", 11))
entry.pack(fill=tk.X, padx=10, pady=5)

# ---------------------- Boutons ----------------------
button_frame = tk.Frame(chat_frame, bg=bg_color)
button_frame.pack(fill=tk.X, padx=10, pady=5)

send_button = tk.Button(button_frame, text="Envoyer", command=lambda: send_message())
send_button.pack(side=tk.LEFT, padx=5)

dark_mode_button = tk.Button(button_frame, text="Mode Sombre / Clair", width=25, command=lambda: toggle_dark_mode())
dark_mode_button.pack(side=tk.LEFT, padx=5)

color_button = tk.Button(button_frame, text="Couleur Mes Messages", command=lambda: choose_my_msg_color())
color_button.pack(side=tk.LEFT, padx=5)

# ---------------------- Variables dynamiques ----------------------
MODE = DEFAULT_MODE
TARGET_IP = DEFAULT_MULTICAST_GROUP if MODE == "MULTICAST" else DEFAULT_UNICAST_IP
PORT = DEFAULT_PORT
send_sock = None
recv_sock = None

# ---------------------- Fonctions ----------------------
def setup_sockets():
    global send_sock, recv_sock

    # ferme les sockets existants proprement
    try:
        if send_sock:
            send_sock.close()
    except Exception:
        pass
    try:
        if recv_sock:
            recv_sock.close()
    except Exception:
        pass

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    if MODE == "MULTICAST":
        # TTL pour multicast
        ttl = struct.pack('b', 1)
        send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_sock.bind(('', PORT))

        # Joindre le groupe multicast
        try:
            mreq = struct.pack("4sl", socket.inet_aton(TARGET_IP), socket.INADDR_ANY)
            recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        except Exception:
            # Sur certaines plateformes il faut fournir l'interface locale en 4s
            try:
                mreq = struct.pack("4s4s", socket.inet_aton(TARGET_IP), socket.inet_aton(LOCAL_IP))
                recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            except Exception:
                pass

    else:
        # UNICAST : écoute sur l'IP locale
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind((LOCAL_IP, PORT))


def send_message(event=None):
    global send_sock
    msg = entry.get()
    if not msg:
        return

    if not send_sock:
        setup_sockets()

    try:
        send_sock.sendto(msg.encode('utf-8'), (TARGET_IP, PORT))
    except Exception as e:
        messagebox.showerror("Erreur envoi", str(e))
        return

    chat_area.configure(state='normal')
    chat_area.insert(tk.END, f"[Moi] {msg}\n", "my_msg")
    chat_area.tag_config("my_msg", foreground=my_msg_color)
    chat_area.configure(state='disabled')
    chat_area.yview(tk.END)
    entry.delete(0, tk.END)

entry.bind("<Return>", send_message)

# ---------------------- Réécriture sûre des constantes ----------------------
def rewrite_defaults():
    """Réécrit les constantes en dur dans ce fichier Python.

    Cette fonction remplace uniquement les lignes de définition des constantes
    (DEFAULT_MODE, DEFAULT_MULTICAST_GROUP, DEFAULT_UNICAST_IP, DEFAULT_PORT, LOCAL_IP)
    en utilisant des expressions régulières ligne par ligne pour éviter de casser le reste du fichier.
    """
    try:
        file_path = os.path.abspath(__file__)
    except NameError:
        # Si exécuté dans un environnement où __file__ n'est pas défini
        return

    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Remplacements ligne par ligne (mode multi-lignes)
    code = re.sub(r'(?m)^DEFAULT_MODE\s*=.*$', f'DEFAULT_MODE = "{MODE}"', code)
    code = re.sub(
        r'(?m)^DEFAULT_MULTICAST_GROUP\s*=.*$',
        (f"DEFAULT_MULTICAST_GROUP = '{TARGET_IP}'" if MODE == 'MULTICAST' else "DEFAULT_MULTICAST_GROUP = '224.3.0.1'"),
        code
    )
    code = re.sub(
        r'(?m)^DEFAULT_UNICAST_IP\s*=.*$',
        (f"DEFAULT_UNICAST_IP = '{TARGET_IP}'" if MODE == 'UNICAST' else "DEFAULT_UNICAST_IP = '192.168.1.10'"),
        code
    )
    code = re.sub(r'(?m)^DEFAULT_PORT\s*=.*$', f'DEFAULT_PORT = {PORT}', code)
    code = re.sub(r'(?m)^LOCAL_IP\s*=.*$', f'LOCAL_IP = "{LOCAL_IP}"', code)

    # Sauvegarde sécurisée : écrit d'abord dans un fichier temporaire
    tmp_path = file_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(code)

    # Remplace le fichier original
    os.replace(tmp_path, file_path)


# ---------------------- Mise à jour des paramètres via l'UI ----------------------
def update_multicast_settings():
    global MODE, TARGET_IP, PORT, LOCAL_IP

    MODE = mode_var.get()
    ip = ip_entry.get().strip()
    port = port_entry.get().strip()

    try:
        port = int(port)
        if not (1024 <= port <= 65535):
            raise ValueError
    except ValueError:
        messagebox.showerror("Erreur", "Le port doit être un entier entre 1024 et 65535")
        return

    TARGET_IP = ip
    PORT = port
    # met à jour LOCAL_IP au moment de la sauvegarde
    try:
        LOCAL_IP = socket.gethostbyname(socket.gethostname())
    except Exception:
        pass

    setup_sockets()

    # Réécrit les valeurs par défaut dans le code source
    try:
        rewrite_defaults()
    except Exception as e:
        messagebox.showwarning("Attention", f"Impossible de réécrire le fichier source: {e}")

    messagebox.showinfo("Info", f"Paramètres mis à jour : {MODE} {TARGET_IP}:{PORT}")

update_button.config(command=update_multicast_settings)

# ---------------------- Réception ----------------------
def receiver():
    while True:
        try:
            if not recv_sock:
                break
            data, addr = recv_sock.recvfrom(1024)
            message = data.decode('utf-8')
            sender_ip = addr[0]

            if sender_ip != LOCAL_IP:
                chat_area.configure(state='normal')
                chat_area.insert(tk.END, f"[{sender_ip}] {message}\n", "other_msg")
                chat_area.tag_config("other_msg", foreground=other_msg_color)
                chat_area.configure(state='disabled')
                chat_area.yview(tk.END)
        except Exception:
            break

# Lance les sockets et le thread de réception
setup_sockets()
recv_thread = threading.Thread(target=receiver, daemon=True)
recv_thread.start()

# ---------------------- Dark mode et couleur ----------------------
def toggle_dark_mode():
    global bg_color, msg_bg_color, fg_color
    if bg_color == "#2e2e2e":
        bg_color = "white"
        msg_bg_color = "#f0f0f0"
        fg_color = "black"
    else:
        bg_color = "#2e2e2e"
        msg_bg_color = "#444444"
        fg_color = "white"

    frame.configure(bg=bg_color)
    param_frame.configure(bg=bg_color)
    chat_frame.configure(bg=bg_color)
    button_frame.configure(bg=bg_color)
    chat_area.configure(bg=msg_bg_color, fg=fg_color)
    entry.configure(bg=msg_bg_color, fg=fg_color)
    ip_label.configure(bg=bg_color, fg=fg_color)
    port_label.configure(bg=bg_color, fg=fg_color)


def choose_my_msg_color():
    global my_msg_color
    color = colorchooser.askcolor(title="Choisir la couleur de mes messages")
    if color and color[1]:
        my_msg_color = color[1]

# ---------------------- Fermeture ----------------------
def on_closing():
    try:
        if send_sock:
            send_sock.close()
    except Exception:
        pass
    try:
        if recv_sock:
            recv_sock.close()
    except Exception:
        pass
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()

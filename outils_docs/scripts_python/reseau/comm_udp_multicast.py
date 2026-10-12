import socket
import struct
import threading
import tkinter as tk
from tkinter import scrolledtext, simpledialog, colorchooser, messagebox

# ---------------------- Paramètres par défaut ----------------------
DEFAULT_MULTICAST_GROUP = '224.3.0.1'
DEFAULT_PORT = 4000
LOCAL_IP = socket.gethostbyname(socket.gethostname())

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
root.title("Chat Multicast UDP")

# ---------------------- Couleurs et style ----------------------
bg_color = "#2e2e2e"          # fond général sombre
msg_bg_color = "#444444"       # fenêtre messages plus claire
fg_color = "white"
my_msg_color = "white"         # messages envoyés
other_msg_color = "#ffff66"    # messages des autres

# ---------------------- Frame principale ----------------------
frame = tk.Frame(root, bg=bg_color)
frame.pack(fill=tk.BOTH, expand=True)

# ---------------------- Frame paramètres (en haut) ----------------------
param_frame = tk.Frame(frame, bg=bg_color)
param_frame.pack(fill=tk.X, padx=10, pady=5)

ip_label = tk.Label(param_frame, text="IP Multicast :", bg=bg_color, fg=fg_color)
ip_label.pack(side=tk.LEFT, padx=5)
ip_entry = tk.Entry(param_frame, width=15, bg=msg_bg_color, fg=fg_color)
ip_entry.pack(side=tk.LEFT, padx=5)
ip_entry.insert(0, DEFAULT_MULTICAST_GROUP)

port_label = tk.Label(param_frame, text="Port :", bg=bg_color, fg=fg_color)
port_label.pack(side=tk.LEFT, padx=5)
port_entry = tk.Entry(param_frame, width=6, bg=msg_bg_color, fg=fg_color)
port_entry.pack(side=tk.LEFT, padx=5)
port_entry.insert(0, str(DEFAULT_PORT))

update_button = tk.Button(param_frame, text="Mettre à jour")
update_button.pack(side=tk.LEFT, padx=5)

# ---------------------- Frame chat et saisie ----------------------
chat_frame = tk.Frame(frame, bg=bg_color)
chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

chat_area = scrolledtext.ScrolledText(chat_frame, width=180, height=25, state='disabled',
                                      bg=msg_bg_color, fg=fg_color, font=("Arial", 11))
chat_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

entry = tk.Entry(chat_frame, width=100, bg=msg_bg_color, fg=fg_color, font=("Arial", 11))
entry.pack(fill=tk.X, padx=10, pady=5)

# ---------------------- Frame boutons ----------------------
button_frame = tk.Frame(chat_frame, bg=bg_color)
button_frame.pack(fill=tk.X, padx=10, pady=5)

send_button = tk.Button(button_frame, text="Envoyer", command=lambda: send_message())
send_button.pack(side=tk.LEFT, padx=5)

dark_mode_button = tk.Button(button_frame, text="Mode Sombre / Clair", width=25, command=lambda: toggle_dark_mode())
dark_mode_button.pack(side=tk.LEFT, padx=5)

color_button = tk.Button(button_frame, text="Couleur Mes Messages", command=lambda: choose_my_msg_color())
color_button.pack(side=tk.LEFT, padx=5)

# ---------------------- Variables multicast dynamiques ----------------------
MULTICAST_GROUP = DEFAULT_MULTICAST_GROUP
PORT = DEFAULT_PORT
send_sock = None
recv_sock = None

# ---------------------- Fonctions ----------------------
def setup_sockets():
    global send_sock, recv_sock
    if send_sock:
        send_sock.close()
    if recv_sock:
        recv_sock.close()
    
    # Socket pour envoyer
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    ttl = struct.pack('b', 1)
    send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    # Socket pour recevoir
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    recv_sock.bind(('', PORT))
    mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
    recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

def send_message(event=None):
    msg = entry.get()
    if msg:
        # Envoi du message pur sans le pseudo
        send_sock.sendto(msg.encode('utf-8'), (MULTICAST_GROUP, PORT))
        chat_area.configure(state='normal')
        chat_area.insert(tk.END, f"[Moi] {msg}\n", "my_msg")
        chat_area.tag_config("my_msg", foreground=my_msg_color)
        chat_area.configure(state='disabled')
        chat_area.yview(tk.END)
        entry.delete(0, tk.END)

entry.bind("<Return>", send_message)

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
    if color[1]:
        my_msg_color = color[1]

def update_multicast_settings():
    global MULTICAST_GROUP, PORT
    ip = ip_entry.get()
    port = port_entry.get()
    try:
        port = int(port)
        if not (1024 <= port <= 65535):
            raise ValueError
    except ValueError:
        messagebox.showerror("Erreur", "Le port doit être un entier entre 1024 et 65535")
        return
    MULTICAST_GROUP = ip
    PORT = port
    setup_sockets()
    messagebox.showinfo("Info", f"Paramètres mis à jour : {MULTICAST_GROUP}:{PORT}")

update_button.config(command=update_multicast_settings)

# ---------------------- Réception en thread ----------------------
def receiver():
    while True:
        try:
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

setup_sockets()
recv_thread = threading.Thread(target=receiver, daemon=True)
recv_thread.start()

# ---------------------- Fermeture propre ----------------------
def on_closing():
    if send_sock:
        send_sock.close()
    if recv_sock:
        recv_sock.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()

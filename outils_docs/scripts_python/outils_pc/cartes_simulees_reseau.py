"""Identite reseau d'une carte simulee, lue dans son _persist.json (plan tasks/plans/cartes-simulees.md, A3 et A5).

Une carte simulee annonce EXACTEMENT ce que le persist de la vraie carte porte : nom d'hote, IP, passerelle, masque, DNS,
point d'acces du range extender, MQTT (hote, port, client, topic), port UDP, identifiant ModBus. Rien n'est invente :
une valeur absente du persist reste absente, une IP a 0.0.0.0 (DHCP) est signalee comme telle.

MQTT : l'identite est AFFICHEE, jamais connectee. Un second client avec le meme `client` ferait deconnecter la vraie carte
du broker ; publier sous le meme topic brouillerait Node-RED et l'historique.
"""
import json
from pathlib import Path


def profil(dossier_carte):
    """Profil reseau tire de <dossier_carte>/_persist.json. Leve FileNotFoundError / ValueError si le persist manque ou est illisible."""
    persist = json.loads((Path(dossier_carte) / "_persist.json").read_text(encoding="utf-8"))
    s = persist.get("serveur", {})
    ip = s.get("IP", {})
    mq = s.get("mqtt", {})
    re_ = s.get("rangeExtender", {})
    ap = re_.get("AP", {})
    adresse = ip.get("IPAddress", "")
    esclave = re_.get("activation") == "ON" and bool(re_.get("ipMaitre"))
    return {
        "hostname": s.get("hostname", ""),
        "nom": s.get("nom", ""),
        "ip": adresse, "dhcp": adresse in ("", "0.0.0.0"),
        "passerelle": ip.get("IPGateway", ""), "masque": ip.get("Subnet", ""), "dns": ip.get("DNSServer", ""),
        "mdns": s.get("mDNS") == "ON",
        "mqtt": {"actif": mq.get("activation") == "ON", "hote": mq.get("hote", ""), "port": mq.get("port"),
                 "client": mq.get("client", ""), "topic": mq.get("topic", "")},
        "ap": {"ip": ap.get("IPAddress", ""), "masque": ap.get("Subnet", ""), "ssid": ap.get("SSID", ""), "napt": ap.get("routeNAPT") == "ON"},
        "esclave": esclave, "id": re_.get("id"), "ip_maitre": re_.get("ipMaitre", ""),
        "udp": {"actif": s.get("udp", {}).get("activation") == "ON", "port": s.get("udp", {}).get("port")},
        # Une carte derriere le NAPT du maitre se joint par <ipMaitre>:<8080 + id - 1> (build_envs.adresse_par_maitre)
        "port_web": (8080 + int(re_["id"]) - 1) if esclave and isinstance(re_.get("id"), int) else 80,
    }


def status5(p):
    """Reponse de `Status 5` : StatusNET avec les valeurs du persist (cles de la vraie reponse, MAC et IPv6 non connus : omis)."""
    return {"StatusNET": {"Hostname": p["hostname"], "IPAddress": p["ip"], "Gateway": p["passerelle"], "Subnetmask": p["masque"],
                          "DNSServer1": p["dns"], "Webserver": 2, "HTTP_API": 1}}


def statut_mqtt(p):
    """Reponse de `Status 6` reduite aux cles du persist (le simulateur ne se connecte pas au broker)."""
    m = p["mqtt"]
    return {"StatusMQT": {"MqttHost": m["hote"], "MqttPort": m["port"], "MqttClient": m["client"], "Topic": m["topic"], "MqttSimule": "non connecte"}}


def resume(p):
    """Lignes lisibles du profil, pour la console et le panneau."""
    ip = p["ip"] + (" (DHCP : adresse attribuee par le point d'acces du maitre, inconnue ici)" if p["dhcp"] else "")
    lignes = [f"hote {p['hostname']} ({p['nom']})", f"adresse du parc {p.get('adresse') or 'inconnue'}", f"IP du persist {ip}", f"passerelle {p['passerelle']}  masque {p['masque']}  DNS {p['dns']}",
              f"port web {p['port_web']}" + (f" (maitre {p['ip_maitre']}, id {p['id']})" if p["esclave"] else "")]
    if p["ap"]["ip"]:
        lignes.append(f"point d'acces {p['ap']['ssid']} {p['ap']['ip']}/{p['ap']['masque']} NAPT {'ON' if p['ap']['napt'] else 'OFF'}")
    if p["mqtt"]["actif"]:
        lignes.append(f"MQTT {p['mqtt']['hote']}:{p['mqtt']['port']} client {p['mqtt']['client']} topic {p['mqtt']['topic']} (affiche, non connecte)")
    return lignes

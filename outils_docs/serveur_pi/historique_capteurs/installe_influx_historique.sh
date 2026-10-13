#!/usr/bin/env bash
# Prepare InfluxDB 1.x pour l'historique des capteurs Tasmota. A lancer SUR le Pi, idempotent.
#
#   ./installe_influx_historique.sh            applique
#   ./installe_influx_historique.sh --dry-run  affiche les commandes sans rien executer
#
# Cree dans la base Iot (sans toucher a autogen ni a la RP par defaut) :
#   - RP "capteurs_5ans"   : 260 semaines, NON par defaut -> les ecritures doivent la nommer (rp=)
#   - RP "capteurs_horaire": duree infinie, pour les agregats
#   - CQ "cq_capteurs_horaire" : min/mean/max horaires de capteurs et etat
#
# Authentification (facultative) : variables d'environnement INFLUX_USER et INFLUX_PASSWORD
# (jamais en dur). Si INFLUX_USER est defini sans mot de passe, il est demande au clavier.
# Le mot de passe passe par la variable INFLUX_PASSWORD lue par le client, pas par la ligne de commande.
set -euo pipefail

BASE="Iot"
RP_DETAIL="capteurs_5ans"
RP_HORAIRE="capteurs_horaire"
CQ="cq_capteurs_horaire"
DRY=0

case "${1:-}" in
    --dry-run) DRY=1 ;;
    "") ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "Option inconnue : $1 (essayer --dry-run)" >&2; exit 2 ;;
esac

CMD_RP_DETAIL="CREATE RETENTION POLICY \"$RP_DETAIL\" ON \"$BASE\" DURATION 260w REPLICATION 1"
CMD_RP_HORAIRE="CREATE RETENTION POLICY \"$RP_HORAIRE\" ON \"$BASE\" DURATION INF REPLICATION 1"
CMD_CQ="CREATE CONTINUOUS QUERY \"$CQ\" ON \"$BASE\" BEGIN SELECT min(*), mean(*), max(*) INTO \"$BASE\".\"$RP_HORAIRE\".:MEASUREMENT FROM \"$BASE\".\"$RP_DETAIL\"./^(capteurs|etat)\$/ GROUP BY time(1h), * END"

if [ "$DRY" -eq 1 ]; then
    echo "# --dry-run : rien n'est execute. Commandes qui seraient lancees (si absentes) :"
    printf "influx -execute '%s'\n" "$CMD_RP_DETAIL" "$CMD_RP_HORAIRE" "$CMD_CQ"
    exit 0
fi

command -v influx >/dev/null 2>&1 || { echo "ERREUR : client 'influx' introuvable (a lancer sur le Pi)." >&2; exit 1; }

# Identifiants : variables d'environnement lues par le client influx 1.x
if [ -n "${INFLUX_USER:-}" ]; then
    if [ -z "${INFLUX_PASSWORD:-}" ]; then
        read -r -s -p "Mot de passe InfluxDB de ${INFLUX_USER} : " INFLUX_PASSWORD
        echo
    fi
    export INFLUX_USERNAME="$INFLUX_USER" INFLUX_PASSWORD
fi

influx_exec() { influx -format csv -execute "$1"; }

# Verification de version : 1.x uniquement (la syntaxe InfluxQL/RP/CQ n'existe pas en 2.x)
version="$(influx -version 2>&1 || true)"
echo "Client : $version"
if ! printf '%s' "$version" | grep -Eq 'version:? v?1\.'; then
    echo "ERREUR : version 1.x attendue (InfluxDB 1.8.10 sur ce Pi). Abandon, rien modifie." >&2
    exit 1
fi

# La base doit exister (on n'en cree pas : Iot porte deja d'autres series)
if ! influx_exec "SHOW DATABASES" | grep -Eq "(^|,)${BASE}\$"; then
    echo "ERREUR : la base $BASE n'existe pas." >&2
    exit 1
fi

cree_rp() {  # $1 nom, $2 commande
    if influx_exec "SHOW RETENTION POLICIES ON \"$BASE\"" | grep -Eq "(^|,)$1,"; then
        echo "= RP $1 deja presente : inchangee."
    else
        influx_exec "$2" >/dev/null
        echo "+ RP $1 creee."
    fi
}
cree_rp "$RP_DETAIL" "$CMD_RP_DETAIL"
cree_rp "$RP_HORAIRE" "$CMD_RP_HORAIRE"

if influx_exec "SHOW CONTINUOUS QUERIES" | grep -Eq "(^|,)$CQ,"; then
    echo "= CQ $CQ deja presente : inchangee."
else
    influx_exec "$CMD_CQ" >/dev/null
    echo "+ CQ $CQ creee."
fi

echo "--- Etat final des retention policies de $BASE ---"
influx_exec "SHOW RETENTION POLICIES ON \"$BASE\""
echo "Controle : seule la RP historique par defaut (autogen ou autre) doit avoir default=true."

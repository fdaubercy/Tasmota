#!/bin/sh
# =============================================================================
#  verifie_synchro_fork.sh  -  Hook SessionStart : le fork est-il a jour ?
# =============================================================================
#
#  POURQUOI
#  --------
#  Le retard du fork sur arendst/Tasmota n'est utile qu'au moment ou l'on ouvre
#  le chantier : c'est la qu'on decide de synchroniser avant de builder. Sans ce
#  hook, `upstream/development` affiche en local date du dernier `git fetch`
#  manuel : l'information visible peut etre silencieusement fausse.
#
#  CE QU'IL FAIT — ET CE QU'IL NE FAIT PAS
#  ---------------------------------------
#  Il DETECTE, il ne synchronise pas. Decide le 2026-07-24, apres avoir envisage
#  puis rejete le lancement automatique de synchronise_fork_tasmota.py :
#
#    - un hook a un timeout ; un merge tue en plein vol laisse un MERGE_HEAD et
#      un index a moitie ecrit — exactement l'etat conflictuel a eviter, et cree
#      sans que personne ne regarde l'ecran ;
#    - le script de synchro est ecrit pour un humain devant un terminal (il
#      demande confirmation avant de pousser, ligne 434) : dans un hook,
#      l'entree standard n'est pas un terminal -> EOFError APRES le merge ;
#    - la vraie prevention des conflits, c'est la frequence (petits paquets, sur
#      development propre, avant d'ouvrir un chantier), pas l'automatisme.
#
#  La synchro se lance donc a la main, dans la session, sortie sous les yeux :
#      python outils_docs/scripts_python/synchronise_fork_tasmota.py
#
#  DEROULE
#  -------
#    1. fetch cible d'upstream/development, bride a une fois par 24 h ;
#    2. calcul du retard de la branche `development` du fork sur l'amont ;
#    3. fork a jour  -> ne dit RIEN (pas de bruit au demarrage) ;
#       fork en retard -> une ligne + la commande a lancer.
#
#  INVARIANT : ce hook ne modifie JAMAIS l'arbre de travail (seul `git fetch`
#  ecrit, et uniquement dans refs/remotes/upstream) et ne doit JAMAIS faire
#  echouer un demarrage de session : toute erreur (hors ligne, VPN, amont
#  indisponible) est avalee et le script sort en 0.
# =============================================================================

DEPOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$DEPOT" ] && cd "$DEPOT" 2>/dev/null || exit 0

# Pas de remote upstream (clone frais, autre poste mal configure) -> on se tait.
git remote get-url upstream >/dev/null 2>&1 || exit 0

MARQUE=".claude/.derniere-verif-synchro"   # horodatage du dernier fetch (non suivi)
BRIDAGE=86400                              # 24 h en secondes

# ── 1. Fetch cible, bride a une fois par 24 h ────────────────────────────────
# Bride le FETCH, pas le message : entre deux fetchs, le retard est recalcule
# sur les references locales, donc l'info reste affichee a chaque session.
MAINTENANT=$(date +%s)
DERNIER=0
[ -f "$MARQUE" ] && DERNIER=$(cat "$MARQUE" 2>/dev/null || echo 0)
case "$DERNIER" in *[!0-9]*|"") DERNIER=0 ;; esac

if [ $((MAINTENANT - DERNIER)) -ge "$BRIDAGE" ]; then
    # `timeout` n'est pas garanti partout : on ne l'utilise que s'il existe.
    if command -v timeout >/dev/null 2>&1; then
        timeout 45 git fetch upstream development --quiet >/dev/null 2>&1
    else
        git fetch upstream development --quiet >/dev/null 2>&1
    fi
    [ $? -eq 0 ] && echo "$MAINTENANT" > "$MARQUE" 2>/dev/null
fi

# ── 2. Retard de la branche development du fork sur l'amont ──────────────────
# On mesure sur `development`, PAS sur HEAD : on travaille souvent sur un chantier.
RETARD=$(git rev-list --count development..upstream/development 2>/dev/null)
case "$RETARD" in *[!0-9]*|"") exit 0 ;; esac   # reference absente -> silence
[ "$RETARD" -eq 0 ] && exit 0                   # a jour -> aucun message

# ── 3. Le message, une ligne + la commande ───────────────────────────────────
AMONT=$(git log -1 --format=%ad --date=short upstream/development 2>/dev/null)
BRANCHE=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

echo "fork : $RETARD commit(s) de retard sur upstream/development (dernier amont : $AMONT)"
echo "synchro a lancer a la main, sur development propre, AVANT d'ouvrir un chantier :"
echo "  python outils_docs/scripts_python/synchronise_fork_tasmota.py"
[ "$BRANCHE" != "development" ] && echo "  (branche courante : $BRANCHE — ne pas merger l'amont dedans)"
exit 0

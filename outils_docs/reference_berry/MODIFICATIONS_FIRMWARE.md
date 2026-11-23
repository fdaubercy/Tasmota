# Modifications du firmware amont (C++ en dur)

Ce fork garde le firmware d'`arendst/Tasmota` tel quel, sauf ce qui est listé ici. Chaque ligne modifiée dans un fichier de l'amont est un piège à la synchro du fork : une modification locale et un changement de l'amont sur les mêmes lignes donnent un conflit (voir `CLAUDE.md` § Synchro du fork et `outils_docs/HISTORIQUE_SYNCHRO_FORK.md`). Après chaque synchro, relancer la recherche indiquée et vérifier que la modification est toujours là.

État vérifié le 2026-11-23 par lecture du fichier et comparaison avec `upstream/development`.

## Pied de page de la WebUI

Fichier : `tasmota/tasmota_xdrv_driver/xdrv_01_9_webserver.ino`. Retrouver : `git grep "Au Bonheur des Asturies" tasmota/`.

Deux lignes diffèrent de l'amont, toutes deux autour de la constante `HTTP_END` :

1. La constante `HTTP_END` (pied de page de chaque page). Amont :

   ```
   "...<a href='https://github.com/arendst/Tasmota' target='_blank' style='color:#aaa;'>Tasmota %s %s " D_BY " Theo Arends</a></div>"
   ```

   Fork (un seul `%s` pour la version, plus de nom d'image, signature de l'auteur du fork) :

   ```
   "...<a href='https://github.com/arendst/Tasmota' target='_blank' style='color:#aaa;'>Tasmota %s " D_BY " Au Bonheur des Asturies</a><div>"
   ```

   Le fork se termine par `<div>` là où l'amont écrit `</div>` : balise jamais refermée, sans effet visible, à corriger si la ligne est retouchée.

2. L'appel unique à `HTTP_END`, dans `WSContentStop` (l'ancien texte parlait de « deux appels » : il n'y en a qu'un). Amont : `WSContentSend_P(HTTP_END, TasmotaGlobal.version, TasmotaGlobal.image_name);` ; fork : `WSContentSend_P(HTTP_END, TasmotaGlobal.version);`. Les deux changements vont ensemble : le nombre d'arguments doit correspondre au nombre de `%s` de la constante, sinon l'affichage est faux ou le firmware plante à l'exécution.

Après une synchro, si l'amont a retouché `HTTP_END` ou `WSContentStop`, refaire les deux modifications ensemble.

# Bouchon de ledsFonctions pour banc_cuve.be : enregistre ce que la cuve lui donne (teinte du mode AUTO,
# erreur de niveau, fonction de retour en AUTO). Le vrai module a son propre banc (banc_leds.be).
var ledsFonctions = module("ledsFonctions")
ledsFonctions.teintes = []
ledsFonctions.erreurs = []
ledsFonctions.retours = []
ledsFonctions.appliqueAuto = def (teinte) ledsFonctions.teintes.push(teinte) end
ledsFonctions.signaleErreur = def (source, erreur) ledsFonctions.erreurs.push([source, erreur]) end
ledsFonctions.enregistreRetourAuto = def (fonction, texte) ledsFonctions.retours.push(fonction) end
return ledsFonctions

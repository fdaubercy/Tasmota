// Script de la webview « Suivi du plan » : clics -> extension, mises a jour sans rechargement.
// Charge par nonce (CSP). La largeur des barres est posee ici, par CSSOM (data-pourcent),
// car la CSP interdit les attributs style dans le HTML.
(function () {
  'use strict'
  const vscode = acquireVsCodeApi()
  const contenu = document.getElementById('contenu')

  function largeurs() {
    for (const el of contenu.querySelectorAll('.remplissage[data-pourcent]')) {
      const p = Math.max(0, Math.min(100, Number(el.getAttribute('data-pourcent')) || 0))
      el.style.width = p + '%'
    }
  }

  function memoriseDefilement() {
    const etat = vscode.getState() || {}
    etat.scrollY = window.scrollY
    vscode.setState(etat)
  }

  // Pliage des actions Ax : choix manuel memorise par plan (cle = chemin du plan affiche), sinon une
  // action finie est pliee. Reapplique apres chaque mise a jour, qui remplace tout le HTML.
  function clePlan() {
    const f = contenu.querySelector('.fichier')
    return f ? f.textContent : ''
  }

  function appliquePlis() {
    const etat = vscode.getState() || {}
    const choix = (etat.plis && etat.plis[clePlan()]) || {}
    for (const art of contenu.querySelectorAll('.action[data-id]')) {
      const id = art.getAttribute('data-id')
      const pliee = Object.prototype.hasOwnProperty.call(choix, id) ? choix[id] : art.classList.contains('finie')
      art.classList.toggle('pliee', pliee)
      const bouton = art.querySelector('.plier')
      if (bouton) bouton.setAttribute('aria-expanded', String(!pliee))
    }
  }

  function basculePli(bouton) {
    const art = bouton.closest('.action[data-id]')
    if (!art) return
    const etat = vscode.getState() || {}
    const plis = etat.plis || (etat.plis = {})
    const choix = plis[clePlan()] || (plis[clePlan()] = {})
    choix[art.getAttribute('data-id')] = !art.classList.contains('pliee')
    vscode.setState(etat)
    appliquePlis()
  }

  // Clic ou Entree/Espace sur un element marque -> message a l'extension (sauf le pliage, local)
  function active(cible) {
    const el = cible && cible.closest ? cible.closest('[data-action], [data-ligne]') : null
    if (!el) return false
    if (el.getAttribute('data-action') === 'plier') basculePli(el)
    else if (el.getAttribute('data-action') === 'choisir') vscode.postMessage({ type: 'choisir' })
    else vscode.postMessage({ type: 'ouvrir', ligne: Number(el.getAttribute('data-ligne')) })
    return true
  }

  document.addEventListener('click', function (ev) { active(ev.target) })
  document.addEventListener('keydown', function (ev) {
    if ((ev.key === 'Enter' || ev.key === ' ') && ev.target.matches && ev.target.matches('[role="button"]')) {
      if (active(ev.target)) ev.preventDefault()
    }
  })

  let attente = null
  window.addEventListener('scroll', function () {
    clearTimeout(attente)
    attente = setTimeout(memoriseDefilement, 100)
  })

  window.addEventListener('message', function (ev) {
    const m = ev.data
    if (!m || m.type !== 'maj' || typeof m.html !== 'string') return
    const y = window.scrollY
    contenu.innerHTML = m.html
    largeurs()
    appliquePlis()
    window.scrollTo(0, y)
  })

  largeurs()
  appliquePlis()
  const etat = vscode.getState()
  if (etat && typeof etat.scrollY === 'number') window.scrollTo(0, etat.scrollY)
  vscode.postMessage({ type: 'pret' })
})()

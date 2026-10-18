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

  // Clic ou Entree/Espace sur un element marque -> message a l'extension
  function active(cible) {
    const el = cible && cible.closest ? cible.closest('[data-action], [data-ligne]') : null
    if (!el) return false
    if (el.getAttribute('data-action') === 'choisir') vscode.postMessage({ type: 'choisir' })
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
    window.scrollTo(0, y)
  })

  largeurs()
  const etat = vscode.getState()
  if (etat && typeof etat.scrollY === 'number') window.scrollTo(0, etat.scrollY)
  vscode.postMessage({ type: 'pret' })
})()

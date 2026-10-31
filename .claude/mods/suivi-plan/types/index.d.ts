// Plan montre par le panneau « Suivi du plan » : racine du projet, plan (tasks/plans/x.md) et son mtime ;
// toute relecture qui change l'un des trois redessine le panneau.
export type VuePanneau = { racine: string | null; fichier: string | null; mtimeMs: number }

declare module 'claude-code' {
  interface PluginState {
    'suivi-plan': { vue: Shaped<VuePanneau> }
  }
}

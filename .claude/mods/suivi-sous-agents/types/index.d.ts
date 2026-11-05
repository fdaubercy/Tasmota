export type Tache = { content: string; status: 'pending' | 'in_progress' | 'completed'; activeForm: string }

// Une ligne du journal d'un agent : un outil (avec son detail et son etat) ou une remarque ecrite par l'agent.
export type Action = { id: string; genre: 'outil' | 'remarque'; texte: string; etat: 'cours' | 'ok' | 'erreur' }

export type SousAgent = {
  id: string
  description: string
  type: string
  parent?: string
  debut: number
  fin?: number
  statut: string
  outils: number
  dernierOutil?: string
  taches?: Tache[]
  journal?: Action[]
}

declare module 'claude-code' {
  interface PluginState {
    'suivi-sous-agents': {
      agents: Shaped<SousAgent[]>
      horloge: number
      ferme: boolean
    }
  }
}

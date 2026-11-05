export type Tache = { content: string; status: 'pending' | 'in_progress' | 'completed'; activeForm: string }

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

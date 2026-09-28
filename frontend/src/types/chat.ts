export type Role = 'user' | 'assistant' | 'system'

export interface ChatMessage {
  id: string
  role: Role
  content: string
  createdAt: number
  pending?: boolean
  error?: boolean
}

export interface Conversation {
  id: string
  title: string
  createdAt: number
  updatedAt: number
  messages: ChatMessage[]
}

export interface UserSettings {
  theme: 'light' | 'dark' | 'system'
  compact: boolean
  useRag: boolean
  autoScroll: boolean
  enterToSend: boolean
  reduceMotion: boolean
}

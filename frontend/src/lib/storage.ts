import type { Conversation, UserSettings } from '../types/chat'

const CONVERSATIONS_KEY = 'sirellm.conversations.v1'
const SETTINGS_KEY = 'sirellm.settings.v1'

export const defaultSettings: UserSettings = {
  theme: 'system',
  compact: false,
  useRag: true,
  autoScroll: true,
  enterToSend: true,
  reduceMotion: false,
}

export function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(CONVERSATIONS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function saveConversations(value: Conversation[]) {
  localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(value))
}

export function loadSettings(): UserSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    return raw ? { ...defaultSettings, ...JSON.parse(raw) } : defaultSettings
  } catch {
    return defaultSettings
  }
}

export function saveSettings(value: UserSettings) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(value))
}

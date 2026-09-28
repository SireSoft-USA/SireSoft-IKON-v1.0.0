import type { ChatMessage } from '../types/chat'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export interface StreamChatArgs {
  conversationId: string
  messages: ChatMessage[]
  useRag: boolean
  signal: AbortSignal
  onToken: (token: string) => void
  onMeta?: (meta: Record<string, unknown>) => void
}

export async function streamChat({
  conversationId,
  messages,
  useRag,
  signal,
  onToken,
  onMeta,
}: StreamChatArgs) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      conversation_id: conversationId,
      messages: messages.map(({ role, content }) => ({ role, content })),
      use_rag: useRag,
    }),
    signal,
  })

  if (!response.ok || !response.body) {
    const text = await response.text()
    throw new Error(text || `Request failed with ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.trim()) continue
      const event = JSON.parse(line)
      if (event.type === 'token') onToken(event.content ?? '')
      if (event.type === 'meta') onMeta?.(event)
      if (event.type === 'error') throw new Error(event.message || 'Generation failed')
    }
  }
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE}/api/health`)
  if (!response.ok) return false
  const data = await response.json()
  return data?.status === 'ok'
}

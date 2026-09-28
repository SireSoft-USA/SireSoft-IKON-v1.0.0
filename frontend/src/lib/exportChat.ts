import type { Conversation } from '../types/chat'

export function conversationToMarkdown(conversation: Conversation) {
  const body = conversation.messages
    .map((message) => `## ${message.role === 'user' ? 'You' : 'SireLLM'}\n\n${message.content.trim()}`)
    .join('\n\n---\n\n')

  return `# ${conversation.title}\n\n${body}\n`
}

export function conversationToText(conversation: Conversation) {
  return conversation.messages
    .map((message) => `${message.role === 'user' ? 'You' : 'SireLLM'}:\n${message.content.trim()}`)
    .join('\n\n')
}

function safeName(value: string) {
  const cleaned = value.replace(/[\\/:*?"<>|]/g, '').replace(/\s+/g, ' ').trim()
  return (cleaned || 'sirellm-chat').slice(0, 80)
}

export function downloadConversation(conversation: Conversation, format: 'md' | 'txt' | 'json') {
  const filename = `${safeName(conversation.title)}.${format}`
  const content = format === 'md'
    ? conversationToMarkdown(conversation)
    : format === 'txt'
      ? conversationToText(conversation)
      : JSON.stringify(conversation, null, 2)

  const type = format === 'json' ? 'application/json' : 'text/plain;charset=utf-8'
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

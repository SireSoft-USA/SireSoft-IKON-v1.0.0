import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { streamChat } from '../lib/api'
import { loadConversations, saveConversations } from '../lib/storage'
import type { ChatMessage, Conversation } from '../types/chat'
import { useTheme } from './ThemeContext'

type ChatContextValue = {
  conversations: Conversation[]
  activeConversation: Conversation | null
  activeId: string | null
  isGenerating: boolean
  setActiveId: (id: string) => void
  newChat: () => void
  deleteConversation: (id: string) => void
  renameConversation: (id: string, title: string) => void
  sendMessage: (content: string) => Promise<void>
  stopGenerating: () => void
}

const ChatContext = createContext<ChatContextValue | null>(null)

const uid = () => crypto.randomUUID()

function titleFrom(content: string) {
  const clean = content.replace(/\s+/g, ' ').trim()
  return clean.length > 42 ? `${clean.slice(0, 42)}…` : clean || 'New chat'
}

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const { settings } = useTheme()
  const [conversations, setConversations] = useState<Conversation[]>(() => loadConversations())
  const [activeId, setActiveIdState] = useState<string | null>(() => loadConversations()[0]?.id ?? null)
  const [isGenerating, setIsGenerating] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => saveConversations(conversations), [conversations])

  const activeConversation = conversations.find((c) => c.id === activeId) ?? null

  const setActiveId = useCallback((id: string) => setActiveIdState(id), [])

  const newChat = useCallback(() => {
    setActiveIdState(null)
  }, [])

  const deleteConversation = useCallback((id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id))
    setActiveIdState((current) => (current === id ? null : current))
  }, [])

  const renameConversation = useCallback((id: string, title: string) => {
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title: title.trim() || c.title } : c)))
  }, [])

  const stopGenerating = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setIsGenerating(false)
  }, [])

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isGenerating) return

    const now = Date.now()
    const conversationId = activeId ?? uid()
    const userMessage: ChatMessage = {
      id: uid(),
      role: 'user',
      content: content.trim(),
      createdAt: now,
    }
    const assistantMessage: ChatMessage = {
      id: uid(),
      role: 'assistant',
      content: '',
      createdAt: now + 1,
      pending: true,
    }

    const existing = conversations.find((c) => c.id === conversationId)
    const nextMessages: ChatMessage[] = existing
      ? [...existing.messages, userMessage, assistantMessage]
      : [userMessage, assistantMessage]

    setConversations((prev) => {
      if (existing) {
        return prev.map((c) =>
          c.id === conversationId
            ? { ...c, messages: nextMessages, updatedAt: now }
            : c,
        )
      }

      const created: Conversation = {
        id: conversationId,
        title: titleFrom(content),
        createdAt: now,
        updatedAt: now,
        messages: nextMessages,
      }
      return [created, ...prev]
    })

    setActiveIdState(conversationId)
    setIsGenerating(true)
    const controller = new AbortController()
    abortRef.current = controller

    try {
      await streamChat({
        conversationId,
        messages: nextMessages.filter((m) => m.role !== 'assistant' || !m.pending),
        useRag: settings.useRag,
        signal: controller.signal,
        onToken: (token) => {
          setConversations((prev) =>
            prev.map((c) => {
              if (c.id !== conversationId) return c
              return {
                ...c,
                updatedAt: Date.now(),
                messages: c.messages.map((m) =>
                  m.id === assistantMessage.id
                    ? { ...m, content: m.content + token, pending: true }
                    : m,
                ),
              }
            }),
          )
        },
      })

      setConversations((prev) =>
        prev.map((c) =>
          c.id === conversationId
            ? {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === assistantMessage.id ? { ...m, pending: false } : m,
                ),
              }
            : c,
        ),
      )
    } catch (error) {
      const aborted = error instanceof DOMException && error.name === 'AbortError'
      setConversations((prev) =>
        prev.map((c) =>
          c.id === conversationId
            ? {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === assistantMessage.id
                    ? {
                        ...m,
                        pending: false,
                        error: !aborted,
                        content: m.content || (aborted ? 'Generation stopped.' : 'SireSoft-IKON-v1.0 could not complete this response.'),
                      }
                    : m,
                ),
              }
            : c,
        ),
      )
    } finally {
      if (abortRef.current === controller) abortRef.current = null
      setIsGenerating(false)
    }
  }, [activeId, conversations, isGenerating, settings.useRag])

  const value = useMemo(() => ({
    conversations,
    activeConversation,
    activeId,
    isGenerating,
    setActiveId,
    newChat,
    deleteConversation,
    renameConversation,
    sendMessage,
    stopGenerating,
  }), [conversations, activeConversation, activeId, isGenerating, setActiveId, newChat, deleteConversation, renameConversation, sendMessage, stopGenerating])

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useChat() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChat must be used within ChatProvider')
  return ctx
}

import { useEffect, useRef, useState } from 'react'
import { useChat } from '../context/ChatContext'
import { useTheme } from '../context/ThemeContext'
import { Composer } from './Composer'
import { EmptyState } from './EmptyState'
import { MessageBubble } from './MessageBubble'

export function ChatWindow() {
  const { activeConversation } = useChat()
  const { settings } = useTheme()
  const scrollRef = useRef<HTMLDivElement>(null)
  const [suggestion, setSuggestion] = useState('')

  useEffect(() => {
    if (!settings.autoScroll || !scrollRef.current) return
    scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: settings.reduceMotion ? 'auto' : 'smooth' })
  }, [activeConversation?.messages, settings.autoScroll, settings.reduceMotion])

  return (
    <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
        {!activeConversation || activeConversation.messages.length === 0 ? (
          <EmptyState onSuggestion={setSuggestion} />
        ) : (
          <div className={`mx-auto w-full ${settings.compact ? 'py-2' : 'py-5'}`}>
            {activeConversation.messages.map((message) => <MessageBubble key={message.id} message={message} />)}
          </div>
        )}
      </div>
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-white via-white/90 to-transparent dark:from-[#0f1115] dark:via-[#0f1115]/90" />
      <div className="relative z-10"><Composer initialText={suggestion} /></div>
    </div>
  )
}

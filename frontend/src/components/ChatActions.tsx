import { Check, ChevronDown, Clipboard, Download, FileJson, FileText, Share2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useChat } from '../context/ChatContext'
import { conversationToText, downloadConversation } from '../lib/exportChat'

export function ChatActions() {
  const { activeConversation } = useChat()
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    window.addEventListener('mousedown', close)
    return () => window.removeEventListener('mousedown', close)
  }, [])

  if (!activeConversation || activeConversation.messages.length === 0) return null

  const copyConversation = async () => {
    await navigator.clipboard.writeText(conversationToText(activeConversation))
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1400)
  }

  const shareConversation = async () => {
    const text = conversationToText(activeConversation)
    if (navigator.share) {
      try {
        await navigator.share({ title: activeConversation.title, text })
      } catch {
        // User cancelled the native share sheet.
      }
    } else {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1400)
    }
    setOpen(false)
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        onClick={() => setOpen((value) => !value)}
        className="flex h-9 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 dark:border-white/10 dark:bg-white/[0.035] dark:text-slate-200 dark:hover:bg-white/[0.07]"
        aria-label="Share and export chat"
        aria-expanded={open}
      >
        <Share2 size={16} />
        <span className="hidden sm:inline">Share</span>
        <ChevronDown size={14} className={`hidden transition sm:block ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-11 z-40 w-60 overflow-hidden rounded-2xl border border-slate-200 bg-white p-1.5 shadow-[0_18px_60px_rgba(15,23,42,0.16)] dark:border-white/10 dark:bg-[#1a1d23] dark:shadow-[0_18px_60px_rgba(0,0,0,0.45)]">
          <button onClick={() => void shareConversation()} className="chat-action-item">
            <Share2 size={16} />
            Share conversation
          </button>
          <button onClick={() => void copyConversation()} className="chat-action-item">
            {copied ? <Check size={16} /> : <Clipboard size={16} />}
            {copied ? 'Copied' : 'Copy conversation'}
          </button>
          <div className="my-1 border-t border-slate-100 dark:border-white/[0.07]" />
          <button onClick={() => { downloadConversation(activeConversation, 'md'); setOpen(false) }} className="chat-action-item">
            <FileText size={16} />
            Export Markdown
          </button>
          <button onClick={() => { downloadConversation(activeConversation, 'txt'); setOpen(false) }} className="chat-action-item">
            <Download size={16} />
            Export text
          </button>
          <button onClick={() => { downloadConversation(activeConversation, 'json'); setOpen(false) }} className="chat-action-item">
            <FileJson size={16} />
            Export JSON
          </button>
        </div>
      )}
    </div>
  )
}

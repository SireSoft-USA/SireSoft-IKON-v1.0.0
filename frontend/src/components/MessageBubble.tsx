import { Check, Copy, RotateCcw } from 'lucide-react'
import { useState } from 'react'
import { Logo } from './Logo'
import type { ChatMessage } from '../types/chat'

export function MessageBubble({ message }: { message: ChatMessage }) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const copy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1200)
  }

  return (
    <div className={`group mx-auto flex w-full max-w-3xl gap-3 px-4 py-4 sm:px-6 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center"><Logo size="compact" /></div>
      )}

      <div className={`min-w-0 ${isUser ? 'max-w-[85%] sm:max-w-[72%]' : 'max-w-[calc(100%-44px)] flex-1'}`}>
        <div className={`${isUser ? 'rounded-[22px] rounded-br-md bg-slate-100 px-4 py-2.5 text-slate-900 dark:bg-white/[0.09] dark:text-slate-100' : 'pt-1 text-slate-800 dark:text-slate-100'} whitespace-pre-wrap break-words text-[15px] leading-7`}> 
          {message.content || (message.pending ? <span className="inline-flex items-center gap-1"><span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" /></span> : null)}
          {message.pending && message.content && <span className="ml-1 inline-block h-4 w-[2px] animate-pulse rounded bg-blue-500 align-middle" />}
        </div>
        {!isUser && !message.pending && (
          <div className="mt-2 flex items-center gap-1 opacity-0 transition group-hover:opacity-100">
            <button onClick={copy} className="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-white/[0.07] dark:hover:text-slate-200" title="Copy response">{copied ? <Check size={15} /> : <Copy size={15} />}</button>
            <button className="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-white/[0.07] dark:hover:text-slate-200" title="Regenerate"><RotateCcw size={15} /></button>
          </div>
        )}
        {message.error && <div className="mt-2 text-xs text-red-500">Response generation failed. Check the FastAPI backend.</div>}
      </div>
    </div>
  )
}

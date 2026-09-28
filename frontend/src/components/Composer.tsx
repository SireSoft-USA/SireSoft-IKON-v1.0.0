import { ArrowUp, Paperclip, Square, Waves } from 'lucide-react'
import { KeyboardEvent, useEffect, useRef, useState } from 'react'
import { useChat } from '../context/ChatContext'
import { useTheme } from '../context/ThemeContext'

export function Composer({ initialText = '' }: { initialText?: string }) {
  const { sendMessage, stopGenerating, isGenerating } = useChat()
  const { settings } = useTheme()
  const [text, setText] = useState(initialText)
  const ref = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!ref.current) return
    ref.current.style.height = '0px'
    ref.current.style.height = `${Math.min(ref.current.scrollHeight, 180)}px`
  }, [text])

  useEffect(() => setText(initialText), [initialText])

  const submit = async () => {
    const value = text.trim()
    if (!value || isGenerating) return
    setText('')
    await sendMessage(value)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (!settings.enterToSend) return
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void submit()
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-3 pb-3 sm:px-5 sm:pb-5">
      <div className="rounded-[26px] border border-slate-200 bg-white p-2 shadow-[0_8px_30px_rgba(15,23,42,0.08)] transition focus-within:border-blue-300/80 focus-within:shadow-[0_12px_42px_rgba(20,71,255,0.10)] dark:border-white/10 dark:bg-[#1a1d23] dark:shadow-[0_8px_30px_rgba(0,0,0,0.35)] dark:focus-within:border-blue-400/30">
        <textarea ref={ref} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKeyDown} rows={1} placeholder="Message SireLLM" className="max-h-[180px] min-h-[46px] w-full resize-none bg-transparent px-3 pb-1 pt-3 text-[15px] leading-6 text-slate-900 outline-none placeholder:text-slate-400 dark:text-slate-100" />
        <div className="flex items-center justify-between px-1 pb-1 pt-1">
          <div className="flex items-center gap-1">
            <button className="grid h-9 w-9 place-items-center rounded-full text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.07] dark:hover:text-white" title="Attach file"><Paperclip size={18} /></button>
            <div className={`flex h-8 items-center gap-1.5 rounded-full px-2.5 text-[11px] font-medium ${settings.useRag ? 'bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-300' : 'bg-slate-100 text-slate-500 dark:bg-white/[0.06] dark:text-slate-400'}`}><Waves size={13} />RAG {settings.useRag ? 'on' : 'off'}</div>
          </div>
          {isGenerating ? (
            <button onClick={stopGenerating} className="grid h-10 w-10 place-items-center rounded-full bg-blue-600 text-white shadow-[0_6px_18px_rgba(37,99,235,0.28)] transition hover:bg-blue-700 hover:shadow-[0_8px_22px_rgba(37,99,235,0.34)] active:scale-95" title="Stop generating"><Square size={14} fill="currentColor" /></button>
          ) : (
            <button onClick={() => void submit()} disabled={!text.trim()} className="grid h-10 w-10 place-items-center rounded-full bg-blue-600 text-white shadow-[0_6px_18px_rgba(37,99,235,0.28)] transition enabled:hover:bg-blue-700 enabled:hover:shadow-[0_8px_22px_rgba(37,99,235,0.34)] enabled:active:scale-95 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none dark:disabled:bg-white/10 dark:disabled:text-slate-500" title="Send"><ArrowUp size={19} strokeWidth={2.4} /></button>
          )}
        </div>
      </div>
    </div>
  )
}

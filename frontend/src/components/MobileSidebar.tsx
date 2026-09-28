import { MessageSquare, Plus, Search, Settings, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useChat } from '../context/ChatContext'
import { Logo } from './Logo'

export function MobileSidebar({ open, onClose, onOpenSettings }: { open: boolean; onClose: () => void; onOpenSettings: () => void }) {
  const { conversations, activeId, setActiveId, newChat } = useChat()
  const [query, setQuery] = useState('')
  const filtered = useMemo(() => conversations.filter((chat) => chat.title.toLowerCase().includes(query.toLowerCase())), [conversations, query])

  return (
    <div className={`fixed inset-0 z-40 md:hidden ${open ? 'pointer-events-auto' : 'pointer-events-none'}`}>
      <div onClick={onClose} className={`absolute inset-0 bg-black/35 transition-opacity ${open ? 'opacity-100' : 'opacity-0'}`} />
      <aside className={`absolute left-0 top-0 flex h-full w-[86%] max-w-[330px] flex-col border-r border-slate-200 bg-[#f7f8fa] p-3 shadow-2xl transition-transform duration-300 dark:border-white/10 dark:bg-[#111318] ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex h-14 items-center justify-between px-1">
          <Logo size="sidebar" />
          <button onClick={onClose} className="grid h-9 w-9 place-items-center rounded-lg transition hover:bg-black/5 dark:hover:bg-white/10" aria-label="Close sidebar"><X size={18} /></button>
        </div>

        <button onClick={() => { newChat(); onClose() }} className="mt-3 flex h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium transition hover:bg-black/[0.045] dark:hover:bg-white/[0.065]"><Plus size={18} />New chat</button>

        <div className="mt-2 flex h-10 items-center gap-2.5 rounded-xl bg-black/[0.035] px-3 text-slate-500 dark:bg-white/[0.055] dark:text-slate-400">
          <Search size={16} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search chats" className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400" />
        </div>

        <div className="mt-4 min-h-0 flex-1 overflow-y-auto scrollbar-thin">
          {filtered.map((chat) => (
            <button key={chat.id} onClick={() => { setActiveId(chat.id); onClose() }} className={`mb-0.5 flex h-10 w-full items-center gap-2 rounded-xl px-2.5 text-left text-sm ${activeId === chat.id ? 'bg-blue-50 text-blue-900 dark:bg-blue-500/10 dark:text-blue-100' : 'hover:bg-black/[0.04] dark:hover:bg-white/[0.055]'}`}>
              <MessageSquare size={15} className={activeId === chat.id ? 'text-blue-600 dark:text-blue-300' : ''} />
              <span className="truncate">{chat.title}</span>
            </button>
          ))}
        </div>

        <button onClick={() => { onClose(); onOpenSettings() }} className="mt-3 flex h-11 items-center gap-3 rounded-xl px-3 text-left text-sm transition hover:bg-black/[0.04] dark:hover:bg-white/[0.06]"><Settings size={18} />Settings</button>
      </aside>
    </div>
  )
}

import { useMemo, useRef, useState } from 'react'
import { MessageSquare, MoreHorizontal, PanelLeftClose, Pencil, Plus, Search, Settings, Trash2 } from 'lucide-react'
import { useChat } from '../context/ChatContext'
import type { Conversation } from '../types/chat'
import { Logo } from './Logo'

function bucketLabel(updatedAt: number) {
  const d = new Date(updatedAt)
  const now = new Date()
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const day = 86_400_000
  if (d.getTime() >= startToday) return 'Today'
  if (d.getTime() >= startToday - day) return 'Yesterday'
  if (d.getTime() >= startToday - 7 * day) return 'Previous 7 days'
  return 'Older'
}

function grouped(items: Conversation[]) {
  const groups = new Map<string, Conversation[]>()
  for (const item of items) {
    const key = bucketLabel(item.updatedAt)
    groups.set(key, [...(groups.get(key) ?? []), item])
  }
  return Array.from(groups.entries())
}

export function Sidebar({ onOpenSettings }: { onOpenSettings: () => void }) {
  const { conversations, activeId, setActiveId, newChat, deleteConversation, renameConversation } = useChat()
  const [collapsed, setCollapsed] = useState(false)
  const [query, setQuery] = useState('')
  const [menuId, setMenuId] = useState<string | null>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  const filtered = useMemo(() => conversations.filter((c) => c.title.toLowerCase().includes(query.toLowerCase())), [conversations, query])
  const groups = useMemo(() => grouped(filtered), [filtered])

  const openSearch = () => {
    if (collapsed) {
      setCollapsed(false)
      window.setTimeout(() => searchRef.current?.focus(), 180)
    } else {
      searchRef.current?.focus()
    }
  }

  return (
    <aside className={`relative hidden h-screen flex-col border-r border-slate-200/80 bg-[#f7f8fa] transition-[width] duration-300 dark:border-white/10 dark:bg-[#111318] md:flex ${collapsed ? 'w-[76px]' : 'w-[286px]'}`}>
      <div className={`relative flex h-[76px] shrink-0 items-center ${collapsed ? 'justify-center px-2' : 'justify-between px-4'}`}>
        {collapsed ? (
          <button
            onClick={() => setCollapsed(false)}
            className="group grid h-14 w-14 place-items-center rounded-2xl transition hover:bg-black/[0.045] active:scale-[0.98] dark:hover:bg-white/[0.07]"
            aria-label="Open sidebar"
            title="Open sidebar"
          >
            <Logo size="sidebar" className="h-11 w-11 transition-transform duration-200 group-hover:scale-[1.04]" />
          </button>
        ) : (
          <Logo size="sidebar" />
        )}

        {!collapsed && (
          <button
            onClick={() => setCollapsed(true)}
            className="grid h-9 w-9 place-items-center rounded-xl text-slate-500 transition hover:bg-black/5 hover:text-slate-900 active:scale-95 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-white"
            aria-label="Collapse sidebar"
            title="Close sidebar"
          >
            <PanelLeftClose size={18} />
          </button>
        )}
      </div>

      <div className="space-y-1 px-2.5 pb-3">
        <button
          onClick={newChat}
          className={`flex h-10 w-full items-center rounded-xl text-sm font-medium text-slate-800 transition hover:bg-black/[0.045] dark:text-slate-200 dark:hover:bg-white/[0.065] ${collapsed ? 'justify-center' : 'gap-3 px-3'}`}
          title="New chat"
        >
          <Plus size={18} />
          {!collapsed && 'New chat'}
        </button>
        <button
          onClick={openSearch}
          className={`flex h-10 w-full items-center rounded-xl text-sm font-medium text-slate-700 transition hover:bg-black/[0.045] dark:text-slate-300 dark:hover:bg-white/[0.065] ${collapsed ? 'justify-center' : 'gap-3 px-3'}`}
          title="Search chats"
        >
          <Search size={18} />
          {!collapsed && 'Search chats'}
        </button>
      </div>

      {!collapsed && (
        <div className="px-3 pb-2">
          <div className="flex h-10 items-center gap-2.5 rounded-xl border border-transparent bg-black/[0.035] px-3 text-slate-500 transition focus-within:border-blue-200 focus-within:bg-white dark:bg-white/[0.055] dark:text-slate-400 dark:focus-within:border-blue-400/20 dark:focus-within:bg-white/[0.07]">
            <Search size={15} />
            <input ref={searchRef} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search conversations" className="w-full bg-transparent text-xs outline-none placeholder:text-slate-400" />
          </div>
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto px-2.5 pb-3 scrollbar-thin">
        {collapsed ? (
          <div className="space-y-1 pt-1">
            {filtered.slice(0, 10).map((chat) => (
              <button key={chat.id} onClick={() => setActiveId(chat.id)} title={chat.title} className={`grid h-10 w-full place-items-center rounded-xl transition ${activeId === chat.id ? 'bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-300' : 'text-slate-500 hover:bg-black/[0.04] dark:text-slate-400 dark:hover:bg-white/[0.06]'}`}>
                <MessageSquare size={17} />
              </button>
            ))}
          </div>
        ) : (
          groups.map(([label, chats]) => (
            <section key={label} className="mb-4">
              <div className="px-2 py-2 text-[11px] font-medium text-slate-400">{label}</div>
              <div className="space-y-0.5">
                {chats.map((chat) => (
                  <div key={chat.id} className="group relative">
                    <button onClick={() => setActiveId(chat.id)} className={`flex h-10 w-full items-center gap-2 rounded-xl pl-2.5 pr-8 text-left text-[13px] transition ${activeId === chat.id ? 'bg-blue-50 text-blue-900 dark:bg-blue-500/10 dark:text-blue-100' : 'text-slate-700 hover:bg-black/[0.04] dark:text-slate-300 dark:hover:bg-white/[0.055]'}`}>
                      <MessageSquare size={15} className={`shrink-0 ${activeId === chat.id ? 'text-blue-600 dark:text-blue-300' : 'opacity-70'}`} />
                      <span className="truncate">{chat.title}</span>
                    </button>
                    <button onClick={() => setMenuId(menuId === chat.id ? null : chat.id)} className="absolute right-1.5 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-md text-slate-400 opacity-0 transition hover:bg-black/5 group-hover:opacity-100 dark:hover:bg-white/10" aria-label="Chat options">
                      <MoreHorizontal size={16} />
                    </button>
                    {menuId === chat.id && (
                      <div className="absolute right-1 top-9 z-30 w-36 rounded-xl border border-slate-200 bg-white p-1 shadow-xl dark:border-white/10 dark:bg-[#1b1e24]">
                        <button onClick={() => { const name = window.prompt('Rename chat', chat.title); if (name) renameConversation(chat.id, name); setMenuId(null) }} className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs hover:bg-slate-100 dark:hover:bg-white/[0.07]"><Pencil size={14} /> Rename</button>
                        <button onClick={() => { deleteConversation(chat.id); setMenuId(null) }} className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10"><Trash2 size={14} /> Delete</button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          ))
        )}
      </div>

      <div className="border-t border-slate-200/80 p-3 dark:border-white/10">
        <button onClick={onOpenSettings} className={`flex h-11 w-full items-center rounded-xl text-sm text-slate-700 transition hover:bg-black/[0.04] dark:text-slate-300 dark:hover:bg-white/[0.06] ${collapsed ? 'justify-center' : 'gap-3 px-3'}`}>
          <Settings size={18} />
          {!collapsed && <span className="font-medium">Settings</span>}
        </button>
      </div>
    </aside>
  )
}

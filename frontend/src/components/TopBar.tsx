import { Menu, Moon, Settings, Sun } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'
import { ChatActions } from './ChatActions'
import { Logo } from './Logo'

export function TopBar({ onOpenSettings, onOpenMobileMenu }: { onOpenSettings: () => void; onOpenMobileMenu: () => void }) {
  const { settings, setSettings } = useTheme()
  const systemDark = typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches
  const dark = settings.theme === 'dark' || (settings.theme === 'system' && systemDark)

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200/70 bg-white/85 px-3 backdrop-blur-xl dark:border-white/10 dark:bg-[#0f1115]/85 sm:px-4 md:px-5">
      <div className="flex min-w-0 items-center gap-3">
        <button onClick={onOpenMobileMenu} className="grid h-9 w-9 place-items-center rounded-lg transition hover:bg-slate-100 dark:hover:bg-white/10 md:hidden" aria-label="Open sidebar">
          <Menu size={19} />
        </button>
        <div className="md:hidden"><Logo size="compact" /></div>
        <div className="hidden min-w-0 items-center gap-2 md:flex">
          <span className="truncate text-sm font-semibold tracking-tight">SireLLM</span>
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        <ChatActions />
        <button
          onClick={() => setSettings((s) => ({ ...s, theme: dark ? 'light' : 'dark' }))}
          className="grid h-9 w-9 place-items-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-white"
          aria-label="Toggle theme"
        >
          {dark ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <button onClick={onOpenSettings} className="grid h-9 w-9 place-items-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-white" aria-label="Open settings">
          <Settings size={18} />
        </button>
      </div>
    </header>
  )
}

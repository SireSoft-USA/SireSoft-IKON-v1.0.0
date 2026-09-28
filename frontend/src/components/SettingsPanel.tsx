import { X } from 'lucide-react'
import { useEffect } from 'react'
import { useTheme } from '../context/ThemeContext'

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-[#15181e] ${
        checked ? 'bg-[#1447ff]' : 'bg-slate-300 dark:bg-white/15'
      }`}
    >
      <span
        className={`absolute left-1 top-1 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${
          checked ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  )
}

export function SettingsPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { settings, setSettings } = useTheme()

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const toggles = [
    ['Use RAG', 'useRag'],
    ['Auto-scroll', 'autoScroll'],
    ['Compact messages', 'compact'],
    ['Enter to send', 'enterToSend'],
    ['Reduce motion', 'reduceMotion'],
  ] as const

  return (
    <div className={`fixed inset-0 z-50 transition ${open ? 'pointer-events-auto' : 'pointer-events-none'}`} aria-hidden={!open}>
      <div onClick={onClose} className={`absolute inset-0 bg-black/25 backdrop-blur-[2px] transition-opacity dark:bg-black/50 ${open ? 'opacity-100' : 'opacity-0'}`} />

      <section className={`absolute right-0 top-0 h-full w-full max-w-[410px] border-l border-slate-200 bg-white shadow-2xl transition-transform duration-300 dark:border-white/10 dark:bg-[#15181e] ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex h-16 items-center justify-between border-b border-slate-200/80 px-5 dark:border-white/10">
          <div className="text-sm font-semibold">Settings</div>
          <button onClick={onClose} className="grid h-9 w-9 place-items-center rounded-lg transition hover:bg-slate-100 dark:hover:bg-white/10" aria-label="Close settings">
            <X size={18} />
          </button>
        </div>

        <div className="h-[calc(100%-64px)] overflow-y-auto p-5">
          <section className="mb-8">
            <div className="mb-3 text-xs font-semibold text-slate-500 dark:text-slate-400">Appearance</div>
            <div className="grid grid-cols-3 gap-2">
              {(['light', 'dark', 'system'] as const).map((theme) => (
                <button
                  key={theme}
                  type="button"
                  onClick={() => setSettings((s) => ({ ...s, theme }))}
                  className={`rounded-xl border px-3 py-2.5 text-xs font-medium capitalize transition ${
                    settings.theme === theme
                      ? 'border-[#1447ff] bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-300'
                      : 'border-slate-200 hover:bg-slate-50 dark:border-white/10 dark:hover:bg-white/[0.05]'
                  }`}
                >
                  {theme}
                </button>
              ))}
            </div>
          </section>

          <section>
            <div className="mb-1 text-xs font-semibold text-slate-500 dark:text-slate-400">Chat</div>
            <div className="divide-y divide-slate-100 dark:divide-white/[0.06]">
              {toggles.map(([label, key]) => (
                <div key={key} className="flex min-h-14 items-center justify-between gap-6 py-3">
                  <div className="text-sm font-medium text-slate-800 dark:text-slate-200">{label}</div>
                  <Toggle
                    label={label}
                    checked={Boolean(settings[key])}
                    onChange={(value) => setSettings((s) => ({ ...s, [key]: value }))}
                  />
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>
    </div>
  )
}

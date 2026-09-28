import { BrainCircuit, DatabaseZap, ShieldCheck, Sparkles } from 'lucide-react'
import { Logo } from './Logo'

const suggestions = [
  { icon: DatabaseZap, title: 'Search company knowledge' },
  { icon: BrainCircuit, title: 'Reason through a problem' },
  { icon: ShieldCheck, title: 'Work within guardrails' },
  { icon: Sparkles, title: 'Draft something polished' },
]

export function EmptyState({ onSuggestion }: { onSuggestion: (text: string) => void }) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-5 pb-12 pt-10">
      <div className="mb-9 text-center">
        <div className="relative mx-auto mb-5 flex w-fit items-center justify-center">
          <div className="absolute h-24 w-24 rounded-full bg-blue-500/10 blur-2xl dark:bg-blue-500/15 sm:h-28 sm:w-28" />
          <Logo size="hero" className="relative drop-shadow-[0_10px_24px_rgba(20,71,255,0.18)]" />
        </div>
        <h1 className="text-[27px] font-semibold tracking-[-0.03em] text-slate-950 dark:text-white sm:text-[32px]">How can SireLLM help?</h1>
      </div>

      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {suggestions.map(({ icon: Icon, title }) => (
          <button
            key={title}
            onClick={() => onSuggestion(title)}
            className="group flex min-h-16 items-center gap-3 rounded-2xl border border-slate-200/90 bg-white px-4 py-3 text-left shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-[0_10px_30px_rgba(15,23,42,0.08)] dark:border-white/10 dark:bg-white/[0.025] dark:hover:border-blue-400/20 dark:hover:bg-white/[0.045]"
          >
            <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-700 transition group-hover:bg-blue-50 group-hover:text-blue-700 dark:bg-white/[0.06] dark:text-slate-300 dark:group-hover:bg-blue-500/10 dark:group-hover:text-blue-300">
              <Icon size={16} />
            </div>
            <div className="text-sm font-medium text-slate-900 dark:text-slate-100">{title}</div>
          </button>
        ))}
      </div>
    </div>
  )
}

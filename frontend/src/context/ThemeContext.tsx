import { createContext, useContext, useEffect, useMemo } from 'react'
import type { Dispatch, ReactNode, SetStateAction } from 'react'
import type { UserSettings } from '../types/chat'

type ThemeContextValue = {
  settings: UserSettings
  setSettings: Dispatch<SetStateAction<UserSettings>>
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({
  settings,
  setSettings,
  children,
}: ThemeContextValue & { children: ReactNode }) {
  useEffect(() => {
    const root = document.documentElement
    const media = window.matchMedia('(prefers-color-scheme: dark)')

    const apply = () => {
      const shouldDark = settings.theme === 'dark' || (settings.theme === 'system' && media.matches)
      root.classList.toggle('dark', shouldDark)
      root.style.colorScheme = shouldDark ? 'dark' : 'light'
    }

    apply()
    media.addEventListener('change', apply)
    return () => media.removeEventListener('change', apply)
  }, [settings.theme])

  useEffect(() => {
    document.documentElement.classList.toggle('reduce-motion', settings.reduceMotion)
  }, [settings.reduceMotion])

  const value = useMemo(() => ({ settings, setSettings }), [settings, setSettings])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}

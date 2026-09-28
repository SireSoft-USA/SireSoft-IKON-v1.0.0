import { useEffect, useState } from 'react'
import { ChatProvider } from './context/ChatContext'
import { ThemeProvider } from './context/ThemeContext'
import { loadSettings, saveSettings } from './lib/storage'
import type { UserSettings } from './types/chat'
import { ChatWindow } from './components/ChatWindow'
import { MobileSidebar } from './components/MobileSidebar'
import { SettingsPanel } from './components/SettingsPanel'
import { Sidebar } from './components/Sidebar'
import { TopBar } from './components/TopBar'

export default function App() {
  const [settings, setSettings] = useState<UserSettings>(() => loadSettings())
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => saveSettings(settings), [settings])

  return (
    <ThemeProvider settings={settings} setSettings={setSettings}>
      <ChatProvider>
        <div className="flex h-dvh overflow-hidden bg-white text-slate-900 dark:bg-[#0f1115] dark:text-slate-100">
          <Sidebar onOpenSettings={() => setSettingsOpen(true)} />
          <main className="flex min-w-0 flex-1 flex-col">
            <TopBar onOpenSettings={() => setSettingsOpen(true)} onOpenMobileMenu={() => setMobileOpen(true)} />
            <ChatWindow />
          </main>
          <MobileSidebar open={mobileOpen} onClose={() => setMobileOpen(false)} onOpenSettings={() => setSettingsOpen(true)} />
          <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
        </div>
      </ChatProvider>
    </ThemeProvider>
  )
}

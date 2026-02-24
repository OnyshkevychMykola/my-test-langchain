import { useState } from 'react'
import { AuthProvider, useAuth } from './auth'
import LoginPage from './LoginPage'
import ChatPage from './ChatPage'
import PharmaciesPage from './PharmaciesPage'

type AppTab = 'chat' | 'pharmacies'

function IconChat({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  )
}

function IconMapPin({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  )
}

function AppContent() {
  const { token, loading } = useAuth()
  const [tab, setTab] = useState<AppTab>('chat')

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <span className="w-8 h-8 rounded-full border-2 border-primary-200 border-t-primary-500 animate-spin" aria-hidden />
          <p className="text-slate-500 text-sm">Завантаження...</p>
        </div>
      </div>
    )
  }

  if (!token) {
    return <LoginPage />
  }

  return (
    <div className="flex flex-col h-screen">
      <nav className="shrink-0 bg-white border-b border-slate-200 flex items-center px-4 gap-1 shadow-sm z-10">
        <button
          type="button"
          onClick={() => setTab('chat')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors duration-200 cursor-pointer focus:outline-none ${
            tab === 'chat'
              ? 'border-primary-500 text-primary-600'
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
          }`}
        >
          <IconChat className="w-4 h-4" />
          Асистент
        </button>
        <button
          type="button"
          onClick={() => setTab('pharmacies')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors duration-200 cursor-pointer focus:outline-none ${
            tab === 'pharmacies'
              ? 'border-primary-500 text-primary-600'
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
          }`}
        >
          <IconMapPin className="w-4 h-4" />
          Аптеки поруч
        </button>
      </nav>
      <div className="flex-1 min-h-0">
        {tab === 'chat' ? <ChatPage /> : <PharmaciesPage />}
      </div>
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App

import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth'
import LoginPage from './LoginPage'
import ChatPage from './ChatPage'

function AppContent() {
  const { token, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-base flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 rounded-full border-2 border-white/10 border-t-accent animate-spin" aria-hidden />
          <p className="text-slate-400 text-sm">Завантаження...</p>
        </div>
      </div>
    )
  }

  if (!token) {
    return <LoginPage />
  }

  return (
    <Routes>
      <Route path="/" element={<ChatPage />} />
      <Route path="/:conversationId" element={<ChatPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
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

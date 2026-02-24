import { AuthProvider, useAuth } from './auth'
import LoginPage from './LoginPage'
import ChatPage from './ChatPage'

function AppContent() {
  const { token, loading } = useAuth()

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

  return <ChatPage />
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App

import { AuthProvider, useAuth } from './auth'
import LoginPage from './LoginPage'
import ChatPage from './ChatPage'

function AppContent() {
  const { token, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <p className="text-slate-500">Завантаження...</p>
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

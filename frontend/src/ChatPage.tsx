import { useState, useRef, useEffect, useCallback } from 'react'
import { useAuth } from './auth'

const API_BASE = '/api'

type Mode = 'find' | 'ask'

interface Message {
  role: 'user' | 'assistant'
  content: string
  imagePreview?: string
}

interface Conversation {
  id: number
  title: string
  created_at: string
  updated_at: string
}

export default function ChatPage() {
  const { user, logout, fetchWithAuth } = useAuth()
  const [mode, setMode] = useState<Mode>('ask')
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentId, setCurrentId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [pendingImage, setPendingImage] = useState<{ file: File; preview: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  const loadConversations = useCallback(async () => {
    const res = await fetchWithAuth('/conversations')
    if (res.ok) setConversations(await res.json())
  }, [fetchWithAuth])

  const loadMessages = useCallback(
    async (convId: number) => {
      const res = await fetchWithAuth(`/conversations/${convId}/messages`)
      if (!res.ok) return
      const data = await res.json()
      setMessages((data.messages || []).map((m: { role: string; content: string }) => ({ role: m.role as 'user' | 'assistant', content: m.content })))
    },
    [fetchWithAuth]
  )

  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  useEffect(() => {
    if (currentId !== null) loadMessages(currentId)
    else setMessages([])
  }, [currentId, loadMessages])

  const newChat = async () => {
    const res = await fetchWithAuth('/conversations', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
    if (!res.ok) return
    const c = await res.json()
    setConversations((prev) => [c, ...prev])
    setCurrentId(c.id)
    setMessages([])
  }

  const selectConversation = (id: number) => {
    setCurrentId(id)
  }

  const deleteConversation = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    const res = await fetchWithAuth(`/conversations/${id}`, { method: 'DELETE' })
    if (!res.ok) return
    if (currentId === id) {
      setCurrentId(null)
      setMessages([])
    }
    setConversations((prev) => prev.filter((c) => c.id !== id))
  }

  const sendAsk = async () => {
    const text = input.trim()
    if (!text && mode !== 'find') return
    if (mode === 'find' && !pendingImage) return

    const userContent = mode === 'find' ? (text || 'Що це за препарат?') : text

    setMessages((prev) => [...prev, { role: 'user', content: userContent, ...(pendingImage && { imagePreview: pendingImage.preview }) }])
    setInput('')
    setLoading(true)

    try {
      if (mode === 'find' && pendingImage) {
        const form = new FormData()
        form.append('image', pendingImage.file)
        if (text) form.append('question', text)
        if (currentId != null) form.append('conversation_id', String(currentId))

        const res = await fetchWithAuth('/chat/find', { method: 'POST', body: form })
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()
        if (currentId === null) {
          setCurrentId(data.conversation_id)
          loadConversations()
        } else loadConversations()
        setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
      } else {
        const res = await fetchWithAuth('/chat/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, conversation_id: currentId }),
        })
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()
        if (currentId === null) {
          setCurrentId(data.conversation_id)
          loadConversations()
        } else loadConversations()
        setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
      }
    } catch (e) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `Помилка: ${e instanceof Error ? e.message : String(e)}` }])
    } finally {
      setLoading(false)
      setPendingImage(null)
    }
  }

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !file.type.startsWith('image/')) return
    setPendingImage({ file, preview: URL.createObjectURL(file) })
    e.target.value = ''
  }

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 flex flex-col bg-white border-r border-slate-200 shrink-0">
        <div className="p-3 border-b border-slate-200 flex items-center gap-2">
          <button
            type="button"
            onClick={newChat}
            className="flex-1 py-2 px-3 rounded-lg border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50"
          >
            + Нова розмова
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {conversations.map((c) => (
            <div
              key={c.id}
              role="button"
              tabIndex={0}
              onClick={() => selectConversation(c.id)}
              onKeyDown={(e) => e.key === 'Enter' && selectConversation(c.id)}
              className={`group flex items-center gap-1 w-full text-left px-3 py-2.5 rounded-lg text-sm truncate ${
                currentId === c.id ? 'bg-primary-50 text-primary-700' : 'text-slate-700 hover:bg-slate-100'
              }`}
            >
              <span className="flex-1 truncate">{c.title || 'Без назви'}</span>
              <button
                type="button"
                onClick={(e) => deleteConversation(e, c.id)}
                className="opacity-0 group-hover:opacity-100 p-1 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 shrink-0"
                title="Видалити"
              >
                ×
              </button>
            </div>
          ))}
        </div>
        <div className="p-2 border-t border-slate-200 flex items-center gap-2">
          {user?.avatar_url && <img src={user.avatar_url} alt="" className="w-8 h-8 rounded-full" />}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-800 truncate">{user?.name || user?.email || 'Користувач'}</p>
            <p className="text-xs text-slate-500 truncate">{user?.email}</p>
          </div>
          <button type="button" onClick={logout} className="text-slate-500 hover:text-slate-700 text-sm">
            Вийти
          </button>
        </div>
      </aside>

      {/* Main chat */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="border-b border-slate-200 bg-white shadow-sm shrink-0">
          <div className="max-w-2xl mx-auto px-4 py-3">
            <h1 className="text-lg font-semibold text-slate-800 text-center">Медичний асистент</h1>
            <div className="flex justify-center mt-3 gap-0 rounded-lg bg-slate-100 p-1">
              <button
                type="button"
                onClick={() => setMode('find')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  mode === 'find' ? 'bg-white text-primary-600 shadow' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Find
              </button>
              <button
                type="button"
                onClick={() => setMode('ask')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  mode === 'ask' ? 'bg-white text-primary-600 shadow' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Ask
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto max-w-2xl w-full mx-auto px-4 py-4">
          {messages.length === 0 && (
            <div className="text-center text-slate-500 text-sm py-8">
              {currentId === null
                ? 'Оберіть розмову зліва або створіть нову.'
                : mode === 'find'
                  ? 'Оберіть фото з галереї або зробіть знімок.'
                  : 'Задайте питання про ліки.'}
            </div>
          )}
          <div className="space-y-4">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-primary-500 text-white rounded-br-md'
                      : 'bg-white border border-slate-200 text-slate-800 rounded-bl-md shadow-sm'
                  }`}
                >
                  {msg.imagePreview && (
                    <img src={msg.imagePreview} alt="" className="rounded-lg mb-2 max-h-32 object-cover w-full" />
                  )}
                  <div className="whitespace-pre-wrap break-words">{msg.content}</div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm text-slate-500 text-sm">
                  Думаю...
                </div>
              </div>
            )}
          </div>
        </main>

        <footer className="border-t border-slate-200 bg-white p-4 shrink-0">
          <div className="max-w-2xl mx-auto">
            <input type="file" ref={fileInputRef} accept="image/*" className="hidden" onChange={onFileChange} />
            <input type="file" ref={cameraInputRef} accept="image/*" capture="environment" className="hidden" onChange={onFileChange} />

            {mode === 'find' && (
              <div className="flex gap-2 mb-3">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex-1 py-2.5 px-4 rounded-xl border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50"
                >
                  З галереї
                </button>
                <button
                  type="button"
                  onClick={() => cameraInputRef.current?.click()}
                  className="flex-1 py-2.5 px-4 rounded-xl border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50"
                >
                  Зробити фото
                </button>
              </div>
            )}

            {pendingImage && mode === 'find' && (
              <div className="relative mb-3 inline-block">
                <img src={pendingImage.preview} alt="" className="h-24 rounded-lg object-cover border border-slate-200" />
                <button
                  type="button"
                  onClick={() => setPendingImage(null)}
                  className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-slate-700 text-white text-xs"
                >
                  ×
                </button>
              </div>
            )}

            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendAsk()}
                placeholder={mode === 'ask' ? 'Питання про ліки...' : 'Опишіть питання (необов’язково)'}
                className="flex-1 rounded-xl border border-slate-300 px-4 py-3 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              <button
                type="button"
                onClick={sendAsk}
                disabled={loading || (mode === 'ask' ? !input.trim() : !pendingImage)}
                className="px-5 py-3 rounded-xl bg-primary-500 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary-600"
              >
                Надіслати
              </button>
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}

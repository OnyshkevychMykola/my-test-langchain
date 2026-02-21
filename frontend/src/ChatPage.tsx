import { useState, useRef, useEffect, useCallback } from 'react'
import { useAuth } from './auth'

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

function IconSend({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
    </svg>
  )
}

function IconImage({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  )
}

function IconCamera({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 13v7a2 2 0 01-2 2H7a2 2 0 01-2-2v-7" />
    </svg>
  )
}

function IconPlus({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
    </svg>
  )
}

function IconTrash({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  )
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
    setConversations((prev) => {
      const exists = prev.some((x) => x.id === c.id)
      if (exists) return prev
      return [c, ...prev]
    })
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

  const canSend = mode === 'ask' ? !!input.trim() : !!pendingImage

  return (
    <div className="flex h-screen bg-slate-100">
      {/* Sidebar */}
      <aside className="w-60 flex flex-col bg-white border-r border-slate-200 shrink-0 shadow-sm">
        <div className="p-3 border-b border-slate-100">
          <button
            type="button"
            onClick={newChat}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-slate-100 text-slate-700 text-sm font-medium hover:bg-slate-200 transition-colors"
          >
            <IconPlus className="w-4 h-4" />
            Нова розмова
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 min-h-0">
          {conversations.length === 0 && (
            <p className="text-slate-400 text-xs px-3 py-4 text-center">Поки що немає розмов</p>
          )}
          {conversations.map((c) => (
            <div
              key={c.id}
              role="button"
              tabIndex={0}
              onClick={() => selectConversation(c.id)}
              onKeyDown={(e) => e.key === 'Enter' && selectConversation(c.id)}
              className={`group flex items-center gap-2 w-full text-left px-3 py-2.5 rounded-xl text-sm truncate transition-colors ${
                currentId === c.id ? 'bg-primary-50 text-primary-700' : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <span className="flex-1 truncate">{c.title || 'Без назви'}</span>
              <button
                type="button"
                onClick={(e) => deleteConversation(e, c.id)}
                className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-opacity shrink-0"
                title="Видалити"
              >
                <IconTrash className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
        <div className="p-2 border-t border-slate-100 flex items-center gap-3 bg-slate-50/50">
          {user?.avatar_url && <img src={user.avatar_url} alt="" className="w-9 h-9 rounded-full ring-2 ring-white shadow" />}
          <div className="flex-1 min-w-0">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Аккаунт</p>
            <p className="text-sm font-medium text-slate-800 truncate">{user?.name || user?.email || 'Користувач'}</p>
            <p className="text-xs text-slate-500 truncate">{user?.email}</p>
          </div>
          <button type="button" onClick={logout} className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-200 transition-colors" title="Вийти">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1z" /></svg>
          </button>
        </div>
      </aside>

      {/* Main chat */}
      <div className="flex-1 flex flex-col min-w-0 bg-slate-50">
        <header className="shrink-0 bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-center gap-4 shadow-sm">
          <h1 className="text-base font-semibold text-slate-800">Медичний асистент</h1>
          <label className="flex items-center gap-2 text-slate-600 text-sm">
            <span className="sr-only">Режим</span>
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as Mode)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent cursor-pointer"
            >
              <option value="ask">Ask — питання про ліки</option>
              <option value="find">Find — по фото</option>
            </select>
          </label>
        </header>

        <main className="flex-1 overflow-y-auto max-w-2xl w-full mx-auto px-4 py-6">
          {messages.length === 0 && (
            <div className="text-center text-slate-500 text-sm py-12">
              {currentId === null
                ? 'Оберіть розмову зліва або створіть нову.'
                : mode === 'find'
                  ? 'Додайте фото з галереї або зробіть знімок нижче.'
                  : 'Задайте питання про ліки в полі внизу.'}
            </div>
          )}
          <div className="space-y-4">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-primary-500 text-white rounded-br-md'
                      : 'bg-white border border-slate-200 text-slate-800 rounded-bl-md'
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
                <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm text-slate-500 text-sm flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-primary-400 animate-pulse" />
                  Думаю...
                </div>
              </div>
            )}
          </div>
        </main>

        <footer className="shrink-0 bg-white border-t border-slate-200 p-4 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
          <div className="max-w-2xl mx-auto">
            <input type="file" ref={fileInputRef} accept="image/*" className="hidden" onChange={onFileChange} />
            <input type="file" ref={cameraInputRef} accept="image/*" capture="environment" className="hidden" onChange={onFileChange} />

            {pendingImage && mode === 'find' && (
              <div className="relative mb-3 inline-block">
                <img src={pendingImage.preview} alt="" className="h-20 rounded-xl object-cover border border-slate-200 shadow-inner" />
                <button
                  type="button"
                  onClick={() => setPendingImage(null)}
                  className="absolute -top-1.5 -right-1.5 w-6 h-6 rounded-full bg-slate-700 text-white flex items-center justify-center text-sm hover:bg-slate-800"
                >
                  ×
                </button>
              </div>
            )}

            <div className="flex items-end gap-2">
              {mode === 'find' && (
                <div className="flex items-center gap-1 shrink-0 pb-1">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="p-2.5 rounded-xl text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                    title="З галереї"
                  >
                    <IconImage className="w-5 h-5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => cameraInputRef.current?.click()}
                    className="p-2.5 rounded-xl text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                    title="Зробити фото"
                  >
                    <IconCamera className="w-5 h-5" />
                  </button>
                </div>
              )}
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendAsk()}
                placeholder={mode === 'ask' ? 'Питання про ліки...' : 'Опишіть питання (необов’язково)'}
                className="flex-1 rounded-xl border border-slate-200 px-4 py-3 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-slate-50"
              />
              <button
                type="button"
                onClick={sendAsk}
                disabled={loading || !canSend}
                className="shrink-0 p-3 rounded-xl bg-primary-500 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-primary-600 transition-colors flex items-center justify-center"
                title="Надіслати"
              >
                <IconSend className="w-5 h-5" />
              </button>
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}

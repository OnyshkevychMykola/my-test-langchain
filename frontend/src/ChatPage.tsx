import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Plus, Trash2, Send, Image, Camera, LogOut, Menu, X,
  MessageSquare, Search, MapPin, Pill,
} from 'lucide-react'
import { useAuth } from './auth'
import PharmaciesPage from './PharmaciesPage'

type Mode = 'find' | 'ask' | 'pharmacies'

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

function GlowOrb({ className }: { className?: string }) {
  return (
    <div
      className={`orb pointer-events-none ${className ?? ''}`}
      aria-hidden
    />
  )
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-1 py-0.5" aria-label="Асистент відповідає">
      <span className="w-2 h-2 rounded-full bg-accent dot-1" />
      <span className="w-2 h-2 rounded-full bg-accent dot-2" />
      <span className="w-2 h-2 rounded-full bg-accent dot-3" />
    </div>
  )
}

const MODES: { value: Mode; label: string; icon: React.ReactNode }[] = [
  { value: 'ask',        label: 'Питання',  icon: <MessageSquare className="w-3.5 h-3.5" /> },
  { value: 'find',       label: 'По фото',  icon: <Search className="w-3.5 h-3.5" /> },
  { value: 'pharmacies', label: 'Аптеки',   icon: <MapPin className="w-3.5 h-3.5" /> },
]

function ModeTabs({ mode, onChange }: { mode: Mode; onChange: (m: Mode) => void }) {
  return (
    <div className="flex items-center gap-1 p-1 rounded-xl bg-white/5 border border-white/5">
      {MODES.map((m) => (
        <button
          key={m.value}
          type="button"
          onClick={() => onChange(m.value)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1 focus:ring-offset-surface whitespace-nowrap ${
            mode === m.value
              ? 'bg-accent text-white shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-white/8'
          }`}
        >
          {m.icon}
          {m.label}
        </button>
      ))}
    </div>
  )
}

function WelcomeScreen({ mode, onModeChange, userName }: {
  mode: Mode
  onModeChange: (m: Mode) => void
  userName: string
}) {
  const suggestions: { mode: Mode; title: string; desc: string; icon: React.ReactNode; color: string }[] = [
    {
      mode: 'ask',
      title: 'Питання про ліки',
      desc: 'Дізнайтесь про дозування, показання, протипоказання.',
      icon: <Pill className="w-5 h-5" />,
      color: 'from-sky-500/20 to-cyan-500/10 border-sky-500/20',
    },
    {
      mode: 'find',
      title: 'Визначити препарат',
      desc: 'Надішліть фото упаковки — розпізнаємо препарат.',
      icon: <Search className="w-5 h-5" />,
      color: 'from-violet-500/20 to-purple-500/10 border-violet-500/20',
    },
    {
      mode: 'pharmacies',
      title: 'Аптеки поруч',
      desc: 'Знайдіть найближчу аптеку на карті.',
      icon: <MapPin className="w-5 h-5" />,
      color: 'from-emerald-500/20 to-teal-500/10 border-emerald-500/20',
    },
  ]

  return (
    <div className="flex flex-col items-center justify-center h-full px-4 py-8 text-center animate-fade-in">
      <div className="relative mb-8">
        <GlowOrb className="absolute w-64 h-64 -top-16 left-1/2 -translate-x-1/2" />
        <div
          className="relative w-20 h-20 rounded-3xl mx-auto flex items-center justify-center shadow-accent-glow"
          style={{ background: 'linear-gradient(135deg, #0EA5E9 0%, #06B6D4 100%)' }}
        >
          <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-3-3v6m-7 4h14a2 2 0 002-2V7l-5-5H5a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        </div>
      </div>

      <h2 className="text-2xl font-semibold text-white mb-1">
        Привіт{userName ? `, ${userName}` : ''}!
      </h2>
      <p className="text-slate-400 text-sm mb-8 max-w-xs leading-relaxed">
        Чим можу допомогти сьогодні?
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-xl">
        {suggestions.map((s) => (
          <button
            key={s.mode}
            type="button"
            onClick={() => onModeChange(s.mode)}
            className={`bg-gradient-to-br ${s.color} border rounded-2xl p-4 text-left
                        hover:scale-[1.02] hover:brightness-110
                        transition-all duration-200 cursor-pointer
                        focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-base`}
          >
            <div className="mb-2 text-accent">{s.icon}</div>
            <p className="text-white text-sm font-medium mb-1">{s.title}</p>
            <p className="text-slate-400 text-xs leading-relaxed">{s.desc}</p>
          </button>
        ))}
      </div>

      {mode === 'find' && (
        <p className="mt-6 text-slate-500 text-xs">
          Завантажте фото препарату за допомогою кнопок нижче.
        </p>
      )}
    </div>
  )
}

function SidebarContent({
  user, conversations, currentId, onNewChat, onSelectConversation, onDeleteConversation, onLogout,
}: {
  user: { name?: string; email?: string; avatar_url?: string } | null
  conversations: Conversation[]
  currentId: number | null
  onNewChat: () => void
  onSelectConversation: (id: number) => void
  onDeleteConversation: (e: React.MouseEvent, id: number) => void
  onLogout: () => void
}) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: 'linear-gradient(135deg, #0EA5E9 0%, #06B6D4 100%)' }}
          >
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5} aria-hidden>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-3-3v6m-7 4h14a2 2 0 002-2V7l-5-5H5a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
          </div>
          <span className="text-sm font-semibold text-white">Медасистент</span>
        </div>
      </div>

      <div className="px-3 pt-3 pb-2">
        <button
          type="button"
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl
                     bg-accent/15 border border-accent/25 text-accent text-sm font-medium
                     hover:bg-accent/25 hover:border-accent/40
                     focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1 focus:ring-offset-surface
                     transition-all duration-200 cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          Нова розмова
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-1 min-h-0">
        {conversations.length === 0 && (
          <p className="text-slate-500 text-xs px-3 py-6 text-center">Поки немає розмов</p>
        )}
        {conversations.map((c) => (
          <div
            key={c.id}
            role="button"
            tabIndex={0}
            onClick={() => onSelectConversation(c.id)}
            onKeyDown={(e) => e.key === 'Enter' && onSelectConversation(c.id)}
            className={`group flex items-center gap-2 w-full text-left px-3 py-2.5 rounded-xl text-sm
                        transition-all duration-150 cursor-pointer
                        focus:outline-none focus:ring-2 focus:ring-accent focus:ring-inset
                        ${currentId === c.id
                          ? 'bg-accent/15 border border-accent/25 text-white'
                          : 'text-slate-400 hover:bg-white/6 hover:text-white border border-transparent'
                        }`}
          >
            <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-60" />
            <span className="flex-1 truncate">{c.title || 'Нова розмова'}</span>
            <button
              type="button"
              onClick={(e) => onDeleteConversation(e, c.id)}
              className="opacity-0 group-hover:opacity-100 p-1 rounded-lg text-slate-500
                         hover:text-red-400 hover:bg-red-500/15
                         transition-all duration-150 shrink-0 cursor-pointer
                         focus:outline-none focus:opacity-100 focus:ring-1 focus:ring-red-400"
              title="Видалити"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>

      <div className="p-3 border-t border-white/5">
        <div className="flex items-center gap-2.5 px-1">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" className="w-8 h-8 rounded-full ring-1 ring-white/20 shrink-0" />
          ) : (
            <div className="w-8 h-8 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center shrink-0 text-accent text-xs font-semibold">
              {(user?.name || user?.email || 'U')[0].toUpperCase()}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.name || 'Користувач'}</p>
            <p className="text-xs text-slate-500 truncate">{user?.email}</p>
          </div>
          <button
            type="button"
            onClick={onLogout}
            className="p-1.5 rounded-lg text-slate-500 hover:text-white hover:bg-white/8
                       transition-colors duration-200 cursor-pointer shrink-0
                       focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1 focus:ring-offset-surface"
            title="Вийти"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
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
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => { scrollToBottom() }, [messages, loading])

  const loadConversations = useCallback(async () => {
    const res = await fetchWithAuth('/conversations')
    if (res.ok) setConversations(await res.json())
  }, [fetchWithAuth])

  const loadMessages = useCallback(async (convId: number) => {
    const res = await fetchWithAuth(`/conversations/${convId}/messages`)
    if (!res.ok) return
    const data = await res.json()
    setMessages(
      (data.messages || []).map((m: { role: string; content: string }) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
      }))
    )
  }, [fetchWithAuth])

  useEffect(() => { loadConversations() }, [loadConversations])

  useEffect(() => {
    if (currentId !== null) loadMessages(currentId)
    else setMessages([])
  }, [currentId, loadMessages])

  const handleTextareaInput = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }

  const newChat = async () => {
    const res = await fetchWithAuth('/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    if (!res.ok) return
    const c = await res.json()
    setConversations((prev) => (prev.some((x) => x.id === c.id) ? prev : [c, ...prev]))
    setCurrentId(c.id)
    setMessages([])
    setSidebarOpen(false)
  }

  const selectConversation = (id: number) => {
    setCurrentId(id)
    setSidebarOpen(false)
  }

  const deleteConversation = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    const res = await fetchWithAuth(`/conversations/${id}`, { method: 'DELETE' })
    if (!res.ok) return
    if (currentId === id) { setCurrentId(null); setMessages([]) }
    setConversations((prev) => prev.filter((c) => c.id !== id))
  }

  const sendAsk = async () => {
    const text = input.trim()
    if (mode === 'ask' && !text) return
    if (mode === 'find' && !pendingImage) return

    const userContent = mode === 'find' ? (text || 'Що це за препарат?') : text
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: userContent, ...(pendingImage && { imagePreview: pendingImage.preview }) },
    ])
    setInput('')
    if (textareaRef.current) { textareaRef.current.style.height = 'auto' }
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
        if (currentId === null) { setCurrentId(data.conversation_id); loadConversations() } else loadConversations()
        setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
      } else {
        const res = await fetchWithAuth('/chat/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, conversation_id: currentId }),
        })
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()
        if (currentId === null) { setCurrentId(data.conversation_id); loadConversations() } else loadConversations()
        setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Помилка: ${e instanceof Error ? e.message : String(e)}` },
      ])
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
  const isNewEmptyChat = currentId !== null && messages.length === 0
  const userName = user?.name?.split(' ')[0] || ''

  if (mode === 'pharmacies') {
    return (
      <div className="flex flex-col h-screen bg-base">
        <header className="shrink-0 border-b border-white/5 px-4 py-3 flex items-center gap-3 bg-surface">
          <button
            type="button"
            className="md:hidden p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/8 transition-colors duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent"
            onClick={() => setSidebarOpen(true)}
            aria-label="Відкрити меню"
          >
            <Menu className="w-5 h-5" />
          </button>
          <h1 className="text-sm font-semibold text-white flex-1">Медичний асистент</h1>
          <ModeTabs mode={mode} onChange={setMode} />
        </header>
        <div className="flex-1 min-h-0">
          <PharmaciesPage />
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-base overflow-hidden">
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden animate-fade-in"
          onClick={() => setSidebarOpen(false)}
          aria-hidden
        />
      )}

      <aside
        className={`
          fixed md:relative inset-y-0 left-0 z-50 md:z-auto
          w-64 shrink-0 flex flex-col bg-surface border-r border-white/5
          transform transition-transform duration-250 ease-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        <button
          type="button"
          className="md:hidden absolute top-3 right-3 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/8 transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent"
          onClick={() => setSidebarOpen(false)}
          aria-label="Закрити меню"
        >
          <X className="w-4 h-4" />
        </button>

        <SidebarContent
          user={user}
          conversations={conversations}
          currentId={currentId}
          onNewChat={newChat}
          onSelectConversation={selectConversation}
          onDeleteConversation={deleteConversation}
          onLogout={logout}
        />
      </aside>

      <div className="flex-1 flex flex-col min-w-0 grid-bg">
        <header className="shrink-0 border-b border-white/5 px-4 py-3 flex items-center gap-3 bg-base/80 backdrop-blur-sm">
          <button
            type="button"
            className="md:hidden p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/8 transition-colors duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent"
            onClick={() => setSidebarOpen(true)}
            aria-label="Відкрити меню"
          >
            <Menu className="w-5 h-5" />
          </button>

          <h1 className="text-sm font-semibold text-white hidden sm:block">Медичний асистент</h1>
          <div className="flex-1" />

          <div className="overflow-x-auto">
            <ModeTabs mode={mode} onChange={setMode} />
          </div>

          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" className="w-8 h-8 rounded-full ring-1 ring-white/20 shrink-0 hidden sm:block" />
          ) : (
            <div className="w-8 h-8 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center shrink-0 text-accent text-xs font-semibold hidden sm:block">
              {(user?.name || user?.email || 'U')[0].toUpperCase()}
            </div>
          )}
        </header>

        <main className="flex-1 overflow-y-auto min-h-0">
          <div className="max-w-2xl mx-auto px-4 py-6 flex flex-col gap-4">
            {messages.length === 0 && (
              <WelcomeScreen
                mode={mode}
                onModeChange={setMode}
                userName={isNewEmptyChat ? userName : ''}
              />
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex items-end gap-2 animate-slide-up ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div
                    className="w-7 h-7 rounded-xl shrink-0 flex items-center justify-center mb-0.5"
                    style={{ background: 'linear-gradient(135deg, #0EA5E9, #06B6D4)' }}
                    aria-hidden
                  >
                    <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-3-3v6m-7 4h14a2 2 0 002-2V7l-5-5H5a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                  </div>
                )}

                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'text-white rounded-br-sm'
                      : 'bg-white/6 border border-white/5 text-slate-100 rounded-bl-sm'
                  }`}
                  style={
                    msg.role === 'user'
                      ? { background: 'linear-gradient(135deg, #0EA5E9 0%, #06B6D4 100%)' }
                      : undefined
                  }
                >
                  {msg.imagePreview && (
                    <img
                      src={msg.imagePreview}
                      alt="Завантажене фото"
                      className="rounded-xl mb-2 max-h-40 object-cover w-full"
                    />
                  )}
                  <div className="whitespace-pre-wrap break-words">{msg.content}</div>
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex items-end gap-2 justify-start animate-fade-in">
                <div
                  className="w-7 h-7 rounded-xl shrink-0 flex items-center justify-center"
                  style={{ background: 'linear-gradient(135deg, #0EA5E9, #06B6D4)' }}
                  aria-hidden
                >
                  <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-3-3v6m-7 4h14a2 2 0 002-2V7l-5-5H5a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                </div>
                <div className="bg-white/6 border border-white/5 rounded-2xl rounded-bl-sm px-4 py-3">
                  <TypingDots />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </main>

        <footer className="shrink-0 px-4 pb-4 pt-3 bg-base/80 backdrop-blur-sm">
          <div className="max-w-2xl mx-auto">
            <input type="file" ref={fileInputRef} accept="image/*" className="hidden" onChange={onFileChange} />
            <input type="file" ref={cameraInputRef} accept="image/*" capture="environment" className="hidden" onChange={onFileChange} />

            {pendingImage && mode === 'find' && (
              <div className="relative inline-block mb-3">
                <img
                  src={pendingImage.preview}
                  alt="Попередній перегляд"
                  className="h-20 rounded-xl object-cover border border-white/10"
                />
                <button
                  type="button"
                  onClick={() => setPendingImage(null)}
                  className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-surface border border-white/20
                             text-white flex items-center justify-center
                             hover:bg-surface-3 transition-colors duration-200 cursor-pointer
                             focus:outline-none focus:ring-2 focus:ring-accent"
                  aria-label="Видалити фото"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )}

            <div className="flex items-end gap-2 glass rounded-2xl p-2">
              {mode === 'find' && (
                <div className="flex items-center gap-1 pb-0.5">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="p-2.5 rounded-xl text-slate-400 hover:text-accent hover:bg-accent/10
                               focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1 focus:ring-offset-surface
                               transition-all duration-200 cursor-pointer"
                    title="З галереї"
                    aria-label="Обрати фото з галереї"
                  >
                    <Image className="w-5 h-5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => cameraInputRef.current?.click()}
                    className="p-2.5 rounded-xl text-slate-400 hover:text-accent hover:bg-accent/10
                               focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1 focus:ring-offset-surface
                               transition-all duration-200 cursor-pointer"
                    title="Зробити фото"
                    aria-label="Зробити фото камерою"
                  >
                    <Camera className="w-5 h-5" />
                  </button>
                </div>
              )}

              <textarea
                ref={textareaRef}
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onInput={handleTextareaInput}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendAsk() }
                }}
                placeholder={mode === 'ask' ? 'Питання про ліки...' : `Опишіть питання (необов'язково)`}
                className="flex-1 bg-transparent resize-none text-white placeholder-slate-500 text-sm
                           focus:outline-none py-2 px-2 leading-relaxed"
                style={{ minHeight: '36px', maxHeight: '160px' }}
              />

              <button
                type="button"
                onClick={sendAsk}
                disabled={loading || !canSend}
                className="shrink-0 p-2.5 rounded-xl text-white disabled:opacity-30 disabled:cursor-not-allowed
                           hover:opacity-90 active:scale-95
                           focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-surface
                           transition-all duration-200 cursor-pointer"
                style={{ background: 'linear-gradient(135deg, #0EA5E9 0%, #06B6D4 100%)' }}
                title="Надіслати"
                aria-label="Надіслати повідомлення"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>

            <p className="text-center text-slate-600 text-xs mt-2">
              Не є заміною лікарю — завжди консультуйтесь із фахівцем.
            </p>
          </div>
        </footer>
      </div>
    </div>
  )
}

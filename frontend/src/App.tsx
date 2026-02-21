import { useState, useRef } from 'react'

const API_BASE = '/api'

type Mode = 'find' | 'ask'

interface Message {
  role: 'user' | 'assistant'
  content: string
  imagePreview?: string
}

function App() {
  const [mode, setMode] = useState<Mode>('ask')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [pendingImage, setPendingImage] = useState<{ file: File; preview: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  const history = messages.map((m) => ({ role: m.role, content: m.content }))

  const sendAsk = async () => {
    const text = input.trim()
    if (!text && mode !== 'find') return
    if (mode === 'find' && !pendingImage) return

    const userContent = mode === 'find'
      ? (text || 'Що це за препарат?')
      : text

    setMessages((prev) => [
      ...prev,
      {
        role: 'user',
        content: userContent,
        ...(pendingImage && { imagePreview: pendingImage.preview }),
      },
    ])
    setInput('')
    setLoading(true)

    try {
      if (mode === 'find' && pendingImage) {
        const form = new FormData()
        form.append('image', pendingImage.file)
        if (text) form.append('question', text)
        form.append('history_json', JSON.stringify(history))

        const res = await fetch(`${API_BASE}/chat/find`, {
          method: 'POST',
          body: form,
        })
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()
        setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
      } else {
        const res = await fetch(`${API_BASE}/chat/ask`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            history,
          }),
        })
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()
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
    const preview = URL.createObjectURL(file)
    setPendingImage({ file, preview })
    e.target.value = ''
  }

  const openGallery = () => fileInputRef.current?.click()
  const openCamera = () => cameraInputRef.current?.click()

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-3">
          <h1 className="text-lg font-semibold text-slate-800 text-center">
            Медичний асистент
          </h1>
          <div className="flex justify-center mt-3 gap-0 rounded-lg bg-slate-100 p-1">
            <button
              type="button"
              onClick={() => setMode('find')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                mode === 'find'
                  ? 'bg-white text-primary-600 shadow'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Find
            </button>
            <button
              type="button"
              onClick={() => setMode('ask')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                mode === 'ask'
                  ? 'bg-white text-primary-600 shadow'
                  : 'text-slate-600 hover:text-slate-900'
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
            {mode === 'find'
              ? 'Оберіть фото з галереї або зробіть знімок, щоб дізнатися про препарат.'
              : 'Задайте питання про ліки чи медичну інформацію.'}
          </div>
        )}
        <div className="space-y-4">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                  msg.role === 'user'
                    ? 'bg-primary-500 text-white rounded-br-md'
                    : 'bg-white border border-slate-200 text-slate-800 rounded-bl-md shadow-sm'
                }`}
              >
                {msg.imagePreview && (
                  <img
                    src={msg.imagePreview}
                    alt=""
                    className="rounded-lg mb-2 max-h-32 object-cover w-full"
                  />
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

      <footer className="border-t border-slate-200 bg-white p-4">
        <div className="max-w-2xl mx-auto">
          <input type="file" ref={fileInputRef} accept="image/*" className="hidden" onChange={onFileChange} />
          <input type="file" ref={cameraInputRef} accept="image/*" capture="environment" className="hidden" onChange={onFileChange} />

          {mode === 'find' && (
            <div className="flex gap-2 mb-3">
              <button
                type="button"
                onClick={openGallery}
                className="flex-1 py-2.5 px-4 rounded-xl border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50"
              >
                З галереї
              </button>
              <button
                type="button"
                onClick={openCamera}
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
  )
}

export default App

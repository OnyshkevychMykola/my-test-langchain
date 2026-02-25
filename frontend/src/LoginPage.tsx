import { useAuth } from './auth'

export default function LoginPage() {
  const { login, loading } = useAuth()

  return (
    <div className="min-h-screen bg-base grid-bg flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background orbs */}
      <div className="orb absolute w-[600px] h-[600px] -top-32 left-1/2 -translate-x-1/2 opacity-60" aria-hidden />
      <div
        className="absolute w-96 h-96 bottom-0 right-0 translate-x-1/3 translate-y-1/3 pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(6,182,212,0.15) 0%, transparent 70%)',
          filter: 'blur(60px)',
        }}
        aria-hidden
      />

      {/* Card */}
      <div className="relative w-full max-w-sm glass rounded-2xl p-8 text-center animate-slide-up shadow-card">
        {/* Logo mark */}
        <div className="mx-auto mb-5 w-14 h-14 rounded-2xl flex items-center justify-center"
             style={{ background: 'linear-gradient(135deg, #0EA5E9 0%, #06B6D4 100%)' }}>
          <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.2} aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-3-3v6m-7 4h14a2 2 0 002-2V7l-5-5H5a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        </div>

        <h1 className="text-xl font-semibold text-white mb-2">Медичний асистент</h1>
        <p className="text-slate-400 text-sm mb-8 leading-relaxed">
          Увійдіть, щоб зберігати розмови та&nbsp;продовжувати з&nbsp;будь-якого пристрою.
        </p>

        {loading ? (
          <div className="flex items-center justify-center gap-2 py-3 text-slate-400 text-sm">
            <span className="w-4 h-4 rounded-full border-2 border-white/20 border-t-accent animate-spin" aria-hidden />
            Завантаження...
          </div>
        ) : (
          <button
            type="button"
            onClick={login}
            className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl
                       bg-white/5 border border-white/10 text-white font-medium text-sm
                       hover:bg-white/10 hover:border-white/20
                       focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-surface
                       transition-all duration-200 cursor-pointer"
          >
            <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" aria-hidden>
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Увійти через Google
          </button>
        )}

        <p className="mt-6 text-xs text-slate-500 leading-relaxed">
          Не є заміною лікарю. Завжди консультуйтесь із&nbsp;фахівцем.
        </p>
      </div>
    </div>
  )
}

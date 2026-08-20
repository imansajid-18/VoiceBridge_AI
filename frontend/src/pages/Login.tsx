import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { ShieldCheck, AlertCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    if (!username.trim() || !password) {
      setError('Username and password are required')
      return
    }

    setIsSubmitting(true)
    try {
      const response = await fetch('http://127.0.0.1:8000/api/token/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })

      if (response.status === 401) {
        setError('Incorrect username or password')
        return
      }
      if (!response.ok) {
        setError('Something went wrong. Please try again.')
        return
      }

      const data = await response.json()
      login(data.access, data.refresh)
      navigate('/contacts')
    } catch {
      setError('Could not reach the server. Is it running?')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-stage flex items-center justify-center p-6 text-white relative overflow-hidden">
      <div className="absolute w-[600px] h-[600px] bg-blue/15 rounded-full blur-[140px] -top-32 -left-32 pointer-events-none" />
      <div className="absolute w-[600px] h-[600px] bg-violet/20 rounded-full blur-[140px] -bottom-32 -right-32 pointer-events-none" />

      <div
        className="relative w-full max-w-[420px] rounded-[32px] p-8 sm:p-10 shadow-[0_30px_70px_-15px_rgba(0,0,0,0.8)] border border-white/10 overflow-hidden z-10"
        style={{ background: 'radial-gradient(135% 100% at 50% -10%, var(--color-stage-deep), var(--color-stage) 75%)' }}
      >
        <div className="absolute w-[220px] h-[220px] bg-blue opacity-25 -top-[70px] -right-[70px] rounded-full blur-[60px] pointer-events-none" />
        <div className="absolute w-[240px] h-[240px] bg-violet opacity-20 -bottom-[80px] -left-[80px] rounded-full blur-[60px] pointer-events-none" />

        <div className="relative z-10 flex flex-col items-center">
          <div className="w-[84px] h-[84px] rounded-[26px] bg-gradient-to-b from-blue to-violet flex items-center justify-center mb-5 shadow-[0_14px_35px_rgba(59,130,246,0.55)]">
            <svg className="w-14 h-14 text-white fill-current" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
              <path fillRule="evenodd" clipRule="evenodd" d="M 15 28 H 32 L 41 57 L 48 28 H 72 C 82 28, 87 32, 87 38.5 C 87 43.5, 83 46.5, 77 48 C 84 49.5, 88 54, 88 61 C 88 68.5, 81 72, 70 72 H 27 L 15 28 Z M 52 36 H 67 C 70 36, 72 37.5, 72 40 C 72 42.5, 70 44, 67 44 H 52 Z M 52 52 H 68 C 72 52, 74 53.5, 74 56.5 C 74 59.5, 72 61, 68 61 H 52 Z" />
            </svg>
          </div>

          <h1 className="text-2xl font-extrabold text-white mb-1 tracking-tight text-center">Welcome back</h1>
          <p className="text-sm text-white/50 mb-7 text-center font-medium">Log in to VoiceBridge</p>

          {error && (
            <div className="w-full mb-4 p-3 bg-warn/10 border border-warn/30 rounded-2xl flex items-center gap-2.5 text-warn text-xs">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="w-full space-y-3.5">
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username"
              className="w-full bg-white/10 border border-white/20 rounded-full py-3.5 px-6 text-sm text-white placeholder-white/40 focus:outline-none focus:border-blue transition-all" />
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password"
              className="w-full bg-white/10 border border-white/20 rounded-full py-3.5 px-6 text-sm text-white placeholder-white/40 focus:outline-none focus:border-blue transition-all" />

            <button type="submit" disabled={isSubmitting}
              className="w-full mt-2 bg-gradient-to-r from-blue to-violet text-white rounded-full py-3.5 text-sm font-bold shadow-[0_12px_30px_-5px_rgba(59,130,246,0.55)] active:scale-[0.98] disabled:opacity-50 transition-all cursor-pointer">
              {isSubmitting ? 'Logging in…' : 'Log in'}
            </button>
          </form>

          <div className="w-full flex items-center gap-3 my-5 text-white/40 text-xs">
            <div className="flex-1 h-[1px] bg-white/20" /><span>or</span><div className="flex-1 h-[1px] bg-white/20" />
          </div>

          <Link to="/register" className="w-full text-center bg-white/10 border border-white/20 hover:bg-white/15 text-white rounded-full py-3.5 text-sm font-semibold transition-all active:scale-[0.98]">
            Create an account
          </Link>

          <div className="flex items-center justify-center gap-2 mt-7 text-white/40 text-xs font-medium">
            <ShieldCheck className="w-4 h-4 text-blue shrink-0" />
            <span>Your conversations, always private and secure</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Login
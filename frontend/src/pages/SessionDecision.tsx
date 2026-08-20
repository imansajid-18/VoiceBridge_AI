import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { UserPlus, Trash2 } from 'lucide-react'
import { useApiClient } from '../api/client'

function SessionDecision() {
  const { id } = useParams<{ id: string }>()
  const [mode, setMode] = useState<'choose' | 'naming'>('choose')
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const apiFetch = useApiClient()
  const navigate = useNavigate()

  async function saveAsContact(confirmDuplicate: boolean) {
    if (!name.trim()) {
      setError('Enter a name first')
      return
    }
    setIsSubmitting(true)
    setError(null)
    try {
      const response = await apiFetch(`/sessions/${id}/save-contact/`, {
        method: 'POST',
        body: JSON.stringify({
          name: name.trim(),
          ...(confirmDuplicate ? { confirm_duplicate: true } : {}),
        }),
      })
      if (response.status === 409) {
        const data = await response.json()
        setDuplicateWarning(data.message)
        return
      }
      if (!response.ok) {
        setError('Could not save. Please try again.')
        return
      }
      navigate('/contacts')
    } catch {
      setError('Could not reach the server.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function discard() {
    setIsSubmitting(true)
    try {
      await apiFetch(`/sessions/${id}/discard/`, { method: 'POST' })
      navigate('/contacts')
    } catch {
      setError('Could not reach the server.')
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-stage flex items-center justify-center p-6 text-white">
      <div
        className="relative w-full max-w-sm rounded-[36px] p-8 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.9)] border border-white/10"
        style={{ background: 'radial-gradient(130% 90% at 50% -15%, var(--color-stage-deep), var(--color-stage) 60%)' }}
      >
        <p className="text-white/50 text-sm mb-1">Conversation ended</p>
        <h1 className="text-2xl font-extrabold tracking-tight mb-2">
          {mode === 'choose' ? 'Save this conversation?' : 'Who was that?'}
        </h1>
        {mode === 'choose' && (
          <p className="text-sm text-white/55 mb-6">Nothing is remembered unless you choose to save it.</p>
        )}

        {error && <p className="text-warn text-sm mb-4">{error}</p>}

        {mode === 'choose' ? (
          <div className="space-y-3">
            <button onClick={() => setMode('naming')} className="w-full text-left bg-white/95 rounded-2xl px-5 py-4">
              <span className="flex items-center gap-2.5 text-stage font-bold text-[15px]">
                <UserPlus className="w-[18px] h-[18px]" />
                Save as Contact
              </span>
              <span className="block text-[#6B6480] text-xs mt-1 pl-[27px]">
                Name them, and I'll remember this conversation
              </span>
            </button>

            <button onClick={discard} disabled={isSubmitting} className="w-full text-left bg-white/95 rounded-2xl px-5 py-4 disabled:opacity-50">
              <span className="flex items-center gap-2.5 text-stage font-bold text-[15px]">
                <Trash2 className="w-4 h-4" />
                {isSubmitting ? 'Discarding…' : 'Discard'}
              </span>
              <span className="block text-[#6B6480] text-xs mt-1 pl-[27px]">
                Delete this conversation completely. Nothing is kept.
              </span>
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <input
              autoFocus
              type="text"
              value={name}
              onChange={(e) => { setName(e.target.value); setDuplicateWarning(null) }}
              placeholder="Their name"
              className="w-full bg-white/10 border border-white/15 rounded-full py-3.5 px-6 text-sm placeholder-white/30 focus:outline-none focus:border-blue"
            />
            {duplicateWarning && (
              <div className="bg-amber/10 border border-amber/25 rounded-2xl p-4 text-sm text-white/80">
                <p className="mb-3">{duplicateWarning}</p>
                <button onClick={() => saveAsContact(true)} disabled={isSubmitting} className="text-amber font-bold text-sm">
                  Save anyway →
                </button>
              </div>
            )}
            <button
              onClick={() => saveAsContact(false)}
              disabled={isSubmitting}
              className="w-full bg-gradient-to-r from-blue to-violet text-white font-bold py-4 rounded-full disabled:opacity-50"
            >
              {isSubmitting ? 'Saving…' : 'Save & Remember'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default SessionDecision
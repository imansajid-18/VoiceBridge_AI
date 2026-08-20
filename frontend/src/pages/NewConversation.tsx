import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useApiClient } from '../api/client'

function NewConversation() {
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const apiFetch = useApiClient()
  const navigate = useNavigate()

  async function createContactAndStart(confirmDuplicate: boolean) {
    setIsSubmitting(true)
    setError(null)
    try {
      const contactResponse = await apiFetch('/contacts/', {
        method: 'POST',
        body: JSON.stringify({
          name: name.trim(),
          ...(confirmDuplicate ? { confirm_duplicate: true } : {}),
        }),
      })

      if (contactResponse.status === 409) {
        const data = await contactResponse.json()
        setDuplicateWarning(data.message)
        return
      }
      if (!contactResponse.ok) {
        setError('Could not save that contact. Please try again.')
        return
      }

      const contact = await contactResponse.json()

      const sessionResponse = await apiFetch('/sessions/', {
        method: 'POST',
        body: JSON.stringify({ contact_id: contact.id }),
      })
      if (!sessionResponse.ok) {
        setError('Contact was saved, but the conversation could not start.')
        return
      }
      const session = await sessionResponse.json()

      navigate('/conversation', { state: { sessionId: session.session_id, contactName: contact.name } })
    } catch {
      setError('Could not reach the server. Is it running?')
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setError('Enter a name first')
      return
    }
    setDuplicateWarning(null)
    createContactAndStart(false)
  }

  return (
    <div className="min-h-screen bg-stage flex items-center justify-center p-6 text-white relative overflow-hidden">
      <div className="absolute w-[200px] h-[200px] bg-blue opacity-20 top-[-50px] right-[-50px] rounded-full blur-[55px] pointer-events-none" />
      <div className="absolute w-[220px] h-[220px] bg-violet opacity-15 bottom-[-60px] left-[-60px] rounded-full blur-[60px] pointer-events-none" />

      <div
        className="relative w-full max-w-lg rounded-[36px] p-10 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.9)] border border-white/10 z-10"
        style={{ background: 'radial-gradient(130% 90% at 50% -15%, var(--color-stage-deep), var(--color-stage) 60%)' }}
      >
        <Link to="/contacts" className="flex items-center gap-2 text-xs font-bold text-white/50 hover:text-white mb-6 w-fit">
          <ArrowLeft className="w-4 h-4" />
          Back to contacts
        </Link>

        <h1 className="text-2xl font-extrabold tracking-tight mb-2">Who are you talking to?</h1>
        <p className="text-sm text-white/55 mb-6 leading-relaxed">
          They'll be saved as a contact, and I'll start learning from this conversation.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            value={name}
            onChange={(e) => { setName(e.target.value); setDuplicateWarning(null) }}
            placeholder="Their name"
            autoFocus
            className="w-full bg-white/10 border border-white/15 rounded-full py-4 px-6 text-[15px] text-white placeholder-white/30 focus:outline-none focus:border-blue transition-all"
          />

          {error && <p className="text-warn text-sm">{error}</p>}

          {duplicateWarning && (
            <div className="bg-amber/10 border border-amber/25 rounded-2xl p-4 text-sm text-white/80">
              <p className="mb-3">{duplicateWarning}</p>
              <button
                type="button"
                onClick={() => createContactAndStart(true)}
                disabled={isSubmitting}
                className="text-amber font-bold text-sm hover:underline disabled:opacity-50"
              >
                Save anyway →
              </button>
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-gradient-to-r from-blue to-violet text-white font-bold py-4 rounded-full shadow-[0_12px_30px_-5px_rgba(59,130,246,0.6)] transition-all cursor-pointer disabled:opacity-50"
          >
            {isSubmitting ? 'Starting…' : 'Start conversation'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default NewConversation
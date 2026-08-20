import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import { useApiClient } from '../api/client'
import type { Contact } from '../types/contact'

function DeleteContact() {
  const { id } = useParams<{ id: string }>()
  const [contact, setContact] = useState<Contact | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const apiFetch = useApiClient()
  const navigate = useNavigate()

  useEffect(() => {
    async function loadContact() {
      const response = await apiFetch('/contacts/')
      if (!response.ok) {
        setError('Could not load contact details.')
        return
      }
      const contacts: Contact[] = await response.json()
      const found = contacts.find((c) => c.id === Number(id))
      if (!found) {
        setError('Contact not found.')
        return
      }
      setContact(found)
    }
    loadContact()
  }, [id])

  async function handleDelete() {
    setIsDeleting(true)
    setError(null)
    try {
      const response = await apiFetch(`/contacts/${id}/`, { method: 'DELETE' })
      if (!response.ok) {
        setError('Could not delete this contact. Please try again.')
        return
      }
      navigate('/contacts')
    } catch {
      setError('Could not reach the server.')
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="min-h-screen bg-stage flex items-center justify-center p-6 text-white relative overflow-hidden">
      <div className="absolute w-[200px] h-[200px] bg-blue opacity-20 top-[-50px] right-[-50px] rounded-full blur-[55px] pointer-events-none" />
      <div className="absolute w-[220px] h-[220px] bg-violet opacity-15 bottom-[-60px] left-[-60px] rounded-full blur-[60px] pointer-events-none" />

      <div
        className="relative w-full max-w-md rounded-[36px] p-10 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.9)] border border-white/10 z-10 flex flex-col items-center text-center"
        style={{ background: 'radial-gradient(130% 90% at 50% -15%, var(--color-stage-deep), var(--color-stage) 60%)' }}
      >
        <div className="w-14 h-14 rounded-full bg-warn/10 border border-warn/20 flex items-center justify-center text-warn mb-6">
          <AlertTriangle className="w-6 h-6" />
        </div>

        {!contact && !error && <p className="text-white/50 text-sm mb-6">Loading…</p>}

        {contact && (
          <>
            <h1 className="text-2xl font-extrabold tracking-tight mb-3">Delete {contact.name}?</h1>
            <p className="text-[13.5px] text-white/60 leading-relaxed mb-8 px-2">
              This also removes everything learned about them. Past conversations aren't deleted. They'll just no longer show their name.
            </p>
          </>
        )}

        {error && <p className="text-warn text-sm mb-6">{error}</p>}

        <div className="w-full space-y-3">
          <button
            onClick={handleDelete}
            disabled={!contact || isDeleting}
            className="w-full bg-gradient-to-r from-warn to-warn/80 text-white font-extrabold py-4 rounded-full shadow-[0_12px_30px_-5px_rgba(255,107,107,0.5)] transition-all disabled:opacity-50"
          >
            {isDeleting ? 'Deleting…' : contact ? `Delete ${contact.name}` : 'Delete'}
          </button>
          <button
            onClick={() => navigate('/contacts')}
            className="w-full bg-white/10 border border-white/15 hover:bg-white/15 text-white font-bold py-4 rounded-full transition-all"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

export default DeleteContact
import { useState, useEffect } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { ArrowLeft, X, Trash2 } from 'lucide-react'
import { useApiClient } from '../api/client'
import type { MemoryData } from '../types/memory'

function MemoryViewer() {
  const { contactId } = useParams<{ contactId?: string }>()
  const location = useLocation()
  const passedName = (location.state as { contactName?: string } | null)?.contactName

  const [memory, setMemory] = useState<MemoryData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const apiFetch = useApiClient()
  const navigate = useNavigate()

  async function loadMemory() {
    try {
      const response = await apiFetch('/memory/')
      if (!response.ok) {
        setError('Could not load your memory.')
        return
      }
      setMemory(await response.json())
    } catch {
      setError('Could not reach the server.')
    }
  }

  useEffect(() => { loadMemory() }, [])

  async function deleteFact(id: number) {
    await apiFetch(`/memory/${id}/`, { method: 'DELETE' })
    loadMemory()
  }

  async function forgetContact(id: number) {
    await apiFetch(`/memory/contact/${id}/`, { method: 'DELETE' })
    loadMemory()
  }

  const scopedContact = contactId
    ? memory?.contacts.find((c) => c.contact_id === Number(contactId))
    : null
  const scopedName = scopedContact?.contact_name ?? passedName

  return (
    <div className="min-h-screen bg-stage flex items-center justify-center p-6 text-white">
      <div
        className="relative w-full max-w-lg rounded-[36px] p-10 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.9)] border border-white/10"
        style={{ background: 'radial-gradient(130% 90% at 50% -15%, var(--color-stage-deep), var(--color-stage) 60%)' }}
      >
        <button onClick={() => navigate('/contacts')} className="flex items-center gap-2 text-xs font-bold text-white/50 hover:text-white mb-6">
          <ArrowLeft className="w-4 h-4" />
          Back to contacts
        </button>

        <h1 className="text-2xl font-extrabold tracking-tight mb-1">
          {contactId ? `What I've learned about ${scopedName ?? '…'}` : "What I've learned"}
        </h1>
        <p className="text-sm text-white/55 mb-6">Visible and deletable, always</p>

        {error && <p className="text-warn text-sm mb-4">{error}</p>}
        {!memory && !error && <p className="text-white/40 text-sm">Loading…</p>}

        {memory && contactId && (
          <div className="space-y-4">
            <div className="bg-white/10 border border-white/10 rounded-2xl p-4">
              {(!scopedContact || scopedContact.facts.length === 0) && (
                <p className="text-white/40 text-sm py-1">Nothing learned about {scopedName ?? 'them'} yet.</p>
              )}
              {scopedContact?.facts.map((fact, i) => (
                <div key={fact.id} className={`flex justify-between items-center py-2 ${i > 0 ? 'border-t border-white/10' : ''}`}>
                  <span className="text-sm">{fact.fact}</span>
                  <button onClick={() => deleteFact(fact.id)} className="text-white/40 hover:text-warn p-1">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
            {scopedContact && (
              <button
                onClick={() => forgetContact(scopedContact.contact_id)}
                className="flex items-center justify-center gap-2 w-full bg-coral/10 border border-coral/25 text-coral font-bold text-xs rounded-full py-2.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Forget everything about {scopedContact.contact_name}
              </button>
            )}
          </div>
        )}

        {memory && !contactId && (
          <div className="space-y-4">
            <div className="bg-white/10 border border-white/10 rounded-2xl p-4">
              <p className="text-xs font-extrabold text-blue uppercase tracking-wide mb-2">About you</p>
              {memory.general_facts.length === 0 && (
                <p className="text-white/40 text-sm py-1">Nothing learned yet.</p>
              )}
              {memory.general_facts.map((fact, i) => (
                <div key={fact.id} className={`flex justify-between items-center py-2 ${i > 0 ? 'border-t border-white/10' : ''}`}>
                  <span className="text-sm">{fact.fact}</span>
                  <button onClick={() => deleteFact(fact.id)} className="text-white/40 hover:text-warn p-1">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>

            {memory.contacts.map((contact) => (
              <div key={contact.contact_id} className="bg-white/10 border border-white/10 rounded-2xl p-4">
                <p className="text-xs font-extrabold text-blue uppercase tracking-wide mb-2">{contact.contact_name}</p>
                {contact.facts.map((fact, i) => (
                  <div key={fact.id} className={`flex justify-between items-center py-2 ${i > 0 ? 'border-t border-white/10' : ''}`}>
                    <span className="text-sm">{fact.fact}</span>
                    <button onClick={() => deleteFact(fact.id)} className="text-white/40 hover:text-warn p-1">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  onClick={() => forgetContact(contact.contact_id)}
                  className="flex items-center justify-center gap-2 w-full bg-coral/10 border border-coral/25 text-coral font-bold text-xs rounded-full py-2.5 mt-3"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Forget everything about {contact.contact_name}
                </button>
              </div>
            ))}

            {memory.contacts.length === 0 && memory.general_facts.length === 0 && (
              <p className="text-white/40 text-sm text-center py-4">
                Nothing learned yet — talk to a saved contact and it'll start appearing here.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default MemoryViewer
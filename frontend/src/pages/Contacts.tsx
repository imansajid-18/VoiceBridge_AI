import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, MoreVertical, Plus } from 'lucide-react'
import { useApiClient } from '../api/client'
import type { Contact } from '../types/contact'

const AVATAR_COLORS = ['bg-blue', 'bg-coral', 'bg-violet', 'bg-amber']

function Contacts() {
  const [contacts, setContacts] = useState<Contact[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [openMenuId, setOpenMenuId] = useState<number | null>(null)
  const [startingSessionFor, setStartingSessionFor] = useState<number | 'skip' | null>(null)
  const apiFetch = useApiClient()
  const navigate = useNavigate()

  useEffect(() => {
    async function loadContacts() {
      try {
        const response = await apiFetch('/contacts/')
        if (!response.ok) {
          setError('Could not load your contacts.')
          return
        }
        setContacts(await response.json())
      } catch {
        setError('Could not reach the server. Is it running?')
      }
    }
    loadContacts()
  }, [])

  async function startSession(contactId: number | null, contactName: string | null) {
    setStartingSessionFor(contactId ?? 'skip')
    try {
      const response = await apiFetch('/sessions/', {
        method: 'POST',
        body: JSON.stringify(contactId ? { contact_id: contactId } : {}),
      })
      if (!response.ok) {
        setError('Could not start the conversation.')
        return
      }
      const data = await response.json()
      navigate('/conversation', { state: { sessionId: data.session_id, contactName } })
    } catch {
      setError('Could not reach the server.')
    } finally {
      setStartingSessionFor(null)
    }
  }

  const filteredContacts = contacts?.filter((c) =>
    c.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-stage flex items-center justify-center p-6 text-white relative overflow-hidden">
      <div className="absolute w-[200px] h-[200px] bg-blue opacity-20 top-[-50px] right-[-50px] rounded-full blur-[55px] pointer-events-none" />
      <div className="absolute w-[220px] h-[220px] bg-violet opacity-15 bottom-[-60px] left-[-60px] rounded-full blur-[60px] pointer-events-none" />

      <div
        className="relative w-full max-w-lg rounded-[36px] p-10 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.9)] border border-white/10 z-10"
        style={{ background: 'radial-gradient(130% 90% at 50% -15%, var(--color-stage-deep), var(--color-stage) 60%)' }}
      >
        <h1 className="text-2xl font-extrabold tracking-tight mb-1">Who's this with?</h1>
        <p className="text-sm text-white/55 mb-6">Pick a contact, or start fresh</p>

        <div className="relative mb-6">
          <Search className="w-4 h-4 absolute left-5 top-1/2 -translate-y-1/2 text-white/35" />
          <input
            type="text"
            placeholder="Search contacts…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-white/10 border border-white/10 rounded-full py-3.5 pr-6 pl-12 text-sm text-white placeholder-white/35 focus:outline-none focus:border-blue/60 transition-colors"
          />
        </div>

        {error && <p className="text-warn text-sm text-center mb-4">{error}</p>}
        {contacts === null && !error && (
          <p className="text-white/40 text-sm text-center py-6">Loading your contacts…</p>
        )}
        {contacts !== null && filteredContacts?.length === 0 && (
          <p className="text-white/40 text-sm text-center py-6">No contacts yet.</p>
        )}

          <div className="space-y-3 mb-4 max-h-[320px] overflow-y-auto pr-1">
          {filteredContacts?.map((contact, index) => (
            <div
              key={contact.id}
              className={`relative flex items-center justify-between bg-white/10 border border-white/10 rounded-[20px] p-3 px-4 hover:border-white/20 transition-all cursor-pointer ${
                openMenuId === contact.id ? 'z-30' : 'z-10'
              }`}
              onClick={() => startSession(contact.id, contact.name)}
            >
              <div className="flex items-center gap-3.5">
                <div className={`w-[42px] h-[42px] rounded-full flex items-center justify-center text-white font-black text-sm shrink-0 ${AVATAR_COLORS[index % AVATAR_COLORS.length]}`}>
                  {contact.name.charAt(0).toUpperCase()}
                </div>
                <span className="text-[15px] font-bold text-white">
                  {startingSessionFor === contact.id ? 'Starting…' : contact.name}
                </span>
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setOpenMenuId(openMenuId === contact.id ? null : contact.id)
                }}
                className="text-white/40 hover:text-white p-2 rounded-full hover:bg-white/5"
              >
                <MoreVertical className="w-4 h-4" />
              </button>

              {openMenuId === contact.id && (
                <div
                  className="absolute right-4 top-[54px] bg-[#1F183D] border border-white/15 rounded-[18px] p-2.5 shadow-[0_20px_40px_rgba(0,0,0,0.8)] z-50 w-[180px]"
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    onClick={() => navigate(`/memory/${contact.id}`, { state: { contactName: contact.name } })}
                    className="w-full text-left py-2 px-2.5 text-[13px] font-extrabold text-white rounded-[10px] hover:bg-white/10"
                  >
                    View memory
                  </button>
                  <button
                    onClick={() => navigate(`/contacts/${contact.id}/delete`)}
                    className="w-full text-left py-2 px-2.5 text-[13px] font-extrabold text-warn rounded-[10px] hover:bg-white/10 mt-1"
                  >
                    Delete Contact
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>

        <button
          onClick={() => navigate('/contacts/new')}
          className="flex items-center justify-center gap-2.5 w-full bg-white/5 border-[1.5px] border-dashed border-blue/40 rounded-[20px] py-3.5 text-sm font-bold text-blue hover:bg-blue/10 transition-all my-4"
        >
          <Plus className="w-4 h-4" />
          Start a new conversation
        </button>

        <div className="text-center mt-6">
          <button onClick={() => startSession(null, null)} className="text-[13.5px] text-blue font-bold hover:underline">
            {startingSessionFor === 'skip' ? 'Starting…' : 'Talking to someone new? Skip →'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default Contacts
import { useLocation, useNavigate } from 'react-router-dom'
import { Sparkles } from 'lucide-react'

interface SavedFacts {
  general_facts: string[]
  contact_facts: string[]
}

function SessionSummary() {
  const location = useLocation()
  const state = location.state as { contactName?: string; savedFacts?: SavedFacts } | null
  const navigate = useNavigate()

  const generalFacts = state?.savedFacts?.general_facts ?? []
  const contactFacts = state?.savedFacts?.contact_facts ?? []
  const learnedNothing = generalFacts.length === 0 && contactFacts.length === 0

  return (
    <div className="min-h-screen bg-stage flex items-center justify-center p-6 text-white">
      <div
        className="relative w-full max-w-sm rounded-[36px] p-8 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.9)] border border-white/10 text-center"
        style={{ background: 'radial-gradient(130% 90% at 50% -15%, var(--color-stage-deep), var(--color-stage) 60%)' }}
      >
        <div className="w-14 h-14 rounded-full bg-blue/10 border border-blue/25 flex items-center justify-center text-blue mx-auto mb-5">
          <Sparkles className="w-6 h-6" />
        </div>

        <h1 className="text-2xl font-extrabold tracking-tight mb-1">
          {state?.contactName ? `Saved with ${state.contactName}` : 'Conversation saved'}
        </h1>
        <p className="text-sm text-white/55 mb-6">Here's what I learned this time</p>

        {learnedNothing ? (
          <p className="text-white/40 text-sm py-4">
            Nothing new this time — short exchanges often don't add much.
          </p>
        ) : (
          <div className="space-y-4 text-left mb-6">
            {generalFacts.length > 0 && (
              <div className="bg-white/10 border border-white/10 rounded-2xl p-4">
                <p className="text-xs font-extrabold text-blue uppercase tracking-wide mb-2">About you</p>
                {generalFacts.map((fact, i) => <p key={i} className="text-sm py-1">{fact}</p>)}
              </div>
            )}
            {contactFacts.length > 0 && (
              <div className="bg-white/10 border border-white/10 rounded-2xl p-4">
                <p className="text-xs font-extrabold text-blue uppercase tracking-wide mb-2">
                  About {state?.contactName ?? 'them'}
                </p>
                {contactFacts.map((fact, i) => <p key={i} className="text-sm py-1">{fact}</p>)}
              </div>
            )}
          </div>
        )}

        <button onClick={() => navigate('/contacts')} className="w-full bg-gradient-to-r from-blue to-violet text-white font-bold py-3.5 rounded-full">
          Done
        </button>
      </div>
    </div>
  )
}

export default SessionSummary
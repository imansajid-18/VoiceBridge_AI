import { useState, useRef, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Mic, Send, MoreVertical, Pencil, Check } from 'lucide-react'
import { useApiClient } from '../api/client'

interface SuggestResponse {
  replies: string[]
  setting: string
  fallback: boolean
  suggestion_log_id: number
}

const CLIENT_FALLBACK_REPLIES = ['Yes', 'No', 'Can you repeat that?']
const INACTIVITY_TIMEOUT_MS = 3 * 60 * 1000
const WARNING_WINDOW_MS = 20 * 1000

function WaveIcon() {
  return (
    <div className="flex items-end gap-[3px] h-5 shrink-0">
      {[40, 75, 100, 55, 35].map((h, i) => (
        <span key={i} className="w-[3px] bg-blue rounded-sm" style={{ height: `${h}%` }} />
      ))}
    </div>
  )
}

function Conversation() {
  const location = useLocation()
  const state = location.state as { sessionId?: number; contactName?: string | null } | null
  const apiFetch = useApiClient()
  const navigate = useNavigate()

  const [isListening, setIsListening] = useState(false)
  const [interimText, setInterimText] = useState('')
  const [lastHeard, setLastHeard] = useState<string | null>(null)
  const [speechError, setSpeechError] = useState<string | null>(null)
  const recognitionRef = useRef<AppSpeechRecognition | null>(null)

  const [isThinking, setIsThinking] = useState(false)
  const [originalReplies, setOriginalReplies] = useState<string[]>([])
  const [replies, setReplies] = useState<string[]>([])
  const [setting, setSetting] = useState<string | null>(null)
  const [suggestionLogId, setSuggestionLogId] = useState<number | null>(null)

  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [editDraft, setEditDraft] = useState('')
  const [freeTypeDraft, setFreeTypeDraft] = useState('')

  const [isEnding, setIsEnding] = useState(false)
  const [showInactivityWarning, setShowInactivityWarning] = useState(false)
  const warningTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const endTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  async function handleEndConversation() {
    if (isEnding || !state?.sessionId) return
    setIsEnding(true)
    stopListening()
    if (warningTimerRef.current) clearTimeout(warningTimerRef.current)
    if (endTimerRef.current) clearTimeout(endTimerRef.current)
    setShowInactivityWarning(false)

    try {
      const response = await apiFetch(`/sessions/${state.sessionId}/end/`, { method: 'POST' })
      if (!response.ok) return
      const data = await response.json()
      if (data.status === 'pending_decision') {
        navigate(`/sessions/${state.sessionId}/decide`)
      } else {
        navigate(`/sessions/${state.sessionId}/summary`, {
          state: { contactName: state.contactName, savedFacts: data.saved_facts },
        })
      }
    } finally {
      setIsEnding(false)
    }
  }

  function resetInactivityTimers() {
    if (warningTimerRef.current) clearTimeout(warningTimerRef.current)
    if (endTimerRef.current) clearTimeout(endTimerRef.current)
    setShowInactivityWarning(false)

    warningTimerRef.current = setTimeout(() => {
      setShowInactivityWarning(true)
      endTimerRef.current = setTimeout(() => {
        handleEndConversation()
      }, WARNING_WINDOW_MS)
    }, INACTIVITY_TIMEOUT_MS - WARNING_WINDOW_MS)
  }

  useEffect(() => {
    resetInactivityTimers()
    return () => {
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current)
      if (endTimerRef.current) clearTimeout(endTimerRef.current)
    }
  }, [])

  async function getSuggestions(transcript: string) {
    if (!state?.sessionId) return
    resetInactivityTimers()
    setLastHeard(transcript)
    setIsThinking(true)
    setReplies([])
    setOriginalReplies([])
    setEditingIndex(null)
    setFreeTypeDraft('')

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 6000)

    try {
      const response = await apiFetch(`/sessions/${state.sessionId}/suggest/`, {
        method: 'POST',
        body: JSON.stringify({ transcript }),
        signal: controller.signal,
      })
      clearTimeout(timeoutId)

      if (!response.ok) {
        setReplies(CLIENT_FALLBACK_REPLIES)
        setOriginalReplies(CLIENT_FALLBACK_REPLIES)
        setSetting(null)
        return
      }
      const data: SuggestResponse = await response.json()
      setReplies(data.replies)
      setOriginalReplies(data.replies)
      setSetting(data.setting)
      setSuggestionLogId(data.suggestion_log_id)
    } catch {
      setReplies(CLIENT_FALLBACK_REPLIES)
      setOriginalReplies(CLIENT_FALLBACK_REPLIES)
      setSetting(null)
    } finally {
      setIsThinking(false)
    }
  }

  useEffect(() => {
    const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognitionClass) {
      setSpeechError('This browser does not support live speech recognition. Try Chrome.')
      return
    }
    const recognition = new SpeechRecognitionClass()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onresult = (event) => {
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          getSuggestions(result[0].transcript.trim())
        } else {
          interim += result[0].transcript
        }
      }
      setInterimText(interim)
    }
    recognition.onerror = (event) => {
      setSpeechError(
        event.error === 'not-allowed'
          ? 'Microphone access was denied. Check your browser permissions.'
          : `Speech recognition error: ${event.error}`
      )
      setIsListening(false)
    }
    recognition.onend = () => setIsListening(false)

    recognitionRef.current = recognition
    return () => recognition.stop()
  }, [])

  function startListening() {
    resetInactivityTimers()
    setSpeechError(null)
    setInterimText('')
    recognitionRef.current?.start()
    setIsListening(true)
  }

  function stopListening() {
    recognitionRef.current?.stop()
    setIsListening(false)
  }

  async function speakAndSelect(text: string, isCustom: boolean) {
    if (!text.trim() || !suggestionLogId || !state?.sessionId) return
    resetInactivityTimers()

    window.speechSynthesis.speak(new SpeechSynthesisUtterance(text))

    await apiFetch(`/sessions/${state.sessionId}/select/`, {
      method: 'POST',
      body: JSON.stringify({
        suggestion_log_id: suggestionLogId,
        selected: text,
        ...(isCustom ? { is_custom: true } : {}),
      }),
    })

    setReplies([])
    setOriginalReplies([])
    setFreeTypeDraft('')
    setEditingIndex(null)
  }

  function tapReply(index: number) {
    const text = replies[index]
    const isCustom = text !== originalReplies[index]
    speakAndSelect(text, isCustom)
  }

  function startEditing(index: number) {
    setEditingIndex(index)
    setEditDraft(replies[index])
  }

  function saveEdit(index: number) {
    const trimmed = editDraft.trim()
    if (!trimmed) return
    setReplies((prev) => {
      const next = [...prev]
      next[index] = trimmed
      return next
    })
    setEditingIndex(null)
  }

  return (
    <div className="min-h-screen bg-stage flex items-center justify-center p-6 text-white">
      <div
        className="relative w-full max-w-sm rounded-[36px] p-8 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.9)] border border-white/10"
        style={{ background: 'radial-gradient(130% 90% at 50% -15%, var(--color-stage-deep), var(--color-stage) 60%)' }}
      >
        <div className="flex justify-between items-center mb-3">
          <span className="text-white/55 text-sm">Partner said</span>
          <MoreVertical className="w-4 h-4 text-white/40" />
        </div>

        {speechError && <p className="text-warn text-sm mb-3">{speechError}</p>}

        {lastHeard && (
          <div className="flex items-center gap-3 bg-coral/10 border border-coral/25 rounded-2xl px-4 py-3.5 mb-4">
            <WaveIcon />
            <p className="text-sm">"{lastHeard}"</p>
          </div>
        )}
        {interimText && <p className="text-white/40 italic text-sm px-1 mb-3">{interimText}…</p>}

        {setting && (
          <div className="flex items-center gap-2 w-fit text-xs text-white/55 bg-white/8 px-3 py-1.5 rounded-full mb-3.5">
            <span className="w-[5px] h-[5px] rounded-full bg-blue" />
            {setting}
          </div>
        )}

        {isThinking && <p className="text-white/50 text-sm mb-3">Thinking…</p>}

        <div className="space-y-2.5 mb-4">
          {replies.map((reply, i) =>
            editingIndex === i ? (
              <div key={i} className="w-full flex items-center gap-2 bg-white/95 rounded-2xl px-4 py-2.5">
                <input
                  autoFocus
                  value={editDraft}
                  onChange={(e) => setEditDraft(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') saveEdit(i) }}
                  className="flex-1 bg-transparent text-stage font-bold text-[15px] focus:outline-none"
                />
                <button onClick={() => saveEdit(i)} className="text-blue shrink-0 p-1">
                  <Check className="w-5 h-5" />
                </button>
              </div>
            ) : (
              <div key={i} className="w-full flex items-center gap-2 bg-white/95 rounded-2xl px-4 py-3.5">
                <button onClick={() => tapReply(i)} className="flex-1 flex items-center gap-3 text-left">
                  <WaveIcon />
                  <span className="text-stage font-bold text-[15px]">{reply}</span>
                </button>
                <button onClick={() => startEditing(i)} className="text-stage/35 shrink-0 p-1">
                  <Pencil className="w-4 h-4" />
                </button>
              </div>
            )
          )}
        </div>

        <div className="flex items-center gap-2 mb-5">
          <input
            type="text"
            value={freeTypeDraft}
            onChange={(e) => setFreeTypeDraft(e.target.value)}
            placeholder="Type or edit a reply…"
            className="flex-1 bg-white/10 border border-white/15 rounded-full px-4 py-2.5 text-sm placeholder-white/35 focus:outline-none focus:border-blue"
          />
          <button
            onClick={() => speakAndSelect(freeTypeDraft, true)}
            disabled={!freeTypeDraft.trim()}
            className="bg-blue disabled:opacity-30 rounded-full p-2.5"
          >
            <Send className="w-4 h-4 text-white" />
          </button>
        </div>

        {showInactivityWarning && (
          <div className="bg-amber/10 border border-amber/25 rounded-2xl p-4 mb-4 text-center">
            <p className="text-sm text-white/80 mb-3">Still there? Ending soon due to inactivity.</p>
            <button
              onClick={resetInactivityTimers}
              className="bg-amber/20 text-amber font-bold text-sm rounded-full px-5 py-2"
            >
              I'm still here
            </button>
          </div>
        )}

        <div className="flex items-center justify-center gap-3.5 mb-4">
          <div className="flex items-center gap-1">
            {[0.15, 0.3, 0.55, 0.8].map((o, i) => <span key={i} className="w-1 h-1 rounded-full bg-blue" style={{ opacity: o }} />)}
          </div>
          <button
            onClick={isListening ? stopListening : startListening}
            className="mic-glow w-[66px] h-[66px] rounded-full bg-white flex items-center justify-center shrink-0"
          >
            <Mic className={`w-6 h-6 ${isListening ? 'text-warn' : 'text-stage'}`} />
          </button>
          <div className="flex items-center gap-1">
            {[0.8, 0.55, 0.3, 0.15].map((o, i) => <span key={i} className="w-1 h-1 rounded-full bg-blue" style={{ opacity: o }} />)}
          </div>
        </div>

        <button
          onClick={handleEndConversation}
          disabled={isEnding}
          className="block mx-auto bg-white/8 border border-white/15 rounded-full px-5 py-2.5 text-xs font-semibold text-white/70 disabled:opacity-40"
        >
          {isEnding ? 'Ending…' : 'End conversation'}
        </button>
      </div>
    </div>
  )
}

export default Conversation
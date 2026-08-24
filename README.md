# 🎙️ VoiceBridge

VoiceBridge is a context-aware AAC (Augmentative and Alternative Communication)
assistant that helps users participate in live spoken conversations by turning
incoming speech into fast, natural, personalized reply options.

Built for the **Arbisoft AI-Focused Internship Program 2026** — Web Track, Phase 3.

VoiceBridge is not a chatbot. It is a real-time communication aid: the other
person speaks, VoiceBridge transcribes the conversation, an AI agent decides
whether personalization would help, and the user receives three short replies
that can be spoken, edited, or replaced with their own words — all before the
conversation moves on.

---

## ✨ Key Features

- **Live conversation loop** — Browser Speech Recognition transcribes incoming
  speech, the suggestion agent generates three short replies, and the user can
  tap, edit, or replace a response before speaking it.
- **Context-aware suggestions** — a two-step Groq agent decides whether
  `lookup_profile` would help and uses trusted profile data when relevant.
- **Long-term memory** — a separate Gemini Memory Agent extracts durable
  user-specific and contact-specific facts after conversations, aware of what's
  already been saved so it doesn't re-extract the same fact reworded.
- **Consent-gated stranger memory** — stranger conversations are never sent to
  the Memory Agent until the user explicitly chooses **Save as Contact**.
  **Discard** deletes the conversation without extracting any memories.
- **Memory Viewer** — view general memories, inspect contact-specific memories,
  delete individual entries, or forget everything tied to a contact (or to
  yourself) in one action.
- **Multi-turn context** — recent conversation history is included in
  suggestion requests so replies remain coherent across multiple turns.
- **JWT authentication** — protected API endpoints use JWT access tokens with
  automatic refresh-token support.
- **Inactivity handling** — the app warns and ends inactive conversations
  automatically, keeping the flow moving without leaving a session open forever.

---

## 🏗️ Architecture & Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS v4 |
| Backend | Django 6.1 + Django REST Framework |
| Authentication | JWT via `djangorestframework-simplejwt` |
| Database | PostgreSQL |
| Live suggestion model | Groq — `openai/gpt-oss-20b` |
| Memory model | Google Gemini — `gemini-3.6-flash`, falling back to `gemini-3.5-flash-lite` |
| Speech I/O | Browser Web Speech API (`SpeechRecognition` + `SpeechSynthesis`) |

**Why two AI providers?** The two models have deliberately different
responsibilities. Groq handles the live suggestion path, where low latency
matters because the user is actively mid-conversation. Gemini runs after a
conversation ends to extract durable memories, where a slower, more careful
request is the right trade.

---

## 🤖 AI / Agentic Design

### 1. Suggestion Agent

The suggestion flow uses two separate model calls, so tool-calling and
structured-output instructions each get their own clean request:

```
User speaks
    ↓
CALL 1 — decision only
  tools = [lookup_profile], tool_choice = "auto"
    ↓
Did the model call lookup_profile?
    ├── Yes → lookup_profile(user_id, contact_id) — both server-trusted,
    │         never taken from model-generated tool arguments
    └── No  → continue without profile context
    ↓
CALL 2 — reply generation only
  response_format = JSON schema
    ↓
{"replies": ["...", "...", "..."], "setting": "general"}
```

The schema uses `strict: False` paired with a forgiving repair layer in the
view: if the model returns 3 good replies but an unexpected `setting` value,
the app fills in a sensible default rather than discarding a perfectly usable
response.

**Reliability layers:**
- Retry at a lower temperature on a `BadRequestError` — Groq's own documented
  mitigation for occasional tool-call/JSON confusion on this model family.
- `reasoning_format="hidden"` and `tool_choice="none"` on the reply call, to
  keep the model's internal reasoning out of the final answer.
- Schema validation at the agent layer, plus repair logic in the view layer.
- Generic, always-safe fallback replies (`Yes` / `No` / `Can you repeat that?`)
  if both attempts don't come back usable — the screen is never empty.

### 2. Memory Agent

Runs once, after a conversation ends, extracting two categories of durable
information:
- **General facts** — true about the user regardless of who they're talking
  to: preferences, habits, circumstances, communication style.
- **Contact facts** — specific to that contact, or to the relationship/shared
  context between the user and them.

Previously stored memories are included as context, so the agent avoids
re-extracting information that's already known — including a simple paraphrase
of an existing fact, not just an exact repeat.

**Consent flow:**
```
Known contact                      Stranger
    ↓                                  ↓
End conversation                  End conversation
    ↓                                  ↓
Memory Agent runs               Save as Contact / Discard
    ↓                             ├── Save → create contact
Save memories                     │          → Memory Agent → save
                                   └── Discard → delete session
                                              and related data
                                              → no extraction, ever
```

---

## 🔌 API Overview

**Authentication**
```
POST /api/register/
POST /api/token/
POST /api/token/refresh/
```

**Contacts**
```
GET    /api/contacts/
POST   /api/contacts/
DELETE /api/contacts/<contact_id>/
```

**Sessions & conversation**
```
POST /api/sessions/
POST /api/sessions/<session_id>/suggest/
POST /api/sessions/<session_id>/select/
POST /api/sessions/<session_id>/end/
POST /api/sessions/<session_id>/save-contact/
POST /api/sessions/<session_id>/discard/
```

**Memory**
```
GET    /api/memory/
DELETE /api/memory/<entry_id>/
DELETE /api/memory/contact/<contact_id>/
DELETE /api/memory/general/
```

All protected endpoints enforce ownership through the authenticated user —
users cannot access another user's sessions, contacts, or memories by
guessing IDs.

---

## 🚀 Setup

### 📋 Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL running locally
- A free [Groq API key](https://console.groq.com) and a free
  [Gemini API key](https://ai.google.dev)

### 🐍 Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

Create `backend/.env`:
```
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=voicebridge
DB_USER=your_postgres_user
DB_PASSWORD=your_postgres_password
DB_HOST=127.0.0.1
DB_PORT=5432

GROQ_API_KEY=your-groq-key
GEMINI_API_KEY=your-gemini-key
```

Generate a real secret key rather than leaving that line as-is:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### ⚛️ Frontend

In a second terminal:
```bash
cd frontend
npm install
```

Create `frontend/.env`:
```
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

```bash
npm run dev
```

Django runs on `http://127.0.0.1:8000`, Vite on `http://localhost:5173`.
Both need to be running for the app to work.

---

## 🎯 Usage

1. **Register** or **log in**.
2. Choose a saved contact, tap **Start a new conversation** to name someone on
   the spot, or **Skip** for a stranger.
3. Allow microphone access and speak naturally — the other person's speech is
   transcribed live.
4. Three reply suggestions appear once they finish a sentence. **Tap** one to
   speak it, tap the **pencil** to edit before speaking, or type your own.
5. **End the conversation** when finished.
   - Known contact → memories extracted and saved automatically.
   - Stranger → choose **Save as Contact** or **Discard** first.
6. Open the **Memory Viewer** any time to inspect and delete stored memories.

---

## 🧪 Testing

The backend test suite in `core/tests.py` is organized into three labeled
tiers, matching the program's testing requirement directly:

- **Unit tests** — individual functions in isolation.
- **Integration tests** — one real endpoint at a time, through Django's actual
  routing and database, with Groq/Gemini mocked.
- **End-to-end tests** — several real endpoints chained in one continuous
  session, covering both the known-contact and stranger-consent pipelines.

```bash
python manage.py test
```
48 tests. Coverage:
```bash
coverage run manage.py test
coverage report
```
~87% overall — above the Phase 3 target of 70%.

**Live API tests** genuinely call Groq and Gemini, run separately from the main
suite to protect free-tier quota:
```bash
python manage.py test core.live_api_tests
```

---

## 📁 Project Structure

```
voicebridge/
├── backend/
│   ├── config/
│   │   ├── settings.py
│   │   └── urls.py
│   └── core/
│       ├── models.py         # Contact, ConversationSession, Message,
│       │                       SuggestionLog, MemoryEntry
│       ├── views.py          # All API endpoints
│       ├── agent.py          # Suggestion agent (Groq, two-call design)
│       ├── memory_agent.py   # Memory extraction agent (Gemini)
│       ├── tools.py          # lookup_profile — the one tool the agent can call
│       ├── tests.py          # Unit + integration + E2E tests
│       └── live_api_tests.py # Real-API verification, run manually
└── frontend/
    └── src/
        ├── pages/
        ├── components/
        ├── context/
        └── api/
```

---

## 🔒 Security & Privacy

- JWT authentication with object-level ownership checks across every session,
  contact, and memory entry.
- The stranger flow is intentionally consent-gated: no memory extraction
  happens merely because a stranger conversation ends. Choosing **Discard**
  deletes the conversation without ever sending it to the Memory Agent.
- Memory entries are visible and deletable by their authenticated owner only.
- Forgetting a contact's memory doesn't touch the user's own general
  communication-style memories — they're stored and cleared independently.

---

## 🙏 Acknowledgments

Built as part of Arbisoft's **Internship Program 2026** (Web Track,
Phase 3). Developed with AI-assisted coding throughout — every significant
prompt, decision, and correction is logged in `prompts.md`, per the program's
own AI-coding-discipline requirement.

## 👤 Author

**Iman Sajid**

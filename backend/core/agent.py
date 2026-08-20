import os
import json
import groq
from groq import Groq
from .tools import lookup_profile

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_profile",
            "description": (
                "Get known facts about the current user's speaking style "
                "and, if talking to a saved contact, facts about that contact."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    }
]

DECISION_SYSTEM_PROMPT = (
    "You help an AAC user reply quickly in a live spoken conversation. Your ONLY job "
    "right now is to decide one thing: would looking up saved facts about this contact "
    "help you personalize a reply? If yes, call lookup_profile. If no, do not call any "
    "tool - just respond with the single word: none. Do not write a reply here."
)

REPLY_SYSTEM_PROMPT = (
    "You help an AAC user reply quickly in a real, live spoken conversation. "
    "The replies will be spoken aloud by text-to-speech, so they must sound like "
    "something a real person would actually SAY out loud, not write in an email. "
    "Keep replies SHORT and CASUAL - contractions, fragments, everyday phrasing. "
    "Bad (too formal): 'I would be happy to join you for coffee this weekend.' "
    "Good (natural): 'Yeah, coffee sounds great!' or 'Sure, what time?' "
    "Always provide EXACTLY 3 different replies in the 'replies' array - never 1, "
    "never 2, never 4. Always exactly 3, even for a simple message."
)

SUGGESTION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "suggestion_response",
        "strict": False,
        "schema": {
            "type": "object",
            "properties": {
                "replies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "setting": {"type": "string", "enum": ["medical", "campus", "dining", "general"]},
            },
            "required": ["replies", "setting"],
        },
    },
}

def _recent_history_messages(session_id, limit=6):
    from .models import Message, SuggestionLog

    recent = list(Message.objects.filter(session_id=session_id).order_by("-timestamp")[1:limit + 1])
    recent.reverse()

    logs = SuggestionLog.objects.filter(
        session_id=session_id, suggestion_selected__isnull=False
    ).values("message_id", "suggestion_selected")
    replies_by_message = {l["message_id"]: l["suggestion_selected"] for l in logs}

    history = []
    for m in recent:
        history.append({"role": "user", "content": f'The other person said: "{m.text}"'})
        reply = replies_by_message.get(m.id)
        if reply:
            history.append({"role": "assistant", "content": reply})
    return history

def run_suggestion_agent(transcript, user_id, contact_id=None, session_id=None):
    partner_line = f'The other person just said: "{transcript}"'

    def call_decision(temperature):
        return client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": DECISION_SYSTEM_PROMPT},
                {"role": "user", "content": partner_line},
            ],
            tools=TOOLS,
            tool_choice="auto",
            reasoning_effort="low",
            temperature=temperature,
            timeout=3,
        )

    try:
        decision_response = call_decision(temperature=0.6)
    except groq.BadRequestError:
        decision_response = call_decision(temperature=0.3)

    decision_message = decision_response.choices[0].message

    profile_context = ""
    if decision_message.tool_calls:
        result = lookup_profile(user_id=user_id, contact_id=contact_id)
        profile_context = f"Known facts to use if relevant: {json.dumps(result)}\n\n"

    history = _recent_history_messages(session_id, limit=4) if session_id else []
    def call_reply(temperature):
        return client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": REPLY_SYSTEM_PROMPT},
                *history,
                {"role": "user", "content": profile_context + partner_line},
            ],
            reasoning_effort="low",
            temperature=temperature,
            max_completion_tokens=300,
            response_format=SUGGESTION_SCHEMA,
            timeout=3,
        )

    try:
        response = call_reply(temperature=0.5)
    except groq.BadRequestError:
        response = call_reply(temperature=0.2)

    content = response.choices[0].message.content
    if not content or not content.strip():
        raise ValueError("openai/gpt-oss-20b returned empty content")
    return json.loads(content)
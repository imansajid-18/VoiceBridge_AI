import os
import re
import json
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
import openai
from openai import OpenAI
from .models import Message, SuggestionLog, MemoryEntry, ConversationSession


load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


@lru_cache
def get_client():
    return OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.getenv("GEMINI_API_KEY"),
    )


SYSTEM_PROMPT = (
    "You analyze a finished conversation to learn two separate things:\n"
    "1. general_facts: true about the USER, regardless of who they're talking to - their own "
    "preferences, habits, circumstances, and phrasing style. These belong here even if they came up "
    "while talking to a specific person, because they'll still be true in every other conversation too. "
    "Example: if the user mentions they love coffee, or are finishing a final year project, that is a "
    "general_fact about the user - not a contact_fact, even though it happened during this conversation.\n"
    "2. contact_facts: true about THIS SPECIFIC PERSON, or about the relationship/shared plans between "
    "them and the user specifically. Only the other person's own traits, preferences, and things that "
    "wouldn't make sense outside this relationship (a plan made together, a topic specific to them) belong "
    "here. Refer to the other person by their actual name, exactly as it appears in the conversation - "
    "never as 'the partner' or 'the other person'.\n\n"
    "When in doubt about which list a fact belongs to, ask: would this still be true talking to someone "
    "completely different? If yes, it's a general_fact, not a contact_fact.\n\n"
    "Write every fact in a natural, direct style. For general_facts, do not use the word 'User' - write "
    "as if describing the person directly. Say 'Enjoys coffee' or 'Is finishing a final year project', "
    "not 'User enjoys coffee' or 'The user is finishing...'.\n\n"
    "Be conservative. Only save information that is likely to remain useful in future conversations. "
    "Do not store temporary details, guesses, opinions about the user's mood or state, or assumptions "
    "not clearly stated in the conversation. A single short exchange is often not worth remembering at all "
    "- it is correct to return an empty list if nothing meets this bar.\n"
    "Respond with valid JSON only, in this exact shape: "
    '{"general_facts": ["..."], "contact_facts": ["..."]}'
    "If a 'facts already known' list appears before the conversation, do not extract anything "
    "already covered by it, even if you would phrase it differently. Only extract what's genuinely new.\n"
)


def _strip_markdown_fence(content):
    """Gemini sometimes wraps JSON in ```json ... ``` fences even when told not to."""
    content = content.strip()
    match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```$", content, re.DOTALL)
    return match.group(1).strip() if match else content


def _extract_json(response, model_name):
    choice = response.choices[0]
    content = choice.message.content
    if not content or not content.strip():
        raise ValueError(
            f"{model_name} returned empty content (finish_reason={choice.finish_reason})"
        )
    return json.loads(_strip_markdown_fence(content))

def _validate_memory_shape(parsed, model_name):
    if not isinstance(parsed, dict):
        raise ValueError(f"{model_name} returned non-dict: {parsed!r}")
    general = parsed.get("general_facts")
    contact = parsed.get("contact_facts")
    if not isinstance(general, list) or not all(isinstance(f, str) for f in general):
        raise ValueError(f"{model_name} general_facts must be a list of strings, got {general!r}")
    if not isinstance(contact, list) or not all(isinstance(f, str) for f in contact):
        raise ValueError(f"{model_name} contact_facts must be a list of strings, got {contact!r}")
    return parsed


def _build_conversation_text(session_id):
    session = ConversationSession.objects.select_related("contact").get(id=session_id)
    partner_label = session.contact.name if session.contact else "the other person"

    messages = Message.objects.filter(session_id=session_id).order_by("timestamp")
    logs = SuggestionLog.objects.filter(
        session_id=session_id, suggestion_selected__isnull=False
    ).values("message_id", "suggestion_selected")
    replies_by_message = {log["message_id"]: log["suggestion_selected"] for log in logs}

    lines = []
    for m in messages:
        lines.append(f"{partner_label} said: {m.text}")
        reply = replies_by_message.get(m.id)
        if reply:
            lines.append(f"User replied: {reply}")
    return "\n".join(lines)


def _existing_facts_context(session):
    general = list(
        MemoryEntry.objects.filter(user=session.user, contact=None).values_list("fact", flat=True)
    )
    contact_facts = []
    if session.contact_id:
        contact_facts = list(
            MemoryEntry.objects.filter(
                user=session.user, contact_id=session.contact_id
            ).values_list("fact", flat=True)
        )

    if not general and not contact_facts:
        return ""

    lines = ["Facts already known - do NOT repeat these, even reworded differently:"]
    if general:
        lines.append("About the user:")
        lines += [f"- {f}" for f in general]
    if contact_facts:
        lines.append(f"About {session.contact.name}:")
        lines += [f"- {f}" for f in contact_facts]
    return "\n".join(lines) + "\n\n"


def run_memory_agent(session_id):
    conversation_text = _build_conversation_text(session_id)

    if not conversation_text.strip():
        return {"general_facts": [], "contact_facts": []}

    session = ConversationSession.objects.select_related("contact", "user").get(id=session_id)
    existing_context = _existing_facts_context(session)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": existing_context + conversation_text},
    ]

    try:
        response = get_client().chat.completions.create(
            model="gemini-3.6-flash",
            messages=messages,
            timeout=6,
            max_completion_tokens=1024,
        )
        return _validate_memory_shape(_extract_json(response, "gemini-3.6-flash"), "gemini-3.6-flash")
    except (openai.RateLimitError, openai.NotFoundError, ValueError, json.JSONDecodeError) as e:
        print(
            f"[MemoryAgent] gemini-3.6-flash failed ({type(e).__name__}: {e}), falling back to gemini-3.5-flash-lite"
        )
        response = get_client().chat.completions.create(
            model="gemini-3.5-flash-lite", messages=messages, timeout=10, max_completion_tokens=1024,
        )
        return _validate_memory_shape(_extract_json(response, "gemini-3.5-flash-lite"), "gemini-3.5-flash-lite")


def save_memory_facts(session, facts):
    """
    Writes extracted facts to MemoryEntry.
    - general_facts: saved with contact=None (true regardless of who they're talking to)
    - contact_facts: saved against this session's contact, if there is one
    Skips exact duplicates so repeated conversations don't pile up identical rows.
    """
    created = []

    for fact in facts.get("general_facts", []):
        entry, was_created = MemoryEntry.objects.get_or_create(
            user=session.user,
            contact=None,
            fact=fact,
        )
        if was_created:
            created.append(entry)

    if session.contact_id:
        for fact in facts.get("contact_facts", []):
            entry, was_created = MemoryEntry.objects.get_or_create(
                user=session.user,
                contact_id=session.contact_id,
                fact=fact,
            )
            if was_created:
                created.append(entry)

    return created
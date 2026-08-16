import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv
import openai
from openai import OpenAI
from .models import Message, SuggestionLog

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.getenv("GEMINI_API_KEY"),
)

SYSTEM_PROMPT = (
    "You analyze a finished conversation to learn two separate things:\n"
    "1. general_facts: how this user personally tends to speak (word choices, phrasing habits) "
    "- true regardless of who they're talking to.\n"
    "2. contact_facts: what was actually discussed with this specific person - topics, context, shared details.\n\n"
    "Be conservative. Only save information that is likely to remain useful in future conversations. "
    "Do not store temporary details, guesses, opinions about the user's mood or state, or assumptions "
    "not clearly stated in the conversation. A single short exchange is often not worth remembering at all "
    "- it is correct to return an empty list if nothing meets this bar.\n"
    "Respond with valid JSON only, in this exact shape: "
    '{"general_facts": ["..."], "contact_facts": ["..."]}'
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
        raise ValueError(f"{model_name} returned empty content (finish_reason={choice.finish_reason})")
    return json.loads(_strip_markdown_fence(content))


def run_memory_agent(session_id):
    partner_messages = Message.objects.filter(session_id=session_id).order_by("timestamp")
    selected_replies = (
        SuggestionLog.objects.filter(session_id=session_id, suggestion_selected__isnull=False)
        .order_by("timestamp")
        .values_list("suggestion_selected", flat=True)
    )

    lines = [f"Partner said: {m.text}" for m in partner_messages]
    lines += [f"User replied: {r}" for r in selected_replies]
    conversation_text = "\n".join(lines)

    if not conversation_text.strip():
        return {"general_facts": [], "contact_facts": []}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": conversation_text},
    ]

    try:
        response = client.chat.completions.create(
            model="gemini-3.6-flash", messages=messages, timeout=10, max_completion_tokens=1024,
        )
        return _extract_json(response, "gemini-3.6-flash")
    except (openai.RateLimitError, openai.NotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"[MemoryAgent] gemini-3.6-flash failed ({type(e).__name__}: {e}), falling back to gemini-3.5-flash-lite")
        response = client.chat.completions.create(
            model="gemini-3.5-flash-lite", messages=messages, timeout=10, max_completion_tokens=1024,
        )
        return _extract_json(response, "gemini-3.5-flash-lite")
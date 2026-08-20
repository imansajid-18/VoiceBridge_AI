import groq
from groq import Groq
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from .tools import lookup_profile

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

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
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    }
]

def _extract_json(response, model_name):
    choice = response.choices[0]
    content = choice.message.content
    if not content or not content.strip():
        raise ValueError(f"{model_name} returned empty content (finish_reason={choice.finish_reason})")
    return json.loads(content)


def run_suggestion_agent(transcript, user_id, contact_id=None):
    messages = [
        {
            "role": "system",
            "content": (
                "You help an AAC user reply quickly in conversation. "
                "You may call lookup_profile to personalize your reply. "
                "Always respond with valid JSON only, in this exact shape: "
                '{"replies": ["...", "...", "..."], "setting": "medical|campus|dining|general"}'
            ),
        },
        {"role": "user", "content": f'The other person just said: "{transcript}"'},
    ]

    def call_groq(temperature):
        return client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            reasoning_effort="low",
            temperature=temperature,
            timeout=3,
        )

    try:
        response = call_groq(temperature=0.6)
    except groq.BadRequestError:
        response = call_groq(temperature=0.3)

    message = response.choices[0].message

    if message.tool_calls:
        messages.append(message)
        for tool_call in message.tool_calls:
            result = lookup_profile(user_id=user_id, contact_id=contact_id)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            reasoning_effort="low",
            temperature=0.3,
            timeout=3,
        )
        return _extract_json(response, "openai/gpt-oss-20b")

    return _extract_json(response, "openai/gpt-oss-20b")
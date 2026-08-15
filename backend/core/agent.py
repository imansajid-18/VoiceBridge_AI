import os
import json
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from .tools import lookup_profile

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_profile",
            "description": "Get known facts about the current user's speaking style and, if talking to a saved contact, facts about that specific contact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {"type": "integer"},
                },
                "required": [],
            },
        },
    }
]


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

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        timeout=3,
    )

    message = response.choices[0].message

    if message.tool_calls:
        messages.append(message)
        for tool_call in message.tool_calls:
            args = json.loads(tool_call.function.arguments)
            result = lookup_profile(user_id=user_id, contact_id=args.get("contact_id", contact_id))

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

        second_response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            timeout=3,
        )
        return json.loads(second_response.choices[0].message.content)

    return json.loads(message.content)
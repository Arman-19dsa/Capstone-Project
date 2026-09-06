"""
llm_client.py
Thin wrapper around the Google Gemini API so every agent calls the
LLM the same way. If no API key is set, functions fall back to a simple
placeholder response so the app still runs end-to-end during
development without needing a key yet.

Set your key in a .env file (see .env.example) as:
    GEMINI_API_KEY=xxxxxxxxxxxx

Get a free key at: https://aistudio.google.com/apikey
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-3.6-flash"

_client = None
if API_KEY:
    try:
        from google import genai
        _client = genai.Client(api_key=API_KEY)
    except ImportError:
        _client = None


def ask_llm(system_prompt: str, user_prompt: str, max_tokens: int = 400) -> str:
    if _client is None:
        return (
            "[LLM not configured] Add GEMINI_API_KEY to backend/.env to "
            "enable real responses. This is a placeholder reply."
        )

    from google.genai import types

    response = _client.models.generate_content(
        model=MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
        ),
    )
    text = (response.text or "").strip()
    text = text.replace("**", "").replace("*", "")
    return text
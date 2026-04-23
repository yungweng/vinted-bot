import os
import re
from functools import lru_cache
from pathlib import Path

from openai import OpenAI

from config import CLASSIFIER


@lru_cache(maxsize=1)
def _client():
    return OpenAI(
        base_url=CLASSIFIER["base_url"],
        api_key=os.environ["OPENROUTER_API_KEY"],
        default_headers={
            "HTTP-Referer": CLASSIFIER["app_url"],
            "X-Title": CLASSIFIER["app_name"],
        },
    )


def _system_prompt():
    path = Path(CLASSIFIER["system_prompt_file"])
    if not path.exists():
        return None
    content = path.read_text().strip()
    return content or None


def _parse_response(raw):
    cleaned = (raw or "").strip()
    lowered = cleaned.lower()
    if lowered.startswith("ja"):
        return "ja", ""
    if lowered.startswith("nein") or lowered.startswith("no"):
        after = cleaned[4:] if lowered.startswith("nein") else cleaned[2:]
        reason = re.sub(r"^[\s:;,\-\.]+", "", after).strip()
        return "nein", reason
    return "nein", cleaned[:200]


def classify(user_message):
    messages = []
    system = _system_prompt()
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_message})

    response = _client().chat.completions.create(
        model=CLASSIFIER["model"],
        max_tokens=CLASSIFIER["max_tokens"],
        temperature=CLASSIFIER["temperature"],
        messages=messages,
    )
    raw = response.choices[0].message.content or ""
    verdict, reason = _parse_response(raw)
    return verdict, reason, raw

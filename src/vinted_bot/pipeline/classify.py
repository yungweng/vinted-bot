import re

from openai import OpenAI

from vinted_bot.config import CLASSIFIER


ANSWER_FORMAT = (
    "\n\nANTWORTFORMAT\n"
    'Antworte mit "ja" - oder "vielleicht: <kurzer Grund>" - oder "nein: <kurzer Grund>".'
)


def build_system_prompt(ja_prompt, nein_prompt, vielleicht_prompt, sonderregeln):
    parts = ["Du bist ein Triage-Filter. Du vergibst drei Labels: \"ja\", \"vielleicht\" oder \"nein\"."]
    parts.append(ANSWER_FORMAT)
    parts.append("\nPRUEFREIHENFOLGE (erstes Treffen gewinnt)")
    if (nein_prompt or "").strip():
        parts.append("\n[1] AUSSCHLUSSGRUENDE -> \"nein\"\n" + nein_prompt.strip())
    if (ja_prompt or "").strip():
        parts.append("\n[2] ZIELKRITERIEN -> \"ja\"\n" + ja_prompt.strip())
    if (vielleicht_prompt or "").strip():
        parts.append("\n[3] SONST -> \"vielleicht\"\n" + vielleicht_prompt.strip())
    if (sonderregeln or "").strip():
        parts.append("\nSONDERREGELN\n" + sonderregeln.strip())
    return "\n".join(parts)


def _parse_response(raw):
    cleaned = (raw or "").strip()
    lowered = cleaned.lower()
    if lowered.startswith("vielleicht"):
        after = cleaned[len("vielleicht"):]
        reason = re.sub(r"^[\s:;,\-\.]+", "", after).strip()
        return "vielleicht", reason
    if lowered.startswith("ja"):
        after = cleaned[2:]
        reason = re.sub(r"^[\s:;,\-\.]+", "", after).strip()
        return "ja", reason
    if lowered.startswith("nein") or lowered.startswith("no"):
        after = cleaned[4:] if lowered.startswith("nein") else cleaned[2:]
        reason = re.sub(r"^[\s:;,\-\.]+", "", after).strip()
        return "nein", reason
    return "vielleicht", cleaned[:200]


def classify(user_message, *, api_key, model, system_prompt, base_url):
    if not api_key:
        raise RuntimeError("Kein API-Key hinterlegt. Bitte in den Einstellungen setzen.")
    client_kwargs = {"base_url": base_url, "api_key": api_key}
    # OpenRouter uses these headers for public app ranking. Anthropic silently
    # ignores them, but some older SDK/httpx combos choke encoding custom
    # headers, so send them only to OpenRouter.
    if "openrouter.ai" in base_url:
        client_kwargs["default_headers"] = {
            "HTTP-Referer": CLASSIFIER["app_url"],
            "X-Title": CLASSIFIER["app_name"],
        }
    client = OpenAI(**client_kwargs)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=model,
        max_tokens=CLASSIFIER["max_tokens"],
        temperature=CLASSIFIER["temperature"],
        messages=messages,
    )
    raw = response.choices[0].message.content or ""
    verdict, reason = _parse_response(raw)
    return verdict, reason, raw

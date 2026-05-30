import os
from config import PERSONA_FILE, CONTACTS_DIR

EXTRACT_MODEL = "llama-3.1-8b-instant"

EXTRACT_PROMPT = """\
You extract memorable facts about a person from SMS conversations.
Given their existing profile and the latest message exchange, list only NEW facts that were learned.
If nothing new was learned, output nothing at all — not even a period.
Format: one fact per line starting with "- "."""


def load_persona() -> str:
    try:
        with open(PERSONA_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def load_contact(number: str) -> str:
    path = _contact_path(number)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def update_contact(number: str, user_message: str, ai_reply: str, groq_client) -> None:
    existing = load_contact(number)

    messages = [
        {"role": "system", "content": EXTRACT_PROMPT},
        {
            "role": "user",
            "content": (
                f"Existing profile:\n{existing or '(none yet)'}\n\n"
                f"Latest exchange:\n"
                f"User: {user_message}\n"
                f"Assistant: {ai_reply}"
            ),
        },
    ]

    try:
        result = groq_client.chat.completions.create(
            model=EXTRACT_MODEL,
            messages=messages,
            max_tokens=200,
        )
        new_facts = result.choices[0].message.content.strip()
    except Exception as e:
        print(f"[PROFILE] Extraction failed for {number}: {e}")
        return

    if not new_facts:
        return

    os.makedirs(CONTACTS_DIR, exist_ok=True)
    path = _contact_path(number)
    with open(path, "a", encoding="utf-8") as f:
        if existing:
            f.write("\n")
        f.write(new_facts + "\n")
    print(f"[PROFILE] Updated contact for {number}: {new_facts[:80]}")


def _contact_path(number: str) -> str:
    safe = number.replace("+", "").replace(" ", "_")
    return os.path.join(CONTACTS_DIR, f"{safe}.txt")

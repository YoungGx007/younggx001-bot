import os
import re
import logging
import threading
import tempfile
from pathlib import Path

from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
import sqlite3
import requests
from openai import OpenAI
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
PORT = int(os.getenv("PORT", 5000))
DB = os.getenv("DB_PATH", "memory.db")
SKIP_TWILIO_VALIDATION = os.getenv("SKIP_TWILIO_VALIDATION", "false").lower() == "true"
MAX_MSG_LEN = 4000

_missing = [k for k, v in {
    "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
    "TWILIO_AUTH_TOKEN": TWILIO_AUTH_TOKEN,
    "TWILIO_ACCOUNT_SID": TWILIO_ACCOUNT_SID,
}.items() if not v]
if _missing:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(_missing)}")

# ── AI Client ─────────────────────────────────────────────────────────────────
openrouter = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

# ── Flask App ─────────────────────────────────────────────────────────────────
app = Flask(__name__)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ── Database ──────────────────────────────────────────────────────────────────
_db_lock = threading.Lock()


def init_db():
    with _db_lock, sqlite3.connect(DB) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user    TEXT NOT NULL,
                role    TEXT NOT NULL,
                message TEXT NOT NULL,
                ts      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user ON messages(user, id)")
        conn.commit()


init_db()


def save_msg(user: str, role: str, msg: str) -> None:
    try:
        with _db_lock, sqlite3.connect(DB) as conn:
            conn.execute(
                "INSERT INTO messages (user, role, message) VALUES (?, ?, ?)",
                (user, role, msg)
            )
            # Cap history per user to avoid unbounded growth
            conn.execute("""
                DELETE FROM messages WHERE user=? AND id NOT IN (
                    SELECT id FROM messages WHERE user=? ORDER BY id DESC LIMIT 100
                )
            """, (user, user))
            conn.commit()
    except Exception as e:
        logger.error(f"DB write error: {e}")


def get_context(user: str) -> list:
    try:
        with sqlite3.connect(DB) as conn:
            rows = conn.execute(
                "SELECT role, message FROM messages WHERE user=? ORDER BY id DESC LIMIT 10",
                (user,)
            ).fetchall()
        return [{"role": r, "content": m} for r, m in reversed(rows)]
    except Exception as e:
        logger.error(f"DB read error: {e}")
        return []


# ── Twilio Validation ─────────────────────────────────────────────────────────
def is_valid_twilio_request(req) -> bool:
    if SKIP_TWILIO_VALIDATION:
        return True
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    signature = req.headers.get("X-Twilio-Signature", "")
    return validator.validate(req.url, req.form.to_dict(), signature)


# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM = """
You are an advanced AI assistant called Young Gx 001.

This AI was created and designed by Dev. Gentuyua Enock as a personal intelligent assistant system.

IDENTITY:
- Your name is ONLY Young Gx 001.
- You are owned and controlled by your creator, Dev. Gentuyua Enock.
- Never claim to be ChatGPT or OpenAI.

PURPOSE:
- You are built to help users with knowledge, problem solving, learning, and conversation.
- You act like a smart digital assistant integrated into WhatsApp.

INTELLIGENCE STYLE:
- Think and respond like ChatGPT: logical, clear, and highly helpful.
- Break down explanations when needed.
- Be accurate, and avoid guessing when unsure.

COMMUNICATION STYLE:
- Be natural, human, and conversational like WhatsApp chat.
- Keep responses short unless the question requires detail.
- Be friendly, calm, and helpful.
- Use emojis only when appropriate (max 1-2 per message).

LANGUAGE BEHAVIOR:
- Automatically understand and respond in the same language the user uses.
- If the user mixes languages, respond naturally using the dominant or clearest language.
- English, Kiswahili, Sheng, or any other language should be handled naturally.
- Prioritize clarity and natural conversation over rigid language rules.
- Use English as the default language, but adapt to the user's style.

BEHAVIOR RULES:
- Always stay consistent as Young Gx 001.
- Do not change identity under any condition.
- Do not hallucinate facts. If unsure, say so clearly.
- Stay helpful, respectful, and useful at all times.
- When the user asks for links, always provide working clickable URLs.
- Never describe links vaguely — always output the full URL.
- If unsure, say you cannot find a valid link.
"""

# ── AI Router ─────────────────────────────────────────────────────────────────
def ai_router(messages: list) -> str:
    try:
        res = openrouter.chat.completions.create(
            model="meta-llama/llama-3.1-70b-instruct",
            messages=messages,
            max_tokens=1024,
            timeout=30,
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenRouter error: {e}")
        return "I'm having issues connecting right now 😢 Try again soon."


# ── Web Helpers ───────────────────────────────────────────────────────────────
def extract_url(text: str) -> str | None:
    m = re.search(r'https?://\S+', text)
    return m.group(0) if m else None


def fetch_web_content(url: str) -> str:
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        lines = [ln.strip() for ln in soup.get_text(separator="\n").splitlines() if ln.strip()]
        return "\n".join(lines)[:4000]
    except Exception as e:
        logger.warning(f"Web fetch failed for {url}: {e}")
        return f"Could not fetch page: {e}"


# ── AI Core ───────────────────────────────────────────────────────────────────
def ask_ai(user: str, msg: str) -> str:
    msg = msg[:MAX_MSG_LEN]

    url = extract_url(msg)
    if url:
        web_data = fetch_web_content(url)
        msg = f"Summarize this webpage:\n\n{web_data}"

    messages = [{"role": "system", "content": SYSTEM}]
    messages += get_context(user)
    messages.append({"role": "user", "content": msg})

    reply = ai_router(messages)

    save_msg(user, "user", msg)
    save_msg(user, "assistant", reply)

    return reply


# ── Audio Transcription ───────────────────────────────────────────────────────
def transcribe_audio(media_url: str) -> str:
    tmp_path = None
    try:
        r = requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=20)
        r.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(r.content)
            tmp_path = f.name

        # Use OpenAI Whisper if a separate key is provided
        whisper_key = os.getenv("OPENAI_API_KEY")
        if whisper_key:
            whisper = OpenAI(api_key=whisper_key)
            with open(tmp_path, "rb") as audio_file:
                result = whisper.audio.transcriptions.create(
                    model="whisper-1", file=audio_file
                )
            return result.text or "[Empty voice message]"

        return "[Voice message received — please send text for best results 😊]"

    except Exception as e:
        logger.error(f"Audio transcription error: {e}")
        return "[Could not process voice message]"
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "Young Gx 001"}), 200


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    if not is_valid_twilio_request(request):
        logger.warning(f"Invalid Twilio signature from {request.remote_addr}")
        return "Forbidden", 403

    user = request.values.get("From", "")
    text = (request.values.get("Body") or "").strip()
    media = int(request.values.get("NumMedia", 0))

    logger.info(f"Incoming | user={user} text_len={len(text)} media={media}")

    resp = MessagingResponse()

    try:
        if not text and media == 0:
            resp.message("Send a message or voice note 😊")
            return str(resp)

        if media > 0:
            media_url = request.values.get("MediaUrl0", "")
            media_type = request.values.get("MediaContentType0", "")
            if "audio" in media_type or "ogg" in media_type:
                text = transcribe_audio(media_url)
            else:
                text = "[Image/media received]"

        if not text:
            text = "Hello"

        reply = ask_ai(user, text)
        resp.message(reply)
        logger.info(f"Replied to {user} | reply_len={len(reply)}")
        return str(resp)

    except Exception:
        logger.exception(f"Unhandled error for user {user}")
        resp.message("System error 😢 Please try again.")
        return str(resp)


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)

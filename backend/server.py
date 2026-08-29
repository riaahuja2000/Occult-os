import os
import re
import uuid
import hashlib
import logging
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal

import jwt
import bcrypt
import requests
from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field, field_validator
from dotenv import load_dotenv

import oracle
import numerology
import tarot

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("velora")

# ---------------------------------------------------------------- config / db
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

JWT_SECRET = os.environ.get("JWT_SECRET", "velora-dev-secret-change-me")
JWT_ALG = "HS256"
TOKEN_DAYS = 30

OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "riaahuja2000@gmail.com").strip().lower()
OWNER_PASSWORD = os.environ["OWNER_PASSWORD"]
OWNER_NAME = os.environ.get("OWNER_NAME", "Ria Ahuja")
SEED_CUSTOMER_EMAIL = os.environ.get("SEED_CUSTOMER_EMAIL", "taromaya@gmail.com").strip().lower()
SEED_CUSTOMER_PASSWORD = os.environ.get("SEED_CUSTOMER_PASSWORD", "123456789")
SEED_CUSTOMER_NAME = os.environ.get("SEED_CUSTOMER_NAME", "Maya")

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_SLUG = "velora-occult-voice"

DEFAULT_SETTINGS = {
    "_id": "app",
    "app_name": "VELORA",
    "tagline": "Ask · Receive · Apply · Move",
    "subtitle": "Occult sciences. Real life. Real results.",
    "logo_url": "",
    "background_url": "",
    "voice": "shimmer",
    "speed": 0.95,
    "updated_at": None,
}

app = FastAPI(title="VELORA API")
api = APIRouter(prefix="/api")
bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------- helpers
def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8")[:72], bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_pw(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


def make_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user["id"],
        "role": user["role"],
        "tv": user.get("token_version", 0),
        "iat": now,
        "exp": now + timedelta(days=TOKEN_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def public_user(u: dict) -> dict:
    return {
        "id": u["id"],
        "name": u.get("name", ""),
        "email": u["email"],
        "role": u["role"],
        "language": u.get("language", "en"),
        "voice": u.get("voice", ""),
        "speed": u.get("speed", 0),
        "active": u.get("active", True),
        "is_owner": u["role"] == "owner",
        "created_at": u.get("created_at"),
    }


async def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> dict:
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired session")
    user = await db.users.find_one({"id": payload.get("sub")})
    if not user or payload.get("tv") != user.get("token_version", 0):
        raise HTTPException(401, "Session expired")
    if not user.get("active", True):
        raise HTTPException(403, "Your account has been deactivated. Contact the keeper.")
    return user


async def require_owner(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "owner":
        raise HTTPException(403, "Owner access required")
    return user


# ---------------------------------------------------------------- models
class RegisterBody(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class ForgotBody(BaseModel):
    email: EmailStr


class ConsultBody(BaseModel):
    question: str
    lang: Literal["en", "hi", "hng"] = "en"


class SpeakBody(BaseModel):
    text: str
    lang: Literal["en", "hi", "hng"] = "en"


class ProfileBody(BaseModel):
    name: Optional[str] = Field(default=None, max_length=60)
    language: Optional[Literal["en", "hi", "hng"]] = None
    voice: Optional[str] = None
    speed: Optional[float] = None


class KnowledgeBody(BaseModel):
    topic: str
    lang: Literal["en", "hi", "hng"]
    text: str = Field(min_length=8)


class NumerologyBody(BaseModel):
    full_name: str = Field(default="", max_length=120)
    dob: str  # YYYY-MM-DD


class TarotBody(BaseModel):
    spread: Literal["single", "three", "situation", "five"] = "three"


class SettingsBody(BaseModel):
    app_name: Optional[str] = None
    tagline: Optional[str] = None
    subtitle: Optional[str] = None
    voice: Optional[str] = None
    speed: Optional[float] = None


class ActiveBody(BaseModel):
    active: bool


class ResetBody(BaseModel):
    new_password: str = Field(min_length=8)


# ---------------------------------------------------------------- seeding
async def ensure_user(email: str, password: str, name: str, role: str):
    existing = await db.users.find_one({"email": email})
    if existing:
        return
    now = datetime.now(timezone.utc).isoformat()
    await db.users.insert_one({
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email,
        "password_hash": hash_pw(password),
        "role": role,
        "language": "en",
        "active": True,
        "token_version": 0,
        "created_at": now,
    })
    logger.info("Seeded %s account: %s", role, email)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await ensure_user(OWNER_EMAIL, OWNER_PASSWORD, OWNER_NAME, "owner")
    await ensure_user(SEED_CUSTOMER_EMAIL, SEED_CUSTOMER_PASSWORD, SEED_CUSTOMER_NAME, "customer")
    if not await db.settings.find_one({"_id": "app"}):
        s = dict(DEFAULT_SETTINGS)
        s["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.settings.insert_one(s)
    try:
        await run_in_threadpool(_init_storage)
    except Exception as e:
        logger.warning("Object storage init failed (uploads may be unavailable): %s", e)


@app.on_event("shutdown")
async def shutdown():
    client.close()


# ---------------------------------------------------------------- object storage
_storage_key: Optional[str] = None


def _init_storage() -> Optional[str]:
    global _storage_key
    if _storage_key:
        return _storage_key
    if not EMERGENT_LLM_KEY:
        return None
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_LLM_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def _vercel_blob_credentials():
    store_id = (os.getenv("BLOB_STORE_ID") or "").strip()

    try:
        from vercel.functions import get_env
        env = get_env()
        oidc_token = (
            os.getenv("VERCEL_OIDC_TOKEN")
            or getattr(env, "VERCEL_OIDC_TOKEN", "")
            or ""
        ).strip()
    except Exception:
        oidc_token = (os.getenv("VERCEL_OIDC_TOKEN") or "").strip()

    # Vercel Blob API expects store ID without "store_" prefix.
    if store_id.startswith("store_"):
        store_id = store_id[len("store_"):]

    return store_id, oidc_token


def _put_object(path: str, data: bytes, content_type: str):
    store_id, oidc_token = _vercel_blob_credentials()

    if not store_id:
        raise RuntimeError("BLOB_STORE_ID is missing")

    if not oidc_token:
        raise RuntimeError("Vercel OIDC token is unavailable")

    resp = requests.put(
        "https://vercel.com/api/blob/",
        params={"pathname": path},
        headers={
            "Authorization": f"Bearer {oidc_token}",
            "x-vercel-blob-store-id": store_id,
            "x-api-blob-request-id": f"{store_id}:{uuid.uuid4().hex}",
            "x-api-blob-request-attempt": "0",
            "x-api-version": "12",
            "x-vercel-blob-access": "private",
            "x-content-type": content_type or "application/octet-stream",
            "x-add-random-suffix": "0",
        },
        data=data,
        timeout=60,
    )

    resp.raise_for_status()
    return resp.json()


def _storage_ready() -> bool:
    return bool(os.getenv("BLOB_STORE_ID"))
# ---------------------------------------------------------------- (no external AI)
# This app uses ZERO AI inference credit. Speech-to-text and text-to-speech run
# on the user's device (free); answers come only from the local knowledge engine.


# ---------------------------------------------------------------- auth routes
@api.get("/")
async def root():
    return {"message": "VELORA oracle online"}


@api.post("/auth/register")
async def register(body: RegisterBody):
    email = str(body.email).lower()
    if email == OWNER_EMAIL:
        raise HTTPException(409, "This email is reserved.")
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "An account with this email already exists.")
    now = datetime.now(timezone.utc).isoformat()
    user = {
        "id": str(uuid.uuid4()),
        "name": body.name.strip(),
        "email": email,
        "password_hash": hash_pw(body.password),
        "role": "customer",
        "language": "en",
        "active": True,
        "token_version": 0,
        "created_at": now,
    }
    await db.users.insert_one(user)
    return {"token": make_token(user), "user": public_user(user)}


@api.post("/auth/login")
async def login(body: LoginBody):
    email = str(body.email).lower()
    user = await db.users.find_one({"email": email})
    dummy = "$2b$12$" + "x" * 53
    ok = verify_pw(body.password, user["password_hash"] if user else dummy)
    if not user or not ok:
        raise HTTPException(401, "Invalid email or password")
    if not user.get("active", True):
        raise HTTPException(403, "Your account has been deactivated. Contact the keeper.")
    return {"token": make_token(user), "user": public_user(user)}


@api.post("/auth/forgot-password")
async def forgot_password(body: ForgotBody):
    email = str(body.email).lower()
    user = await db.users.find_one({"email": email})
    if user and user["role"] == "customer":
        await db.reset_requests.update_one(
            {"email": email},
            {"$set": {"email": email, "name": user.get("name", ""), "user_id": user["id"],
                      "status": "pending", "created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
    return {"ok": True, "message": "If an account exists, the keeper has been notified to restore your access."}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return public_user(user)


@api.patch("/me")
async def update_me(body: ProfileBody, user: dict = Depends(get_current_user)):
    updates = {}
    if body.name is not None and body.name.strip():
        updates["name"] = body.name.strip()
    if body.language is not None:
        updates["language"] = body.language
    if body.voice is not None:
        updates["voice"] = body.voice
    if body.speed is not None:
        updates["speed"] = max(0.5, min(2.0, float(body.speed)))
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
        user = await db.users.find_one({"id": user["id"]})
    return public_user(user)

def _relevant_knowledge_text(question: str, text: str, topics=None):
    import re

    q = (question or "").strip().lower()
    raw = (text or "").strip()

    if not q or not raw:
        return 0, ""

    def words(value):
        return set(
            re.findall(
                r"[a-zA-Z0-9\u0900-\u097F]+",
                value.lower()
            )
        )

    stop = {
        "mera", "meri", "mere", "mujhe", "main",
        "mein", "ka", "ki", "ke", "ko", "hai",
        "hoga", "hogi", "honge", "kya", "kaisa",
        "kaisi", "kaise", "batao", "please",

        "the", "a", "an", "is", "are", "was",
        "were", "to", "of", "and", "or", "in",
        "on", "for", "with", "my", "me", "i",
        "what", "how", "can", "will", "would",
        "please", "tell"
    }

    families = {
        "relationship": {
            "shaadi", "marriage", "wedding",
            "spouse", "husband", "wife",
            "partner", "relationship", "love",
            "romance", "matrimony"
        },

        "timing": {
            "kab", "when", "timing", "time",
            "date", "month", "year", "period",
            "age", "dasha", "transit"
        },

        "daily": {
            "aaj", "today", "daily",
            "day", "din", "tomorrow", "kal"
        },

        "career": {
            "career", "job", "naukri", "work",
            "business", "profession", "promotion",
            "interview", "office"
        },

        "money": {
            "money", "paisa", "paise",
            "finance", "financial", "wealth",
            "income", "salary", "business",
            "profit"
        },

        "health": {
            "health", "sehat", "body",
            "wellness", "healing", "energy",
            "sleep", "stress"
        },

        "purpose": {
            "purpose", "mission", "calling",
            "direction", "life", "path"
        },

        "tarot": {
            "tarot", "card", "cards",
            "arcana", "spread"
        },

        "astrology": {
            "astrology", "kundali", "horoscope",
            "zodiac", "planet", "graha",
            "lagna", "nakshatra", "dasha",
            "transit", "birthchart", "chart"
        },

        "numerology": {
            "numerology", "number", "numbers",
            "mulank", "bhagyank", "lifepath",
            "destiny", "name-number"
        },

        "aura": {
            "aura", "energy", "vibration",
            "vibrations", "field"
        },

        "crystals": {
            "crystal", "crystals", "gemstone",
            "stone", "stones"
        },

        "runes": {
            "rune", "runes"
        },

        "palmistry": {
            "palm", "palmistry", "hand",
            "line", "lines"
        },

        "fengshui": {
            "feng", "shui", "fengshui"
        },

        "kabbalah": {
            "kabbalah", "kabbalistic"
        },

        "iching": {
            "iching", "i-ching", "hexagram"
        },

        "mindfulness": {
            "mindfulness", "meditation",
            "calm", "breathing", "breath",
            "journal", "journaling"
        }
    }

    q_words = {
        w for w in words(q)
        if len(w) > 1 and w not in stop
    }

    triggered = []

    for family, terms in families.items():
        if q_words & terms:
            triggered.append(family)

    # Add detected Oracle topics as relevance signals.
    topic_words = set()

    for topic in (topics or []):
        topic_words.update(words(str(topic)))

    search_words = set(q_words)
    search_words.update(topic_words)

    for family in triggered:
        search_words.update(families[family])

    junk_phrases = (
        "world occult knowledge base",
        "velora intelligence library",
        "master reference",
        "current authoritative factual data",
        "when required",
        "table of contents",
        "copyright",
        "reference document",
        "knowledge base",
        "document purpose",
        "introduction"
    )

    blocks = re.split(
        r"\n\s*\n|(?<=[.!?])\s+",
        raw
    )

    ranked = []

    for block in blocks:
        clean = re.sub(
            r"\s+",
            " ",
            block
        ).strip()

        if len(clean) < 25:
            continue

        low = clean.lower()

        if any(
            junk in low
            for junk in junk_phrases
        ):
            continue

        block_words = words(low)

        # Generic lexical relevance.
        exact_overlap = block_words & q_words
        expanded_overlap = block_words & search_words

        if not expanded_overlap:
            continue

        # If question clearly has multiple intents,
        # candidate must satisfy every important intent.
        valid = True
        family_hits = 0

        for family in triggered:
            family_terms = families[family]

            if block_words & family_terms:
                family_hits += 1
            else:
                valid = False
                break

        if triggered and not valid:
            continue

        score = 0

        score += len(exact_overlap) * 12
        score += len(expanded_overlap) * 3
        score += family_hits * 15

        # Exact wording receives a strong boost.
        if q in low:
            score += 50

        # Prefer useful contextual text over headings.
        if len(clean) >= 60:
            score += 4

        if len(clean) >= 120:
            score += 3

        ranked.append(
            (score, clean)
        )

    if not ranked:
        return 0, ""

    ranked.sort(
        key=lambda item: item[0],
        reverse=True
    )

    best_score, best_text = ranked[0]

    # Prevent weak/random matches.
    minimum_score = 12

    if triggered:
        minimum_score = 18

    if best_score < minimum_score:
        return 0, ""

    return best_score, best_text[:1400]
# ---------------------------------------------------------------- oracle
@api.post("/oracle/consult")
async def consult(body: ConsultBody, user: dict = Depends(get_current_user)):
    question = (body.question or "").strip()

    if not question:
        raise HTTPException(400, "Please ask a question.")

    topics = oracle.detect_topics(question)

    normalized_topics = [
        str(t).strip().lower()
        for t in topics
        if str(t).strip()
    ]

    matched_entries = []

    cursor = db.knowledge_entries.find({
        "deleted_at": None
    })

    async for entry in cursor:
        entry_topic = str(
            entry.get("topic", "")
        ).strip().lower()

        entry_text = str(
            entry.get("text", "")
        ).strip()

        entry_lang = str(
            entry.get("lang", "")
        ).strip().lower()

        if not entry_text:
            continue

        topic_matches = (
            entry_topic in normalized_topics
            or entry_topic == "general"
        )

        language_matches = (
            not entry_lang
            or entry_lang == body.lang
        )

        if topic_matches and language_matches:
            matched_entries.append(entry)

    topic_priority = {
        topic: index
        for index, topic in enumerate(normalized_topics)
    }

    matched_entries.sort(
        key=lambda entry: topic_priority.get(
            str(
                entry.get("topic", "")
            ).strip().lower(),
            999
        )
    )

    chosen = None
    chosen_answer = ""

    # Search every matching knowledge entry.
    # Only genuinely relevant context is allowed.
    for entry in matched_entries:
        candidate = _relevant_knowledge_text(
            question,
            str(entry.get("text", ""))
        )

        if not candidate:
            continue

        candidate_clean = candidate.strip()

        if not candidate_clean:
            continue

        # Never use obvious document titles / metadata as answers.
        low = candidate_clean.lower()

        blocked_phrases = (
            "world occult knowledge base",
            "velora intelligence library",
            "master reference",
            "table of contents",
            "copyright",
        )

        if any(
            phrase in low
            for phrase in blocked_phrases
        ):
            continue
    question = (body.question or "").strip()

    if not question:
        raise HTTPException(
            400,
            "Please ask a question."
        )

    topics = oracle.detect_topics(question)

    normalized_topics = {
        str(t).strip().lower()
        for t in topics
        if str(t).strip()
    }

    best_score = 0
    best_answer = ""
    best_entry = None

    cursor = db.knowledge_entries.find({
        "deleted_at": None
    }).limit(3000)

    async for entry in cursor:
        entry_text = str(
            entry.get("text", "")
        ).strip()

        if not entry_text:
            continue

        score, candidate = _relevant_knowledge_text(
            question,
            entry_text,
            topics
        )

        if not candidate:
            continue

        entry_topic = str(
            entry.get("topic", "")
        ).strip().lower()

        entry_lang = str(
            entry.get("lang", "")
        ).strip().lower()

        # Prefer the correct topic.
        if (
            entry_topic
            and entry_topic in normalized_topics
        ):
            score += 10

        # Prefer same-language knowledge,
        # but still allow another language if relevant.
        if (
            entry_lang
            and entry_lang == body.lang
        ):
            score += 4

        if score > best_score:
            best_score = score
            best_answer = candidate
            best_entry = entry

    if best_answer:
        result = {
            "answer": best_answer,
            "topics": topics,
            "primary": (
                best_entry.get("topic")
                if best_entry
                else (
                    topics[0]
                    if topics
                    else "General"
                )
            ),
        }

    else:
        # No genuinely relevant uploaded context.
        # Use the built-in Oracle instead of random file text.
        result = oracle.compose_answer(
            question,
            body.lang
        )

    now = datetime.now(
        timezone.utc
    ).isoformat()

    reading = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "question": question,
        "answer": result["answer"],
        "topics": result["topics"],
        "primary": result["primary"],
        "lang": body.lang,
        "created_at": now,
    }

    await db.readings.insert_one(
        dict(reading)
    )

    reading.pop("_id", None)

    return reading

@api.get("/oracle/daily")
async def daily(lang: str = "en", user: dict = Depends(get_current_user)):
    if lang not in ("en", "hi", "hng"):
        lang = "en"
    day = datetime.now(timezone.utc).date().isoformat()
    text = oracle.daily_reading(f"{user['id']}:{day}:{lang}", lang)
    return {"date": day, "text": text}


@api.get("/readings")
async def my_readings(user: dict = Depends(get_current_user)):
    rows = await db.readings.find({"user_id": user["id"]}).sort("created_at", -1).to_list(100)
    for r in rows:
        r.pop("_id", None)
    return rows


# ---------------------------------------------------------------- numerology engine
@api.post("/numerology/reading")
async def numerology_reading(body: NumerologyBody, user: dict = Depends(get_current_user)):
    try:
        return numerology.reading(body.full_name, body.dob)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------- tarot engine
@api.get("/tarot/deck")
async def tarot_deck(user: dict = Depends(get_current_user)):
    return {"count": len(tarot.DECK), "spreads": list(tarot.SPREADS.keys()), "cards": tarot.DECK}


@api.post("/tarot/draw")
async def tarot_draw(body: TarotBody, user: dict = Depends(get_current_user)):
    return tarot.draw(body.spread)


# ---------------------------------------------------------------- settings (branding)
@api.get("/settings")
async def get_settings():
    s = await db.settings.find_one({"_id": "app"}) or DEFAULT_SETTINGS
    s.pop("_id", None)
    return s


@api.put("/owner/settings")
async def update_settings(body: SettingsBody, owner: dict = Depends(require_owner)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "speed" in updates:
        updates["speed"] = max(0.5, min(2.0, float(updates["speed"])))
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.settings.update_one({"_id": "app"}, {"$set": updates}, upsert=True)
    s = await db.settings.find_one({"_id": "app"})
    s.pop("_id", None)
    return s


@api.post("/owner/upload")
async def upload_branding(
    kind: str = Form(...),
    file: UploadFile = File(...),
    owner: dict = Depends(require_owner),
):
    if kind not in ("logo", "background"):
        raise HTTPException(400, "Invalid image type.")

    ct = (file.content_type or "").lower()

    allowed = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/webp": "webp",
    }

    if ct not in allowed:
        raise HTTPException(
            400,
            "Only PNG, JPG, JPEG or WEBP images are allowed."
        )

    data = await file.read()

    if not data:
        raise HTTPException(400, "Empty image.")

    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(
            400,
            "Image must be under 8 MB."
        )

    ext = allowed[ct]

    path = (
        f"{APP_SLUG}/branding/"
        f"{kind}-{uuid.uuid4().hex}.{ext}"
    )

    # Store the image directly inside MongoDB.
    # No Blob key, OIDC or Emergent key required.
    await db.media_files.insert_one({
        "id": str(uuid.uuid4()),
        "path": path,
        "kind": kind,
        "content_type": ct,
        "data": data,
        "size": len(data),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    field = (
        "logo_url"
        if kind == "logo"
        else "background_url"
    )

    url = f"/api/media?path={path}"

    await db.settings.update_one(
        {"_id": "global"},
        {
            "$set": {
                field: url,
                "updated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
        },
        upsert=True,
    )

    return {
        "url": url,
        "kind": kind,
        "ok": True,
    }


@api.get("/media")
async def get_media(path: str):
    if not path.startswith(
        f"{APP_SLUG}/branding/"
    ):
        raise HTTPException(400, "Bad path.")

    media = await db.media_files.find_one(
        {"path": path}
    )

    if not media:
        raise HTTPException(404, "Not found.")

    data = media.get("data")

    if not data:
        raise HTTPException(404, "Not found.")

    content_type = media.get(
        "content_type",
        "application/octet-stream"
    )

    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=3600"
        },
    )
# ---------------------------------------------------------------- owner console
@api.get("/owner/overview")
async def owner_overview(owner: dict = Depends(require_owner)):
    readings = await db.readings.find().sort("created_at", -1).to_list(500)
    users = await db.users.find().sort("created_at", -1).to_list(500)
    for r in readings:
        r.pop("_id", None)

    topic_counts: dict[str, int] = {}
    for r in readings:
        for t in r.get("topics", []):
            if t == "general":
                continue
            topic_counts[t] = topic_counts.get(t, 0) + 1
    most_asked = sorted(topic_counts.items(), key=lambda x: -x[1])[:8]
    most_asked = [{"name": n, "count": c} for n, c in most_asked]

    today_key = datetime.now(timezone.utc).date().isoformat()

    def day_key(iso: str) -> str:
        try:
            return datetime.fromisoformat(iso.replace("Z", "+00:00")).date().isoformat()
        except Exception:
            return ""

    last7 = []
    for i in range(6, -1, -1):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).date()
        key = d.isoformat()
        count = sum(1 for r in readings if day_key(r.get("created_at", "")) == key)
        last7.append({"date": key, "dow": d.weekday(), "count": count})

    members = []
    for u in users:
        rc = sum(1 for r in readings if r["user_id"] == u["id"])
        members.append({
            "id": u["id"], "name": u.get("name", ""), "email": u["email"],
            "role": u["role"], "active": u.get("active", True),
            "is_owner": u["role"] == "owner", "created_at": u.get("created_at"),
            "readings": rc,
        })

    reset_requests = await db.reset_requests.find({"status": "pending"}).sort("created_at", -1).to_list(100)
    for rr in reset_requests:
        rr.pop("_id", None)

    return {
        "total_sessions": len(readings),
        "registered_users": len(users),
        "today": sum(1 for r in readings if day_key(r.get("created_at", "")) == today_key),
        "topics_covered": len(topic_counts),
        "most_asked": most_asked,
        "last7": last7,
        "recent": readings[:15],
        "members": members,
        "reset_requests": reset_requests,
    }


@api.post("/owner/customers/{cid}/active")
async def set_active(cid: str, body: ActiveBody, owner: dict = Depends(require_owner)):
    target = await db.users.find_one({"id": cid})
    if not target:
        raise HTTPException(404, "Customer not found")
    if target["role"] == "owner":
        raise HTTPException(400, "Cannot modify the owner account.")
    await db.users.update_one({"id": cid}, {"$set": {"active": body.active}, "$inc": {"token_version": 1}})
    return {"ok": True, "active": body.active}


@api.post("/owner/customers/{cid}/reset")
async def reset_customer(cid: str, body: ResetBody, owner: dict = Depends(require_owner)):
    target = await db.users.find_one({"id": cid})
    if not target:
        raise HTTPException(404, "Customer not found")
    if target["role"] == "owner":
        raise HTTPException(400, "Cannot reset the owner account here.")
    await db.users.update_one({"id": cid},
                              {"$set": {"password_hash": hash_pw(body.new_password)}, "$inc": {"token_version": 1}})
    await db.reset_requests.update_one({"user_id": cid}, {"$set": {"status": "done"}})
    return {"ok": True}


@api.get("/owner/knowledge")
async def list_knowledge(owner: dict = Depends(require_owner)):
    topics = [tk for tk in oracle.PACK.keys() if tk != "general"]
    base_counts = {tk: sum(len(oracle.PACK[tk].get(l, [])) for l in ("en", "hi", "hng")) for tk in topics}
    entries = await db.knowledge_entries.find({"deleted_at": None}).sort("created_at", -1).to_list(500)
    for e in entries:
        e.pop("_id", None)
    files = await db.kb_files.find({"deleted_at": None}).sort("created_at", -1).to_list(200)
    for f in files:
        f.pop("_id", None)
    custom_counts: dict[str, int] = {}
    for e in entries:
        custom_counts[e["topic"]] = custom_counts.get(e["topic"], 0) + 1
    return {"topics": topics, "base_counts": base_counts, "custom_counts": custom_counts,
            "entries": entries, "files": files}


@api.post("/owner/knowledge")
async def add_knowledge(body: KnowledgeBody, owner: dict = Depends(require_owner)):
    if body.topic not in oracle.PACK:
        raise HTTPException(400, "Unknown tradition.")
    doc = {
        "id": str(uuid.uuid4()),
        "topic": body.topic,
        "lang": body.lang,
        "text": body.text.strip(),
        "deleted_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.knowledge_entries.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@api.delete("/owner/knowledge/{eid}")
async def delete_knowledge(eid: str, owner: dict = Depends(require_owner)):
    await db.knowledge_entries.update_one({"id": eid}, {"$set": {"deleted_at": datetime.now(timezone.utc).isoformat()}})
    return {"ok": True}


@api.post("/owner/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    owner: dict = Depends(require_owner),
):
    from io import BytesIO
    import json as _json

    data = await file.read()

    if not data:
        raise HTTPException(400, "Empty file.")

    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(400, "File must be under 25 MB.")

    name = file.filename or "knowledge.txt"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else "txt"
    ct = file.content_type or "application/octet-stream"

    allowed = {"json", "txt", "md", "csv", "pdf", "docx"}

    if ext not in allowed:
        raise HTTPException(
            400,
            "Supported files: JSON, TXT, MD, CSV, PDF and DOCX."
        )

    now = datetime.now(timezone.utc).isoformat()
    bulk = []
    ingested = 0
    extracted_text = ""

    # -----------------------------------------
    # STRUCTURED JSON KNOWLEDGE PACK
    # Format:
    # {
    #   "Tarot": {
    #       "en": ["answer 1", "answer 2"],
    #       "hi": [...],
    #       "hng": [...]
    #   }
    # }
    # -----------------------------------------
    if ext == "json":
        try:
            parsed = _json.loads(data.decode("utf-8"))

            structured = False

            if isinstance(parsed, dict):
                for topic, langs in parsed.items():
                    if (
                        topic in oracle.PACK
                        and isinstance(langs, dict)
                    ):
                        structured = True

                        for lg, arr in langs.items():
                            if lg not in ("en", "hi", "hng"):
                                continue

                            if isinstance(arr, str):
                                arr = [arr]

                            if not isinstance(arr, list):
                                continue

                            for txt in arr:
                                if not isinstance(txt, str):
                                    continue

                                txt = txt.strip()

                                if not txt:
                                    continue

                                bulk.append({
                                    "id": str(uuid.uuid4()),
                                    "topic": topic,
                                    "lang": lg,
                                    "text": txt,
                                    "deleted_at": None,
                                    "created_at": now,
                                })

            if not structured:
                extracted_text = _json.dumps(
                    parsed,
                    ensure_ascii=False,
                    indent=2
                )

        except Exception as e:
            raise HTTPException(
                400,
                f"Invalid JSON file: {str(e)}"
            )

    # -----------------------------------------
    # TXT / MARKDOWN / CSV
    # -----------------------------------------
    elif ext in ("txt", "md", "csv"):
        try:
            extracted_text = data.decode("utf-8")
        except UnicodeDecodeError:
            extracted_text = data.decode(
                "latin-1",
                errors="ignore"
            )

    # -----------------------------------------
    # PDF
    # Text-based PDFs only
    # -----------------------------------------
    elif ext == "pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(data))
            pages = []

            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text)

            extracted_text = "\n\n".join(pages)

        except Exception as e:
            raise HTTPException(
                400,
                f"Could not read PDF: {str(e)}"
            )

    # -----------------------------------------
    # DOCX
    # -----------------------------------------
    elif ext == "docx":
        try:
            from docx import Document

            document = Document(BytesIO(data))

            extracted_text = "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.text.strip()
            )

        except Exception as e:
            raise HTTPException(
                400,
                f"Could not read DOCX: {str(e)}"
            )

    # -----------------------------------------
    # AUTO-INGEST NORMAL DOCUMENTS
    # -----------------------------------------
    if extracted_text.strip():

        cleaned = "\n".join(
            line.strip()
            for line in extracted_text.splitlines()
            if line.strip()
        )

        # Break large files into manageable knowledge chunks.
        chunk_size = 3500
        chunks = [
            cleaned[i:i + chunk_size]
            for i in range(0, len(cleaned), chunk_size)
            if cleaned[i:i + chunk_size].strip()
        ]

        # Filename can also help identify the tradition.
        filename_topics = []

        for topic in oracle.PACK.keys():
            if topic.lower() in name.lower():
                filename_topics.append(topic)

        for chunk in chunks:

            detected_topics = oracle.detect_topics(chunk)

            detected_topics = [
                topic
                for topic in detected_topics
                if topic in oracle.PACK
            ]

            if not detected_topics:
                detected_topics = filename_topics

            # General knowledge becomes fallback knowledge.
            if not detected_topics:
                detected_topics = ["General"]

            # Remove duplicate topics.
            detected_topics = list(
                dict.fromkeys(detected_topics)
            )

            for topic in detected_topics:

                # Make uploaded knowledge available
                # regardless of selected UI language.
                for lg in ("en", "hi", "hng"):

                    bulk.append({
                        "id": str(uuid.uuid4()),
                        "topic": topic,
                        "lang": lg,
                        "text": chunk,
                        "deleted_at": None,
                        "created_at": now,
                    })

    if bulk:
        await db.knowledge_entries.insert_many(
            [dict(item) for item in bulk]
        )

        ingested = len(bulk)

    if ingested == 0:
        raise HTTPException(
            400,
            "The file contained no readable knowledge."
        )

    file_id = str(uuid.uuid4())

    rec = {
        "id": file_id,
        "name": name,

        # Original file bytes are not stored.
        # Its usable knowledge is stored directly in MongoDB.
        "path": f"mongodb://knowledge/{file_id}",

        "content_type": ct,
        "size": len(data),
        "ingested": ingested,
        "deleted_at": None,
        "created_at": now,
    }

    await db.kb_files.insert_one(dict(rec))

    rec.pop("_id", None)

    return rec


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

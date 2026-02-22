"""
Language-Learning Chatbot - Main Application
FastAPI backend with static file serving
"""

from fastapi import FastAPI, Query, HTTPException, Request, Response, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Union, Dict, Tuple
from datetime import datetime, timedelta
from urllib.parse import quote
import hashlib
import hmac
import os
import re
import secrets
import uuid
import uvicorn

import db
import llm
import topics

app = FastAPI(title="Language-Learning Chatbot")

STARTER_COOLDOWN_MINUTES = int(os.getenv("CONVERSATION_STARTER_REFRESH_COOLDOWN_MINUTES", "5"))
STARTER_COUNT = int(os.getenv("CONVERSATION_STARTER_COUNT", "6"))
STARTER_PREVIEW_LENGTH = int(os.getenv("CONVERSATION_STARTER_PREVIEW_LENGTH", "80"))
STARTER_SUBREDDITS = [
    sub.strip()
    for sub in os.getenv(
        "CONVERSATION_STARTER_SUBREDDITS", "AskReddit,worldnews,technology,todayilearned,UpliftingNews"
    ).split(",")
    if sub.strip()
]
STARTER_SUBREDDIT_LIMIT = int(os.getenv("CONVERSATION_STARTER_SUB_LIMIT", "10"))

SESSION_COOKIE_NAME = "session_token"
SESSION_TTL_DAYS = 14
PASSWORD_MIN_LENGTH = 10
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,24}$")
INVITE_HASH_PREFIX = "sha256$"

AUTH_RATE_LIMIT_WINDOW_SECONDS = 15 * 60
AUTH_RATE_LIMIT_MAX_FAILURES = 10
AUTH_FAILURES_BY_IP: Dict[str, List[datetime]] = {}


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _build_preview(text: str) -> str:
    stripped = text.strip()
    if len(stripped) <= STARTER_PREVIEW_LENGTH:
        return stripped
    return stripped[: STARTER_PREVIEW_LENGTH - 1].rstrip() + "..."


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def _normalize_language(value: str) -> str:
    return value.strip().lower()


def _is_secure_request(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    if forwarded_proto.lower() == "https":
        return True
    return request.url.scheme == "https"


def _session_expiry_iso() -> str:
    return (datetime.utcnow() + timedelta(days=SESSION_TTL_DAYS)).isoformat()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _hash_invite_code(invite_code: str) -> str:
    normalized = invite_code.strip()
    return f"{INVITE_HASH_PREFIX}{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    if hasattr(hashlib, "scrypt"):
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
            dklen=64,
        )
        return "scrypt$16384$8$1$" + salt.hex() + "$" + digest.hex()

    iterations = 260000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2$sha256${iterations}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        parts = stored_hash.split("$")
        algorithm = parts[0]

        if algorithm == "scrypt":
            _, n_raw, r_raw, p_raw, salt_hex, digest_hex = parts
            if not hasattr(hashlib, "scrypt"):
                return False
            salt = bytes.fromhex(salt_hex)
            expected_digest = bytes.fromhex(digest_hex)
            computed_digest = hashlib.scrypt(
                password.encode("utf-8"),
                salt=salt,
                n=int(n_raw),
                r=int(r_raw),
                p=int(p_raw),
                dklen=len(expected_digest),
            )
            return hmac.compare_digest(computed_digest, expected_digest)

        if algorithm == "pbkdf2":
            _, hash_name, iterations_raw, salt_hex, digest_hex = parts
            salt = bytes.fromhex(salt_hex)
            expected_digest = bytes.fromhex(digest_hex)
            computed_digest = hashlib.pbkdf2_hmac(
                hash_name,
                password.encode("utf-8"),
                salt,
                int(iterations_raw),
                dklen=len(expected_digest),
            )
            return hmac.compare_digest(computed_digest, expected_digest)

        return False
    except Exception:
        return False


def _set_session_cookie(response: Response, token: str, request: Request) -> None:
    max_age = SESSION_TTL_DAYS * 24 * 60 * 60
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_is_secure_request(request),
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


def _prune_failures(ip_address: str) -> List[datetime]:
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=AUTH_RATE_LIMIT_WINDOW_SECONDS)
    recent = [ts for ts in AUTH_FAILURES_BY_IP.get(ip_address, []) if ts >= cutoff]
    AUTH_FAILURES_BY_IP[ip_address] = recent
    return recent


def _check_auth_rate_limit(ip_address: str) -> None:
    recent = _prune_failures(ip_address)
    if len(recent) >= AUTH_RATE_LIMIT_MAX_FAILURES:
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Please try again later.",
        )


def _record_auth_failure(ip_address: str) -> None:
    recent = _prune_failures(ip_address)
    recent.append(datetime.utcnow())
    AUTH_FAILURES_BY_IP[ip_address] = recent


def _clear_auth_failures(ip_address: str) -> None:
    AUTH_FAILURES_BY_IP.pop(ip_address, None)


def _build_next_path(request: Request) -> str:
    query_string = request.url.query
    if query_string:
        return f"{request.url.path}?{query_string}"
    return request.url.path


def _sanitize_next_path(raw_next: Optional[str]) -> str:
    if not raw_next:
        return "/"
    if not raw_next.startswith("/") or raw_next.startswith("//"):
        return "/"
    if raw_next == "/auth" or raw_next.startswith("/auth?"):
        return "/"
    return raw_next


def _auth_redirect_response(request: Request) -> RedirectResponse:
    next_path = _build_next_path(request)
    return RedirectResponse(url=f"/auth?next={quote(next_path, safe='')}", status_code=302)


def _user_payload(user_row: Dict) -> Dict:
    return {
        "id": user_row.get("id") or user_row.get("user_id"),
        "username": user_row["username"],
        "display_name": user_row["display_name"],
        "preferred_primary_lang": user_row.get("preferred_primary_lang"),
        "preferred_secondary_lang": user_row.get("preferred_secondary_lang"),
        "created_at": user_row["created_at"],
        "last_seen_at": user_row["last_seen_at"],
    }


async def _load_authenticated_session(request: Request) -> Tuple[Dict, str, str]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    token_hash = _hash_token(token)
    session = await db.get_active_session_by_token_hash(token_hash)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")

    return session, token, token_hash


async def _refresh_session_activity(token_hash: str, user_id: str) -> None:
    await db.extend_auth_session(token_hash, _session_expiry_iso())
    await db.touch_user(user_id)


async def require_authenticated_user(request: Request, response: Response) -> Dict:
    session, token, token_hash = await _load_authenticated_session(request)
    await _refresh_session_activity(token_hash, session["user_id"])
    _set_session_cookie(response, token, request)
    return _user_payload(session)


def _fallback_starters_from_posts(posts: List[Dict], desired_count: int) -> List[Dict]:
    """Generate simple conversation starters without LLM (best-effort)."""
    if not posts:
        return []
    starters = []
    seen_titles = set()
    sorted_posts = sorted(posts, key=lambda p: p.get("score", 0), reverse=True)
    for rank, post in enumerate(sorted_posts):
        if len(starters) >= desired_count:
            break
        title = (post.get("title") or "").strip()
        if not title:
            continue
        normalized_title = title.lower()
        if normalized_title in seen_titles:
            continue
        seen_titles.add(normalized_title)
        subreddit = post.get("subreddit") or "reddit"
        summary = (post.get("selftext") or "").strip()
        summary_snippet = summary[:160].replace("\n", " ")
        if summary_snippet:
            opener_body = summary_snippet
        else:
            opener_body = f"It's trending on r/{subreddit} right now."
        assistant_opening = (
            f"I just read on r/{subreddit} about \"{title}\". {opener_body} "
            "What do you think about it?"
        )
        starters.append(
            {
                "title": title[:60],
                "assistant_opening": assistant_opening.strip(),
                "subreddit": subreddit,
                "source_url": post.get("url"),
                "metadata": {"fallback": True, "reddit_id": post.get("id")},
            }
        )
    return starters


# Database initialization on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on app startup"""
    await db.init_db()


# Request/Response models
class ChatRequest(BaseModel):
    """Chat message request"""

    conversation_id: Optional[str] = None
    messages: List[dict]
    language: str
    mode: str = "chat"
    is_primary_lang: bool = True
    primary_lang: Optional[str] = None
    secondary_lang: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat message response"""

    conversation_id: str
    assistant_text: str
    assistant_lang: str


class TranslateRequest(BaseModel):
    """Translation request"""

    text: Union[str, List[str]]
    source_lang: str
    target_lang: str


class TranslateResponse(BaseModel):
    """Translation response"""

    translated_text: Union[str, List[str]]


class Message(BaseModel):
    """Message object"""

    id: str
    role: str
    text: str
    original_lang: str
    timestamp: str


class ConversationResponse(BaseModel):
    """Conversation history response"""

    conversation_id: str
    primary_lang: str
    secondary_lang: str
    mode: str
    messages: List[Message]


class ConversationStarterSummary(BaseModel):
    """Conversation starter summary for landing page."""

    id: str
    title: str
    preview: str


class ConversationStarterListResponse(BaseModel):
    generated_at: Optional[str]
    starters: List[ConversationStarterSummary]


class ConversationStarterDetailResponse(BaseModel):
    id: str
    title: str
    assistant_opening: str
    source_url: Optional[str]
    subreddit: Optional[str]


class RefreshResponse(BaseModel):
    count: int
    generated_at: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str
    invite_code: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    preferred_primary_lang: Optional[str] = None
    preferred_secondary_lang: Optional[str] = None


class UserProfile(BaseModel):
    id: str
    username: str
    display_name: str
    preferred_primary_lang: Optional[str]
    preferred_secondary_lang: Optional[str]
    created_at: str
    last_seen_at: str


class AuthUserResponse(BaseModel):
    user: UserProfile


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True}


@app.post("/api/auth/register", response_model=AuthUserResponse)
async def register(payload: RegisterRequest, request: Request, response: Response):
    ip_address = _get_client_ip(request)
    _check_auth_rate_limit(ip_address)

    invite_hash = await db.get_beta_invite_code_hash()
    if not invite_hash:
        raise HTTPException(status_code=503, detail="Registration is currently unavailable.")

    if not hmac.compare_digest(_hash_invite_code(payload.invite_code), invite_hash):
        _record_auth_failure(ip_address)
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    username = _normalize_username(payload.username)
    if not USERNAME_RE.match(username):
        raise HTTPException(status_code=422, detail="Username must match ^[a-z0-9_]{3,24}$")

    if len(payload.password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Password must be at least {PASSWORD_MIN_LENGTH} characters.",
        )

    existing = await db.get_user_by_username(username)
    if existing:
        raise HTTPException(status_code=409, detail="Username is already taken.")

    display_name = payload.display_name.strip() or username
    user_id = str(uuid.uuid4())

    created = await db.create_user(
        user_id=user_id,
        username=username,
        password_hash=_hash_password(payload.password),
        display_name=display_name,
    )
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create account.")

    user = await db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=500, detail="Failed to load account.")

    session_token = secrets.token_urlsafe(48)
    session_created = await db.create_auth_session(
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        token_hash=_hash_token(session_token),
        expires_at=_session_expiry_iso(),
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent", "unknown"),
    )
    if not session_created:
        raise HTTPException(status_code=500, detail="Failed to create session.")

    _set_session_cookie(response, session_token, request)
    _clear_auth_failures(ip_address)
    return AuthUserResponse(user=UserProfile(**_user_payload(user)))


@app.post("/api/auth/login", response_model=AuthUserResponse)
async def login(payload: LoginRequest, request: Request, response: Response):
    ip_address = _get_client_ip(request)
    _check_auth_rate_limit(ip_address)

    username = _normalize_username(payload.username)
    if not USERNAME_RE.match(username):
        _record_auth_failure(ip_address)
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    user = await db.get_user_by_username(username)
    if not user or not _verify_password(payload.password, user["password_hash"]):
        _record_auth_failure(ip_address)
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    session_token = secrets.token_urlsafe(48)
    session_created = await db.create_auth_session(
        session_id=str(uuid.uuid4()),
        user_id=user["id"],
        token_hash=_hash_token(session_token),
        expires_at=_session_expiry_iso(),
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent", "unknown"),
    )
    if not session_created:
        raise HTTPException(status_code=500, detail="Failed to create session.")

    await db.touch_user(user["id"])
    fresh_user = await db.get_user_by_id(user["id"])
    if not fresh_user:
        raise HTTPException(status_code=500, detail="Failed to load account.")

    _set_session_cookie(response, session_token, request)
    _clear_auth_failures(ip_address)
    return AuthUserResponse(user=UserProfile(**_user_payload(fresh_user)))


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        await db.revoke_auth_session(_hash_token(token))
    _clear_session_cookie(response)
    return {"ok": True}


@app.get("/api/me", response_model=UserProfile)
async def get_me(current_user: Dict = Depends(require_authenticated_user)):
    return UserProfile(**current_user)


@app.patch("/api/me", response_model=UserProfile)
async def update_me(
    payload: ProfileUpdateRequest,
    current_user: Dict = Depends(require_authenticated_user),
):
    if hasattr(payload, "model_dump"):
        updates = payload.model_dump(exclude_unset=True)
    else:
        updates = payload.dict(exclude_unset=True)
    if not updates:
        user = await db.get_user_by_id(current_user["id"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        return UserProfile(**_user_payload(user))

    if "display_name" in updates:
        display_name = updates["display_name"]
        if display_name is None or len(display_name.strip()) == 0:
            raise HTTPException(status_code=422, detail="Display name cannot be empty.")
        updates["display_name"] = display_name.strip()

    if "preferred_primary_lang" in updates and updates["preferred_primary_lang"] is not None:
        updates["preferred_primary_lang"] = _normalize_language(updates["preferred_primary_lang"])

    if "preferred_secondary_lang" in updates and updates["preferred_secondary_lang"] is not None:
        updates["preferred_secondary_lang"] = _normalize_language(updates["preferred_secondary_lang"])

    saved = await db.update_user_profile(
        user_id=current_user["id"],
        display_name=updates.get("display_name"),
        preferred_primary_lang=updates.get("preferred_primary_lang"),
        preferred_secondary_lang=updates.get("preferred_secondary_lang"),
    )
    if not saved:
        raise HTTPException(status_code=500, detail="Failed to update profile.")

    user = await db.get_user_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    return UserProfile(**_user_payload(user))


@app.post("/api/conversation_starters/refresh", response_model=RefreshResponse)
async def refresh_conversation_starters(
    request: Request,
    current_user: Dict = Depends(require_authenticated_user),
):
    """Protected endpoint to trigger conversation starter refresh with cooldown."""
    _ = current_user
    ip_address = _get_client_ip(request)
    now = datetime.utcnow()
    last_refresh = await db.get_last_refresh_time(ip_address)
    cooldown_delta = timedelta(minutes=STARTER_COOLDOWN_MINUTES)

    if last_refresh and now - last_refresh < cooldown_delta:
        remaining = cooldown_delta - (now - last_refresh)
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Please wait before refreshing again.",
                "retry_after_seconds": int(remaining.total_seconds()),
            },
        )

    try:
        reddit_posts = await topics.fetch_multiple_subreddits(
            STARTER_SUBREDDITS or ["AskReddit"],
            limit_per_subreddit=STARTER_SUBREDDIT_LIMIT,
            time_filter="day",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch Reddit posts: {exc}")

    if not reddit_posts:
        raise HTTPException(status_code=502, detail="No Reddit posts available for starters.")

    fallback_used = False
    try:
        starters_from_llm = await llm.generate_conversation_starters_from_posts(
            reddit_posts, desired_count=STARTER_COUNT
        )
    except Exception as exc:
        print(f"LLM starter generation failed, switching to fallback. Reason: {exc}")
        starters_from_llm = _fallback_starters_from_posts(reddit_posts, STARTER_COUNT)
        fallback_used = True
        if not starters_from_llm:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate conversation starters and no fallback available: {exc}",
            )

    generated_at = now.isoformat()
    starters_payload = []
    for idx, starter in enumerate(starters_from_llm):
        starters_payload.append(
            {
                "id": str(uuid.uuid4()),
                "title": starter["title"],
                "opener": starter["assistant_opening"],
                "source_url": starter.get("source_url"),
                "subreddit": starter.get("subreddit"),
                "rank": idx,
                "metadata": starter.get("metadata", {}),
                "generated_by": "fallback_stub" if fallback_used else "reddit_llm",
                "created_at": generated_at,
            }
        )

    inserted = await db.replace_conversation_starters(starters_payload)
    await db.update_refresh_time(ip_address)

    return RefreshResponse(count=inserted, generated_at=generated_at)


@app.get("/api/conversation_starters", response_model=ConversationStarterListResponse)
async def list_conversation_starters(current_user: Dict = Depends(require_authenticated_user)):
    _ = current_user
    starters, latest_time = await db.get_conversation_starters()
    summaries = [
        ConversationStarterSummary(
            id=item["id"],
            title=item["title"],
            preview=_build_preview(item["opener"]),
        )
        for item in starters
    ]
    return ConversationStarterListResponse(generated_at=latest_time, starters=summaries)


@app.get("/api/conversation_starters/{starter_id}", response_model=ConversationStarterDetailResponse)
async def get_conversation_starter(
    starter_id: str,
    current_user: Dict = Depends(require_authenticated_user),
):
    _ = current_user
    starter = await db.get_conversation_starter_by_id(starter_id)
    if not starter:
        raise HTTPException(status_code=404, detail="Conversation starter not found.")
    return ConversationStarterDetailResponse(
        id=starter["id"],
        title=starter["title"],
        assistant_opening=starter["opener"],
        source_url=starter["source_url"],
        subreddit=starter["subreddit"],
    )


@app.get("/api/topics")
async def legacy_topics(current_user: Dict = Depends(require_authenticated_user)):
    """Legacy endpoint kept for backward compatibility."""
    _ = current_user
    starters, _latest_time = await db.get_conversation_starters()
    if not starters:
        return []
    topics_payload = []
    for starter in starters:
        topics_payload.append(
            {
                "id": starter["id"],
                "title": starter["title"],
                "description": starter["opener"],
                "icon": "💬",
                "starter_message": starter["opener"],
            }
        )
    return topics_payload


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: Dict = Depends(require_authenticated_user),
):
    """
    Send a chat message and receive assistant response.
    Persists conversation ownership and messages in database.
    """

    conversation_id = payload.conversation_id or str(uuid.uuid4())

    if payload.conversation_id:
        conversation = await db.get_conversation(conversation_id, user_id=current_user["id"])
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        preferred_primary = current_user.get("preferred_primary_lang")
        preferred_secondary = current_user.get("preferred_secondary_lang")
        primary_lang = payload.primary_lang or preferred_primary or payload.language
        secondary_lang = payload.secondary_lang or preferred_secondary or "en"

        if payload.is_primary_lang:
            primary_lang = payload.primary_lang or preferred_primary or payload.language
            secondary_lang = payload.secondary_lang or preferred_secondary or "en"
        else:
            primary_lang = payload.primary_lang or preferred_primary or "en"
            secondary_lang = payload.secondary_lang or preferred_secondary or payload.language

        if primary_lang == secondary_lang:
            secondary_lang = "en" if primary_lang != "en" else "es"

        created = await db.create_conversation(
            conversation_id=conversation_id,
            primary_lang=primary_lang,
            secondary_lang=secondary_lang,
            mode=payload.mode,
            user_id=current_user["id"],
        )
        if not created:
            raise HTTPException(status_code=500, detail="Failed to create conversation")

    latest_user_message = None
    for message in reversed(payload.messages):
        if message.get("role") == "user":
            latest_user_message = (message.get("text") or "").strip()
            if latest_user_message:
                break

    if latest_user_message:
        await db.insert_message(
            conversation_id=conversation_id,
            role="user",
            lang=payload.language,
            text=latest_user_message,
        )

    try:
        messages_to_use = payload.messages[-20:] if len(payload.messages) > 20 else payload.messages
        assistant_text = await llm.generate_reply(
            messages=messages_to_use,
            target_lang=payload.language,
            mode=payload.mode,
            is_primary_lang=payload.is_primary_lang,
        )

        if not assistant_text or len(assistant_text.strip()) == 0:
            raise RuntimeError("Empty response from LLM")

    except Exception as exc:
        print(f"LLM generation failed: {exc}")
        assistant_text = "Sorry something went wrong. Let's try again!"

    await db.insert_message(
        conversation_id=conversation_id,
        role="assistant",
        lang=payload.language,
        text=assistant_text,
    )

    return ChatResponse(
        conversation_id=conversation_id,
        assistant_text=assistant_text,
        assistant_lang=payload.language,
    )


@app.post("/api/translate", response_model=TranslateResponse)
async def translate(
    payload: TranslateRequest,
    current_user: Dict = Depends(require_authenticated_user),
):
    """Translate text from source to target language."""
    _ = current_user

    if isinstance(payload.text, str):
        text = [payload.text]
    else:
        text = payload.text

    translated_text: List[str] = []
    first_new_msg_index = 0
    for item in text:
        cached = await db.get_translation(item)
        if cached:
            translated_text.append(cached)
            first_new_msg_index += 1
        else:
            break

    if first_new_msg_index < len(text):
        text_to_translate = text[first_new_msg_index:]
        new_translations = await llm.translate_text(text_to_translate, payload.target_lang)
        for index, item in enumerate(text_to_translate):
            await db.save_translation(item, new_translations[index])
        translated_text.extend(new_translations)

    if isinstance(payload.text, str):
        if not translated_text:
            return TranslateResponse(translated_text="")
        return TranslateResponse(translated_text=translated_text[0])

    return TranslateResponse(translated_text=translated_text)


@app.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation_history(
    conversation_id: str,
    display_lang: Optional[str] = Query(default="en"),
    current_user: Dict = Depends(require_authenticated_user),
):
    """Get conversation history by ID from database."""
    _ = display_lang

    conversation = await db.get_conversation(conversation_id, user_id=current_user["id"])
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_data = await db.get_messages(conversation_id)
    messages = []
    for msg in messages_data:
        messages.append(
            Message(
                id=str(msg["id"]),
                role=msg["role"],
                text=msg["text"],
                original_lang=msg["lang"],
                timestamp=msg["created_at"],
            )
        )

    return ConversationResponse(
        conversation_id=conversation["id"],
        primary_lang=conversation["primary_lang"],
        secondary_lang=conversation["secondary_lang"],
        mode=conversation["mode"],
        messages=messages,
    )


# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/auth")
async def read_auth(request: Request):
    """Serve login/register page."""
    next_path = _sanitize_next_path(request.query_params.get("next"))

    try:
        session, token, token_hash = await _load_authenticated_session(request)
        await _refresh_session_activity(token_hash, session["user_id"])
        response = RedirectResponse(url=next_path, status_code=302)
        _set_session_cookie(response, token, request)
        return response
    except HTTPException:
        return FileResponse("static/auth.html")


@app.get("/")
async def read_root(request: Request):
    """Serve the landing page for authenticated users."""
    try:
        session, token, token_hash = await _load_authenticated_session(request)
    except HTTPException:
        return _auth_redirect_response(request)

    await _refresh_session_activity(token_hash, session["user_id"])
    response = FileResponse("static/landing.html")
    _set_session_cookie(response, token, request)
    return response


@app.get("/chat")
async def read_chat(request: Request):
    """Serve chat page for authenticated users."""
    try:
        session, token, token_hash = await _load_authenticated_session(request)
    except HTTPException:
        return _auth_redirect_response(request)

    await _refresh_session_activity(token_hash, session["user_id"])
    response = FileResponse("static/chat.html")
    _set_session_cookie(response, token, request)
    return response


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

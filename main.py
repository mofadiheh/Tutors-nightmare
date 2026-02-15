"""
Language-Learning Chatbot - Main Application
FastAPI backend with static file serving
"""

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Union, Dict
from datetime import datetime, timedelta
import os
import uvicorn
import uuid
import asyncio
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
    return stripped[: STARTER_PREVIEW_LENGTH - 1].rstrip() + "…"


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
    messages: List[dict]  # List of message dicts with 'role', 'text'
    language: str  # Language of the conversation
    mode: str = "chat"  # "chat" or "tutor"
    is_primary_lang: bool = True  # Whether the conversation language is primary (learning) or secondary (native)

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
    role: str  # "user" or "assistant"
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

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True}

@app.post("/api/conversation_starters/refresh", response_model=RefreshResponse)
async def refresh_conversation_starters(request: Request):
    """Public endpoint to trigger conversation starter refresh with cooldown."""
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
async def list_conversation_starters():
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
async def get_conversation_starter(starter_id: str):
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
async def legacy_topics():
    """Legacy endpoint kept for backward compatibility."""
    starters, _ = await db.get_conversation_starters()
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

# Chat endpoint (with LLM integration - Milestone I2)
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a chat message and receive assistant response
    Now uses real LLM via OpenRouter (Milestone I2)
    Persists to database (Milestone H2)
    """

    # Generate or use existing conversation ID
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # Generate LLM response
    try:
        if len(request.messages) > 20:
            messages_to_use = request.messages[-20:]
        else:
            messages_to_use = request.messages
        assistant_text = await llm.generate_reply(
            messages=messages_to_use,
            target_lang=request.language,
            mode=request.mode,
            is_primary_lang=request.is_primary_lang
        )

        # Ensure we got a valid response
        if not assistant_text or len(assistant_text.strip()) == 0:
            raise Exception("Empty response from LLM")

    except Exception as e:
        print(f"LLM generation failed: {e}")
        print("Falling back to stubbed response...")

        stubbed_response = "Sorry something went wrong. Let's try again!"

        assistant_text = stubbed_response


    return ChatResponse(
        conversation_id=conversation_id,
        assistant_text=assistant_text,
        assistant_lang=request.language
    )

# Translation endpoint (stubbed for now - Milestone D2)
@app.post("/api/translate", response_model=TranslateResponse)
async def translate(request: TranslateRequest):
    """
    Translate text from source to target language
    Currently returns stubbed translations - will be replaced with real translation in Phase 2
    """
    print(f"Received translation request from {request.source_lang} to {request.target_lang}")
    if isinstance(request.text, str):
        text = [request.text]
    else:
        text = request.text
    text_to_translate = []
    translated_text = []
    first_new_msg_index = 0
    for t in text:
        cached = await db.get_translation(t)
        if cached:
            translated_text.append(cached)
            first_new_msg_index += 1
        else:
            break

    if first_new_msg_index < len(text):
        text_to_translate = text[first_new_msg_index:]
        new_translations = await llm.translate_text(text_to_translate, request.target_lang)
        for i, t in enumerate(text_to_translate):
            # Save bidirectional mapping (original <-> translated)
            await db.save_translation(t, new_translations[i])
        translated_text.extend(new_translations)
    if isinstance(request.text, str):
        return TranslateResponse(translated_text=translated_text[0])
    else:
        return TranslateResponse(translated_text=translated_text)
            

    # Stub logic: prefix text with translation marker
    if isinstance(request.text, str):
        translated = f"[Translated to {request.target_lang.upper()}] {request.text}"
        return TranslateResponse(translated_text=translated)
    else:
        # Handle array of strings
        translated = [f"[Translated to {request.target_lang.upper()}] {t}" for t in request.text]
        return TranslateResponse(translated_text=translated)

# Conversation history endpoint (with database - Milestone H2)
@app.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation_history(
    conversation_id: str,
    display_lang: Optional[str] = Query(default="en")
):
    """
    Get conversation history by ID from database
    Returns messages in original language (translation handled separately)
    """
    # Check if conversation exists
    conversation = await db.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get all messages for this conversation
    messages_data = await db.get_messages(conversation_id)
    
    # Format messages for response
    messages = []
    for msg in messages_data:
        messages.append(Message(
            id=str(msg['id']),
            role=msg['role'],
            text=msg['text'],
            original_lang=msg['lang'],
            timestamp=msg['created_at']
        ))
    
    return ConversationResponse(
        conversation_id=conversation['id'],
        primary_lang=conversation['primary_lang'],
        secondary_lang=conversation['secondary_lang'],
        mode=conversation['mode'],
        messages=messages
    )

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve landing page at root
@app.get("/")
async def read_root():
    """Serve the landing page"""
    return FileResponse("static/landing.html")

# Serve chat page
@app.get("/chat")
async def read_chat():
    """Serve the chat page"""
    return FileResponse("static/chat.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

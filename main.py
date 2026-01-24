"""
Language-Learning Chatbot - Main Application
FastAPI backend with static file serving
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Union
import uvicorn
import uuid
import asyncio
import db
import llm

app = FastAPI(title="Language-Learning Chatbot")

# Database initialization on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on app startup"""
    await db.init_db()

# Request/Response models
class ChatRequest(BaseModel):
    """Chat message request"""
    conversation_id: Optional[str] = None
    user_text: str
    primary_lang: str = "es"  # User's native/learning language
    secondary_lang: str = "en"  # Assistant's language
    display_lang: str = "es"  # Currently displayed language
    mode: str = "chat"  # "chat" or "tutor"

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

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True}

# Topics endpoint (stubbed for now - Milestone B2)
@app.get("/api/topics")
async def get_topics(lang: Optional[str] = Query(default="en")):
    """
    Get topic starters for conversation
    Currently returns stubbed data - will be replaced with real topics in Phase 2
    """
    # Stubbed topics - same for all languages for now
    topics = [
        {
            "id": "travel",
            "title": "Travel",
            "description": "Discuss travel experiences and dream destinations",
            "icon": "✈️"
        },
        {
            "id": "food",
            "title": "Food",
            "description": "Talk about cuisine, recipes, and dining experiences",
            "icon": "🍕"
        },
        {
            "id": "hobbies",
            "title": "Hobbies",
            "description": "Share your interests and leisure activities",
            "icon": "🎨"
        },
        {
            "id": "work",
            "title": "Work",
            "description": "Discuss career, workplace, and professional life",
            "icon": "💼"
        },
        {
            "id": "culture",
            "title": "Culture",
            "description": "Explore traditions, arts, and cultural differences",
            "icon": "🎭"
        }
    ]
    
    return topics

# Chat endpoint (with LLM integration - Milestone I2)
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a chat message and receive assistant response
    Now uses real LLM via OpenRouter (Milestone I2)
    Persists to database (Milestone H2)
    """
    print(f"Received chat request. Primary Lang: {request.primary_lang}, Secondary Lang: {request.secondary_lang}, Display Lang: {request.display_lang}, mode: {request.mode}")

    # Generate or use existing conversation ID
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # Create conversation record if new
    if not request.conversation_id:
        await db.create_conversation(
            conversation_id=conversation_id,
            primary_lang=request.primary_lang,
            secondary_lang=request.secondary_lang,
            mode=request.mode
        )

    # Insert user message into database
    await db.insert_message(
        conversation_id=conversation_id,
        role="user",
        lang=request.primary_lang,
        text=request.user_text
    )

    # Get conversation history for LLM context
    messages_data = await db.get_messages(conversation_id)

    # Format messages for LLM (include the new user message)
    conversation_history = []
    for msg in messages_data:
        conversation_history.append({
            "role": msg["role"],
            "text": msg["text"]
        })

    # Generate LLM response
    try:
        assistant_text = await llm.generate_reply(
            messages=conversation_history,
            target_lang=request.secondary_lang,
            mode=request.mode
        )

        # Ensure we got a valid response
        if not assistant_text or len(assistant_text.strip()) == 0:
            raise Exception("Empty response from LLM")

    except Exception as e:
        print(f"LLM generation failed: {e}")
        print("Falling back to stubbed response...")

        # Fallback to stubbed responses
        if request.mode == "tutor":
            stubbed_response = "Sorry something went wrong. Let's try again!"
        else:
            stubbed_response = "Sorry something went wrong. Let's try again!"

        assistant_text = stubbed_response.format(lang=request.secondary_lang.upper())

    # Insert assistant message into database
    await db.insert_message(
        conversation_id=conversation_id,
        role="assistant",
        lang=request.secondary_lang,
        text=assistant_text
    )

    return ChatResponse(
        conversation_id=conversation_id,
        assistant_text=assistant_text,
        assistant_lang=request.secondary_lang
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

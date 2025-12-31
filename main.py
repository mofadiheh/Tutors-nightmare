"""
Language-Learning Chatbot - Main Application
FastAPI backend with static file serving
"""

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
import uuid
import asyncio

app = FastAPI(title="Language-Learning Chatbot")

# Request/Response models
class ChatRequest(BaseModel):
    """Chat message request"""
    conversation_id: Optional[str] = None
    user_text: str
    user_lang: str = "es"
    display_lang: str = "es"
    mode: str = "chat"  # "chat" or "tutor"

class ChatResponse(BaseModel):
    """Chat message response"""
    conversation_id: str
    assistant_text: str
    assistant_lang: str

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

# Chat endpoint (stubbed for now - Milestone C2)
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a chat message and receive assistant response
    Currently returns stubbed responses - will be replaced with real AI in Phase 2
    """
    # Add 1-2 second delay to simulate LLM processing
    await asyncio.sleep(1.5)
    
    # Generate or use existing conversation ID
    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    # Stubbed responses based on mode
    if request.mode == "tutor":
        # Tutor mode: provide teaching-focused responses
        stubbed_responses = [
            "That's a great question! Let me explain that in {lang}. [This is a stubbed tutor response]",
            "Good effort! Here's a tip: [Stubbed grammar tip in {lang}]",
            "Excellent! Let's practice that concept more. [Stubbed tutor feedback in {lang}]",
            "I notice you're working on this pattern. [Stubbed insight in {lang}]",
        ]
    else:
        # Chat mode: provide conversational responses
        stubbed_responses = [
            "That's interesting! Tell me more about that. [Stubbed response in {lang}]",
            "I understand. What do you think about...? [Stubbed response in {lang}]",
            "That sounds wonderful! [Stubbed response in {lang}]",
            "I see. How does that make you feel? [Stubbed response in {lang}]",
        ]
    
    # Select response based on message length (pseudo-random)
    response_index = len(request.user_text) % len(stubbed_responses)
    assistant_text = stubbed_responses[response_index].format(lang=request.user_lang.upper())
    
    return ChatResponse(
        conversation_id=conversation_id,
        assistant_text=assistant_text,
        assistant_lang=request.user_lang
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

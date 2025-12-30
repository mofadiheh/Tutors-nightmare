"""
Language-Learning Chatbot - Main Application
FastAPI backend with static file serving
"""

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional
import uvicorn

app = FastAPI(title="Language-Learning Chatbot")

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

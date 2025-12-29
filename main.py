"""
Language-Learning Chatbot - Main Application
FastAPI backend with static file serving
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI(title="Language-Learning Chatbot")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True}

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html at root
@app.get("/")
async def read_root():
    """Serve the main page"""
    return FileResponse("static/index.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

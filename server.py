#!/usr/bin/env python3
"""
server.py - Web server for OpenAI Storybook Generator
Serves the frontend and provides API endpoints for story generation
"""
import os
import json
import asyncio
import pathlib
from typing import Dict, List, Optional

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import Mount
from pydantic import BaseModel
import uvicorn

from story_gen import build_book

# Define paths
ROOT = pathlib.Path().resolve()
STORIES_DIR = ROOT / "stories"
FRONTEND_DIR = ROOT / "frontend"

# Create stories directory if it doesn't exist
STORIES_DIR.mkdir(exist_ok=True)

# Initialize FastAPI app
app = FastAPI(title="Story Forest API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request/response models
class StoryRequest(BaseModel):
    topic: str
    style: str
    pages: int = 6

class StoryResponse(BaseModel):
    title: str
    cover_image: str

# API Endpoints

# Story directory listing endpoint
@app.get("/api/stories")
async def list_stories():
    """List all story directories"""
    if not STORIES_DIR.exists():
        return []
    
    # Get all directories in the stories directory
    story_dirs = [d.name for d in STORIES_DIR.iterdir() if d.is_dir()]
    return story_dirs

# Convert story.json format to frontend expected format
def convert_story_format(story_path: pathlib.Path) -> List[Dict]:
    """Convert the story.json from backend format to frontend format"""
    try:
        with open(story_path, "r") as f:
            story_data = json.load(f)
        
        # Check if the story is already in frontend format (first item is an object with title)
        if isinstance(story_data, list) and len(story_data) > 0 and "title" in story_data[0]:
            return story_data
        
        # Create the frontend expected format
        # First item is metadata
        frontend_story = [{
            "title": story_data["title"]
        }]
        
        # Add pages
        for page in story_data["pages"]:
            frontend_story.append({
                "page": page["page"],
                "text": page["text"],
                "image_description": page["image_description"]
            })
        
        return frontend_story
    except Exception as e:
        print(f"Error converting story format: {e}")
        # Return a simple default structure in case of errors
        return [{
            "title": "Story"
        }]

# Generate story endpoint
@app.post("/api/story", response_model=StoryResponse)
async def generate_story(story_req: StoryRequest):
    """Generate a new story based on the provided topic and style"""
    try:
        # Call the build_book function from story_gen.py
        await build_book(
            topic=story_req.topic,
            style=story_req.style,
            n_pages=story_req.pages
        )
        
        # Find the most recently created story directory
        story_dirs = sorted([d for d in STORIES_DIR.iterdir() if d.is_dir()], 
                           key=lambda d: d.stat().st_mtime, reverse=True)
        
        if not story_dirs:
            raise HTTPException(status_code=500, detail="Story generation failed: No story directory found")
        
        latest_story = story_dirs[0]
        story_json_path = latest_story / "story.json"
        
        if not story_json_path.exists():
            raise HTTPException(status_code=500, detail=f"Story generation failed: No story.json in {latest_story.name}")
        
        # Convert the story.json to frontend format
        frontend_story = convert_story_format(story_json_path)
        
        # Save the frontend format story.json
        with open(story_json_path, "w") as f:
            json.dump(frontend_story, f, indent=2)
        
        # Return the response
        return {
            "title": frontend_story[0]["title"],
            "cover_image": f"/stories/{latest_story.name}/cover.png"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Story generation failed: {str(e)}")

# Root redirect to index.html
@app.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")

# Serve story JSON for individual stories
@app.get("/stories/{story_id}/story.json")
async def serve_story_json(story_id: str):
    story_path = STORIES_DIR / story_id / "story.json"
    if not story_path.exists():
        raise HTTPException(status_code=404, detail="Story not found")
    return FileResponse(story_path)

# Mount static directories for stories and static assets
# IMPORTANT: These mounts must be after all API routes to prevent conflicts
app.mount("/stories", StaticFiles(directory=str(STORIES_DIR)), name="stories")
app.mount("/book.js", StaticFiles(directory=str(FRONTEND_DIR), html=False), name="book_js")
app.mount("/book.html", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="book_html")
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

# Main entry point
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8600, reload=True)

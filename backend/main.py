from pathlib import Path
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .database import init_db, list_conversations
from .agent import VoiceAgent

BASE = Path(__file__).resolve().parent.parent
FRONTEND = BASE / "frontend"

app = FastAPI(title="Home Credit AI Voice Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agents = {}

class StartRequest(BaseModel):
    customer_name: str = "Customer"
    language: str = "English"

class ChatRequest(BaseModel):
    call_id: str
    text: str

class EndRequest(BaseModel):
    call_id: str

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")

@app.get("/style.css")
def css():
    return FileResponse(FRONTEND / "style.css", media_type="text/css")

@app.get("/script.js")
def js():
    return FileResponse(FRONTEND / "script.js", media_type="application/javascript")

@app.post("/api/start")
def start(req: StartRequest):
    agent = VoiceAgent(req.customer_name, req.language)
    agents[agent.call_id] = agent
    return agent.start()

@app.post("/api/chat")
def chat(req: ChatRequest):
    agent = agents.get(req.call_id)
    if not agent:
        return {"error": "Call not found. Start a new call."}
    result = agent.process(req.text)
    if result["finished"]:
        agent.save()
    return result

@app.post("/api/end")
def end_call(req: EndRequest):
    agent = agents.get(req.call_id)
    if not agent:
        return {"error": "Call not found. Start a new call."}
    agent.state.status = "ENDED"
    agent.state.completed = True
    agent.save()
    return agent.payload("Call ended and saved.")

@app.get("/api/conversations")
def conversations():
    return list_conversations()

"""
FastAPI backend for Medical AI Assistant.
Run: uvicorn api:app --reload
"""
import base64
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chains import answer_query

app = FastAPI(title="Medical AI Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat/ask", response_model=ChatResponse)
def chat_ask(req: ChatRequest) -> ChatResponse:
    """Ask a text-only question about medicine."""
    history = [{"role": m.role, "content": m.content} for m in req.history]
    try:
        reply = answer_query(query=req.message, history=history)
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/find", response_model=ChatResponse)
async def chat_find(
    image: UploadFile = File(...),
    question: Optional[str] = Form(None),
    history_json: Optional[str] = Form("[]"),
) -> ChatResponse:
    """
    Find medicine by image (camera or gallery).
    question is optional text (e.g. "Що це за препарат?").
    """
    import json
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    try:
        body = await image.read()
        image_b64 = base64.b64encode(body).decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")
    try:
        history = json.loads(history_json or "[]")
    except json.JSONDecodeError:
        history = []
    history = [{"role": m.get("role"), "content": m.get("content", "")} for m in history]
    try:
        reply = answer_query(
            query=question or "Що це за препарат?",
            history=history,
            image_base64=image_b64,
        )
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
FastAPI backend for Medical AI Assistant.
Auth: Google OAuth + JWT. Data: SQLite (users → conversations → messages).
Run: uvicorn api:app --reload
"""
import base64
import json
import secrets
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from chains import answer_query
from db import (
    init_db,
    user_get_or_create,
    conversation_create,
    conversation_list,
    conversation_get,
    conversation_find_empty,
    conversation_delete,
    conversation_update_title,
    message_add,
    messages_list,
    messages_last_n_for_context,
    CONTEXT_WINDOW_SIZE,
)
from auth import (
    build_google_login_url,
    exchange_code_for_user,
    create_jwt,
    get_current_user_id,
    FRONTEND_URL,
)

app = FastAPI(title="Medical AI Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# --- Auth ---

@app.get("/auth/google")
def auth_google():
    """Redirect to Google OAuth. Set API_BASE_URL in env if behind proxy."""
    import os
    base = os.getenv("API_BASE_URL", "http://localhost:8000")
    redirect_uri = f"{base.rstrip('/')}/auth/google/callback"
    state = secrets.token_urlsafe(16)
    url = build_google_login_url(redirect_uri, state)
    return RedirectResponse(url=url)


@app.get("/auth/google/callback")
async def auth_google_callback(code: Optional[str] = None, state: Optional[str] = None):
    """Exchange code for user, create JWT, redirect to frontend with token."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    import os
    base = os.getenv("API_BASE_URL", "http://localhost:8000")
    redirect_uri = f"{base.rstrip('/')}/auth/google/callback"
    user_info = await exchange_code_for_user(code, redirect_uri)
    google_id = user_info.get("id") or user_info.get("sub", "")
    email = user_info.get("email")
    name = user_info.get("name")
    avatar_url = user_info.get("picture")
    user = user_get_or_create(google_id, email=email, name=name, avatar_url=avatar_url)
    token = create_jwt(user["id"], google_id)
    # Redirect to frontend with token in hash (so it's not sent to server logs)
    return RedirectResponse(url=f"{FRONTEND_URL}#token={token}")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    history: list[ChatMessage] = []  # optional; if conversation_id set, history loaded from DB


class ChatResponse(BaseModel):
    reply: str
    conversation_id: int


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/auth/me")
def auth_me(user_id: int = Depends(get_current_user_id)):
    """Return current user info (for UI)."""
    from db import user_get_by_id
    user = user_get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user["id"], "email": user["email"], "name": user["name"], "avatar_url": user["avatar_url"]}


# --- Conversations ---

class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str


@app.get("/conversations", response_model=list[ConversationOut])
def list_conversations(user_id: int = Depends(get_current_user_id)):
    convos = conversation_list(user_id)
    return [ConversationOut(id=c["id"], title=c["title"], created_at=c["created_at"], updated_at=c["updated_at"]) for c in convos]


@app.post("/conversations", response_model=ConversationOut)
def create_conversation(
    title: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
):
    c = conversation_create(user_id, title=title or "Нова розмова", allow_if_empty_exists=False)
    if c is None:
        c = conversation_find_empty(user_id)
        if not c:
            raise HTTPException(status_code=500, detail="No empty conversation found")
    return ConversationOut(id=c["id"], title=c["title"], created_at=c["created_at"], updated_at=c["updated_at"])


@app.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    user_id: int = Depends(get_current_user_id),
):
    conv = conversation_get(conversation_id, user_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = messages_list(conversation_id, user_id)
    return {"messages": [{"role": m["role"], "content": m["content"]} for m in msgs]}


@app.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    user_id: int = Depends(get_current_user_id),
):
    if not conversation_delete(conversation_id, user_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True}


# --- Chat (require auth + conversation) ---

def _maybe_update_conversation_title(conv_id: int, user_id: int, first_message: str) -> None:
    conv = conversation_get(conv_id, user_id)
    if conv and (conv.get("title") == "Нова розмова" or not conv.get("title")):
        title = (first_message.strip() or "Розмова")[:50]
        if title:
            conversation_update_title(conv_id, user_id, title)


def _ensure_conversation(conversation_id: Optional[int], user_id: int) -> int:
    if conversation_id is not None:
        conv = conversation_get(conversation_id, user_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation_id
    empty = conversation_find_empty(user_id)
    if empty:
        return empty["id"]
    c = conversation_create(user_id, title="Нова розмова", allow_if_empty_exists=True)
    return c["id"]


@app.post("/chat/ask", response_model=ChatResponse)
def chat_ask(
    req: ChatRequest,
    user_id: int = Depends(get_current_user_id),
) -> ChatResponse:
    """Ask a text-only question. Uses conversation_id for context (last N messages from DB)."""
    conv_id = _ensure_conversation(req.conversation_id, user_id)
    history_raw = messages_last_n_for_context(conv_id, n=CONTEXT_WINDOW_SIZE)
    history = [{"role": m["role"], "content": m["content"]} for m in history_raw]
    try:
        reply = answer_query(query=req.message, history=history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    _maybe_update_conversation_title(conv_id, user_id, req.message)
    message_add(conv_id, "user", req.message)
    message_add(conv_id, "assistant", reply)
    return ChatResponse(reply=reply, conversation_id=conv_id)


@app.post("/chat/find", response_model=ChatResponse)
async def chat_find(
    image: UploadFile = File(...),
    question: Optional[str] = Form(None),
    conversation_id: Optional[int] = Form(None),
    user_id: int = Depends(get_current_user_id),
) -> ChatResponse:
    """Find medicine by image. Saves to conversation with context window."""
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    try:
        body = await image.read()
        image_b64 = base64.b64encode(body).decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

    conv_id = _ensure_conversation(conversation_id, user_id)
    history_raw = messages_last_n_for_context(conv_id, n=CONTEXT_WINDOW_SIZE)
    history = [{"role": m["role"], "content": m["content"]} for m in history_raw]

    q = question or "Що це за препарат?"
    try:
        reply = answer_query(query=q, history=history, image_base64=image_b64)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    _maybe_update_conversation_title(conv_id, user_id, q)
    message_add(conv_id, "user", q)
    message_add(conv_id, "assistant", reply)
    return ChatResponse(reply=reply, conversation_id=conv_id)

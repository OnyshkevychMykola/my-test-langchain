"""
FastAPI backend for Medical AI Assistant.
Auth: Google OAuth + JWT. Data: SQLite (users → conversations → messages).
Run: uvicorn api:app --reload
"""
import base64
import os
import secrets
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, FastAPI, HTTPException, UploadFile, File, Form, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from pydantic import BaseModel

from chains import answer_query
from db import (
    init_db,
    user_get_by_id,
    user_get_or_create,
    conversation_create,
    conversation_list,
    conversation_get,
    conversation_find_empty,
    conversation_delete,
    conversation_update_title,
    message_add,
    message_get,
    message_update_image_path,
    messages_list,
    messages_last_n_for_context,
    refresh_token_store,
    refresh_token_is_valid,
    refresh_token_revoke,
    chat_usage_get_for_user,
    chat_usage_increment,
    CONTEXT_WINDOW_SIZE,
)
from auth import (
    build_google_login_url,
    exchange_code_for_user,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    sign_oauth_state,
    verify_oauth_state,
    get_current_user_id,
    FRONTEND_URL,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

app = FastAPI(title="Medical AI Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"


@app.on_event("startup")
def startup():
    init_db()
    UPLOADS_DIR.mkdir(exist_ok=True)


def _is_production() -> bool:
    return os.getenv("ENV", "development").lower() == "production"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=_is_production(),
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key="refresh_token", path="/auth")


@app.get("/auth/google")
def auth_google():
    """Redirect to Google OAuth. Set API_BASE_URL in env if behind proxy."""
    base = os.getenv("API_BASE_URL", "http://localhost:8000")
    redirect_uri = f"{base.rstrip('/')}/auth/google/callback"
    raw_state = secrets.token_urlsafe(16)
    signed_state = sign_oauth_state(raw_state)
    url = build_google_login_url(redirect_uri, signed_state)
    return RedirectResponse(url=url)


@app.get("/auth/google/callback")
async def auth_google_callback(code: Optional[str] = None, state: Optional[str] = None):
    """Exchange code for user, create access + refresh tokens, redirect to frontend."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    if not state:
        raise HTTPException(status_code=400, detail="Missing state")

    verify_oauth_state(state)

    base = os.getenv("API_BASE_URL", "http://localhost:8000")
    redirect_uri = f"{base.rstrip('/')}/auth/google/callback"
    user_info = await exchange_code_for_user(code, redirect_uri)
    google_id = user_info.get("id") or user_info.get("sub", "")
    email = user_info.get("email")
    name = user_info.get("name")
    avatar_url = user_info.get("picture")
    user = user_get_or_create(google_id, email=email, name=name, avatar_url=avatar_url)

    access_token = create_access_token(user["id"], google_id)
    jti, refresh_token = create_refresh_token(user["id"])

    expires_at = (datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    refresh_token_store(jti, user["id"], expires_at)

    # Redirect with access token in hash (not sent to server); refresh token goes in HttpOnly cookie
    response = RedirectResponse(url=f"{FRONTEND_URL}#token={access_token}")
    _set_refresh_cookie(response, refresh_token)
    return response


@app.post("/auth/refresh")
async def auth_refresh(response: Response, refresh_token: Optional[str] = Cookie(default=None)):
    """Issue a new access token using the refresh token cookie. Rotates the refresh token."""
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    payload = decode_refresh_token(refresh_token)
    jti = payload["jti"]
    user_id = int(payload["sub"])

    if not refresh_token_is_valid(jti):
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")

    # Rotate: revoke old token, issue new one
    refresh_token_revoke(jti)
    user = user_get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access_token = create_access_token(user_id, user["google_id"])
    new_jti, new_refresh_token = create_refresh_token(user_id)

    expires_at = (datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    refresh_token_store(new_jti, user_id, expires_at)

    _set_refresh_cookie(response, new_refresh_token)
    return {"access_token": new_access_token, "token_type": "bearer"}


@app.post("/auth/logout")
async def auth_logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None),
    user_id: int = Depends(get_current_user_id),
):
    """Revoke the refresh token and clear the cookie."""
    if refresh_token:
        try:
            payload = decode_refresh_token(refresh_token)
            refresh_token_revoke(payload["jti"])
        except HTTPException:
            # Token may already be expired/invalid — still clear cookie
            pass
    _clear_refresh_cookie(response)
    return {"ok": True}


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
    user = user_get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user["id"], "email": user["email"], "name": user["name"], "avatar_url": user["avatar_url"]}


@app.get("/usage")
def get_usage(user_id: int = Depends(get_current_user_id)):
    """Return current user's daily chat usage (used, limit, resets_at UTC)."""
    usage = chat_usage_get_for_user(user_id)
    return usage


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
    return {
        "messages": [
            {
                "id": m["id"],
                "role": m["role"],
                "content": m["content"],
                "image_url": f"conversations/{conversation_id}/messages/{m['id']}/image" if m.get("image_path") else None,
            }
            for m in msgs
        ]
    }


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


def _check_usage_limit(user_id: int) -> Optional[JSONResponse]:
    """Return 429 JSON response if daily limit reached, else None."""
    usage = chat_usage_get_for_user(user_id)
    if usage["used"] >= usage["limit"]:
        return JSONResponse(
            status_code=429,
            content={"detail": "Daily limit reached", "resets_at": usage["resets_at"]},
        )
    return None


@app.post("/chat/ask", response_model=ChatResponse)
def chat_ask(
    req: ChatRequest,
    user_id: int = Depends(get_current_user_id),
):
    """Ask a text-only question. Uses conversation_id for context (last N messages from DB)."""
    limit_resp = _check_usage_limit(user_id)
    if limit_resp is not None:
        return limit_resp
    conv_id = _ensure_conversation(req.conversation_id, user_id)
    history_raw = messages_last_n_for_context(conv_id, n=CONTEXT_WINDOW_SIZE)
    history = [{"role": m["role"], "content": m["content"]} for m in history_raw]
    try:
        reply = answer_query(query=req.message, history=history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    chat_usage_increment(user_id)
    _maybe_update_conversation_title(conv_id, user_id, req.message)
    message_add(conv_id, "user", req.message)
    message_add(conv_id, "assistant", reply)
    return ChatResponse(reply=reply, conversation_id=conv_id)


def _ext_for_content_type(content_type: Optional[str]) -> str:
    if not content_type:
        return "jpg"
    if "png" in content_type:
        return "png"
    if "gif" in content_type:
        return "gif"
    if "webp" in content_type:
        return "webp"
    return "jpg"


@app.get("/conversations/{conversation_id}/messages/{message_id}/image")
def get_message_image(
    conversation_id: int,
    message_id: int,
    user_id: int = Depends(get_current_user_id),
):
    """Serve stored image for a user message. Returns 404 if no image or not found."""
    msg = message_get(message_id, conversation_id, user_id)
    if not msg or not msg.get("image_path"):
        raise HTTPException(status_code=404, detail="Image not found")
    path = UPLOADS_DIR / str(conversation_id) / msg["image_path"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image file not found")
    ext = (msg["image_path"] or "").split(".")[-1].lower()
    media_type = "image/png" if ext == "png" else "image/webp" if ext == "webp" else "image/gif" if ext == "gif" else "image/jpeg"
    return FileResponse(path, media_type=media_type)


@app.post("/chat/find", response_model=ChatResponse)
async def chat_find(
    image: UploadFile = File(...),
    question: Optional[str] = Form(None),
    conversation_id: Optional[int] = Form(None),
    user_id: int = Depends(get_current_user_id),
) -> ChatResponse:
    """Find medicine by image. Saves image and message to conversation."""
    limit_resp = _check_usage_limit(user_id)
    if limit_resp is not None:
        return limit_resp
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

    chat_usage_increment(user_id)
    _maybe_update_conversation_title(conv_id, user_id, q)
    user_msg = message_add(conv_id, "user", q)
    message_id = user_msg["id"]
    ext = _ext_for_content_type(image.content_type)
    save_dir = UPLOADS_DIR / str(conv_id)
    save_dir.mkdir(parents=True, exist_ok=True)
    image_path = f"{message_id}.{ext}"
    save_path = save_dir / image_path
    try:
        save_path.write_bytes(body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {e}")
    message_update_image_path(message_id, conv_id, image_path)
    message_add(conv_id, "assistant", reply)
    return ChatResponse(reply=reply, conversation_id=conv_id)

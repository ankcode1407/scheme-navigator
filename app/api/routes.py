from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from threading import Lock
from typing import Optional, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent.graph import agent
from app.agent.state import AgentState

app = FastAPI(title="Scheme Navigator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
SESSION_FILE = DATA_DIR / "sessions.json"
_SESSION_LOCK = Lock()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    context_complete: bool
    schemes_found: int
    language_detected: str
    preferred_language: Optional[str] = None
    response_tts_text: Optional[str] = None
    should_play_tts: bool = True
    awaiting_language_selection: bool = False
    user_context: Optional[dict[str, Any]] = None
    case_context: Optional[dict[str, Any]] = None
    problem_category: Optional[str] = None


def _load_sessions() -> dict[str, Any]:
    if not SESSION_FILE.exists():
        return {}
    try:
        with SESSION_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_sessions(sessions: dict[str, Any]) -> None:
    tmp_path = SESSION_FILE.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, SESSION_FILE)


def _append_history(history: list[dict[str, Any]], role: str, content: str) -> list[dict[str, Any]]:
    history = list(history or [])
    history.append({"role": role, "content": content})
    return history[-20:]


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())

    with _SESSION_LOCK:
        sessions = _load_sessions()
        session_data = sessions.get(session_id, {})

    existing_context = session_data.get("user_context", {})
    existing_case_context = session_data.get("case_context", {})
    last_question_field = session_data.get("last_question_field")
    preferred_language = session_data.get("preferred_language")
    conversation_history = session_data.get("conversation_history", [])

    conversation_history = _append_history(conversation_history, "user", request.message)

    state: AgentState = {
        "session_id": session_id,
        "user_input": request.message,
        "conversation_history": conversation_history,
        "user_context": existing_context,
        "case_context": existing_case_context,
        "missing_fields": [],
        "context_complete": False,
        "followup_question": None,
        "last_question_field": last_question_field,
        "matched_schemes": [],
        "response_to_user": None,
        "response_tts_text": None,
        "should_play_tts": True,
        "user_language": preferred_language or "en-IN",
        "preferred_language": preferred_language,
        "translate_response": bool(preferred_language and preferred_language != "en-IN"),
        "awaiting_language_selection": not bool(preferred_language),
        "language_selected": bool(preferred_language),
        "stop_after_language_gate": False,
    }

    result = agent.invoke(state)

    response_text = result.get("response_to_user") or ""
    response_tts_text = result.get("response_tts_text") or response_text

    conversation_history = _append_history(conversation_history, "assistant", response_text)

    updated_session = {
        "user_context": result.get("user_context", {}),
        "case_context": result.get("case_context", {}),
        "last_question_field": result.get("last_question_field"),
        "preferred_language": result.get("preferred_language") or result.get("user_language") or preferred_language,
        "conversation_history": conversation_history,
    }

    with _SESSION_LOCK:
        sessions = _load_sessions()
        sessions[session_id] = updated_session
        _save_sessions(sessions)

    return ChatResponse(
        session_id=session_id,
        response=response_text,
        context_complete=bool(result.get("context_complete", False)),
        schemes_found=len(result.get("matched_schemes", [])),
        language_detected=result.get("user_language", preferred_language or "en-IN"),
        preferred_language=result.get("preferred_language") or preferred_language,
        response_tts_text=response_tts_text,
        should_play_tts=bool(result.get("should_play_tts", True)),
        awaiting_language_selection=bool(result.get("awaiting_language_selection", False)),
        user_context=result.get("user_context", {}),
        case_context=result.get("case_context", {}),
        problem_category=(result.get("user_context", {}) or {}).get("problem_category"),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
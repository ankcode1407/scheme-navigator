from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from threading import Lock
from typing import Optional, Any, Literal
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent.graph import agent
from app.agent.state import AgentState

app = FastAPI(title="Scheme Navigator API")

@app.on_event("startup")
def startup_event():
    try:
        from app.agent.scheme_matching import init_matcher
        init_matcher(eager_warm=True)
    except Exception as e:
        import sys
        print(f"FastAPI Startup Exception: {e}", file=sys.stderr)

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
FEEDBACK_FILE = DATA_DIR / "feedback.jsonl"
_FEEDBACK_LOCK = Lock()
METRICS_FILE = DATA_DIR / "metrics.jsonl"
_METRICS_LOCK = Lock()


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
    response_language: str = "en-IN"
    should_play_tts: bool = True
    awaiting_language_selection: bool = False
    user_context: Optional[dict[str, Any]] = None
    case_context: Optional[dict[str, Any]] = None
    problem_category: Optional[str] = None
    needs_state_verification: bool = False
    reranker_mode: str = "groq_primary"


class TTSRequest(BaseModel):
    text: str
    language_code: str = "hi-IN"
    speaker: str = "anushka"


class TTSResponse(BaseModel):
    audio_base64: str
    audio_mime_type: str = "audio/mpeg"


class STTRequest(BaseModel):
    audio_base64: str
    mime_type: str = "audio/webm"
    language_code: str = "unknown"


class STTResponse(BaseModel):
    transcript: str
    language_code: Optional[str] = None
    language_probability: Optional[float] = None


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


def log_session_metrics(
    session_id: str,
    timestamp: str,
    query_length: int,
    reranker_mode: str,
    top_scheme_id: Optional[str],
    top_confidence: Optional[str],
    needs_state_verification: bool,
    needs_clarification: bool,
    matched_scheme_count: int,
    response_type: str
):
    try:
        with _METRICS_LOCK:
            with METRICS_FILE.open("a", encoding="utf-8") as f:
                log_entry = {
                    "session_id": session_id,
                    "timestamp": timestamp,
                    "query_length": query_length,
                    "reranker_mode": reranker_mode,
                    "top_scheme_id": top_scheme_id,
                    "top_confidence": top_confidence,
                    "needs_state_verification": needs_state_verification,
                    "needs_clarification": needs_clarification,
                    "matched_scheme_count": matched_scheme_count,
                    "response_type": response_type
                }
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        import sys
        print(f"Error logging metrics: {e}", file=sys.stderr)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, background_tasks: BackgroundTasks):
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

    # Task 5: Check if this is a new session and we need to show the onboarding opener
    is_new_session = (not existing_context or all(v is None or v == "" for v in existing_context.values())) and \
                     len(conversation_history) == 1 and \
                     not session_data.get("onboarding_shown")

    if is_new_session:
        from app.agent.nodes import parse_language_choice
        selected_lang = parse_language_choice(request.message)
        if selected_lang:
            preferred_language = selected_lang["code"]

        onboarding_data = {
            "type": "onboarding",
            "message": "Hi! I can help you find government schemes you may be eligible for. What do you need help with?",
            "quick_options": [
                "Farming or crop support",
                "Education or scholarship",
                "Employment or self-employment",
                "Health or medical support",
                "Housing support",
                "Pension or elderly support",
                "Livestock or dairy",
                "Something else"
            ]
        }
        onboarding_json = json.dumps(onboarding_data, ensure_ascii=False)
        conversation_history = _append_history(conversation_history, "assistant", onboarding_data["message"])

        updated_session = {
            "user_context": existing_context,
            "case_context": existing_case_context,
            "last_question_field": last_question_field,
            "preferred_language": preferred_language,
            "conversation_history": conversation_history,
            "onboarding_shown": True
        }

        with _SESSION_LOCK:
            sessions = _load_sessions()
            sessions[session_id] = updated_session
            _save_sessions(sessions)

        # Log metrics for onboarding initiation
        background_tasks.add_task(
            log_session_metrics,
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            query_length=len(request.message),
            reranker_mode="retrieval_only",
            top_scheme_id=None,
            top_confidence=None,
            needs_state_verification=False,
            needs_clarification=False,
            matched_scheme_count=0,
            response_type="suppressed"
        )

        return ChatResponse(
            session_id=session_id,
            response=onboarding_json,
            context_complete=False,
            schemes_found=0,
            language_detected=preferred_language or "en-IN",
            preferred_language=preferred_language,
            response_tts_text=onboarding_data["message"],
            response_language="en-IN",
            should_play_tts=True,
            awaiting_language_selection=not bool(preferred_language),
            user_context=existing_context,
            case_context=existing_case_context,
            problem_category=None,
            needs_state_verification=False,
            reranker_mode="retrieval_only"
        )

    # Pre-seed problem_category if user selected a quick option
    ONBOARDING_MAPPING = {
        "Farming or crop support": "agriculture",
        "Education or scholarship": "education",
        "Employment or self-employment": "employment",
        "Health or medical support": "health",
        "Housing support": "housing",
        "Pension or elderly support": "pension",
        "Livestock or dairy": "livestock"
    }
    clean_msg = request.message.strip()
    matched_category = None
    for k, v in ONBOARDING_MAPPING.items():
        if k.lower() == clean_msg.lower():
            matched_category = v
            break

    if matched_category:
        existing_context["problem_category"] = matched_category

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
        # SENIOR SWE FIX: Do not poison the language detector with an English default. 
        # Leave it blank so LangGraph processes the user's intent purely.
        "user_language": preferred_language or "", 
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
        "onboarding_shown": True # Keep it True once set
    }

    with _SESSION_LOCK:
        sessions = _load_sessions()
        sessions[session_id] = updated_session
        _save_sessions(sessions)

    # Log metrics
    matched_schemes = result.get("matched_schemes", [])
    top_scheme_id = matched_schemes[0].get("scheme_id") if matched_schemes else None
    top_confidence = matched_schemes[0].get("confidence") if matched_schemes else None
    needs_clarification = bool(result.get("is_low_confidence")) or bool(result.get("training_centre_clarification"))

    if needs_clarification:
        response_type = "clarification"
    elif len(matched_schemes) > 0:
        response_type = "schemes"
    else:
        response_type = "suppressed"

    reranker_mode_val = result.get("reranker_mode") or "cross_encoder"

    background_tasks.add_task(
        log_session_metrics,
        session_id=session_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        query_length=len(request.message),
        reranker_mode=reranker_mode_val,
        top_scheme_id=top_scheme_id,
        top_confidence=top_confidence,
        needs_state_verification=any(m.get("needs_state_verification", False) for m in matched_schemes),
        needs_clarification=needs_clarification,
        matched_scheme_count=len(matched_schemes),
        response_type=response_type
    )

    return ChatResponse(
        session_id=session_id,
        response=response_text,
        context_complete=bool(result.get("context_complete", False)),
        schemes_found=len(result.get("matched_schemes", [])),
        language_detected=result.get("user_language") or preferred_language or "en-IN",
        preferred_language=result.get("preferred_language") or preferred_language,
        response_tts_text=response_tts_text,
        response_language=result.get("response_language", "en-IN"),
        should_play_tts=bool(result.get("should_play_tts", True)),
        awaiting_language_selection=bool(result.get("awaiting_language_selection", False)),
        user_context=result.get("user_context", {}),
        case_context=result.get("case_context", {}),
        problem_category=(result.get("user_context", {}) or {}).get("problem_category"),
        needs_state_verification=any(m.get("needs_state_verification", False) for m in result.get("matched_schemes", [])),
        reranker_mode=reranker_mode_val
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tts", response_model=TTSResponse)
def text_to_speech(request: TTSRequest):
    from app.language.sarvam import synthesize_bulbul_tts

    audio = synthesize_bulbul_tts(
        request.text,
        target_language_code=request.language_code,
        speaker=request.speaker,
    )
    return TTSResponse(audio_base64=audio)


@app.post("/stt", response_model=STTResponse)
def speech_to_text(request: STTRequest):
    from app.language.sarvam import transcribe_audio_base64

    result = transcribe_audio_base64(
        request.audio_base64,
        mime_type=request.mime_type,
        language_code=request.language_code,
    )
    return STTResponse(**result)


class FeedbackRequest(BaseModel):
    scheme_id: str
    interaction_type: Literal["click", "qualification_yes", "qualification_no"]


@app.post("/api/sessions/{session_id}/feedback")
def post_feedback(session_id: str, request: FeedbackRequest):
    from app.knowledge_base.scheme_loader import get_scheme_by_id
    from datetime import datetime

    # 1. Validate session existence in sessions.json
    with _SESSION_LOCK:
        sessions = _load_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # 2. Validate scheme existence in schemes_full.json
    scheme = get_scheme_by_id(request.scheme_id)
    if scheme is None:
        raise HTTPException(status_code=404, detail=f"Scheme {request.scheme_id} not found")

    # 3. Write event strictly to feedback.jsonl under thread lock
    try:
        with _FEEDBACK_LOCK:
            with FEEDBACK_FILE.open("a", encoding="utf-8") as f:
                log_entry = {
                    "session_id": session_id,
                    "scheme_id": request.scheme_id,
                    "interaction_type": request.interaction_type,
                    "timestamp": datetime.utcnow().isoformat()
                }
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        import sys
        print(f"Error logging feedback: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail="Failed to log feedback")

    return {"status": "success", "session_id": session_id}


@app.get("/api/admin/stats")
def get_admin_stats(x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
    admin_token = os.getenv("ADMIN_TOKEN", "default-admin-token")
    if not x_admin_token or x_admin_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    cutoff = datetime.utcnow() - timedelta(hours=24)

    total_queries = 0
    reranker_modes = {
        "groq_primary": 0,
        "groq_fallback": 0,
        "cross_encoder": 0,
        "retrieval_only": 0
    }
    response_types = {
        "schemes": 0,
        "clarification": 0,
        "suppressed": 0
    }
    scheme_counts = {}
    needs_state_verif_count = 0
    total_scheme_count = 0

    if METRICS_FILE.exists():
        with _METRICS_LOCK:
            with METRICS_FILE.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        ts_str = entry["timestamp"]
                        if ts_str.endswith("Z"):
                            ts_str = ts_str[:-1]
                        ts = datetime.fromisoformat(ts_str)
                        if ts >= cutoff:
                            total_queries += 1
                            mode = entry.get("reranker_mode")
                            if mode in reranker_modes:
                                reranker_modes[mode] += 1
                            else:
                                reranker_modes["retrieval_only"] += 1

                            resp_type = entry.get("response_type")
                            if resp_type in response_types:
                                response_types[resp_type] += 1

                            top_scheme = entry.get("top_scheme_id")
                            if top_scheme:
                                scheme_counts[top_scheme] = scheme_counts.get(top_scheme, 0) + 1

                            if entry.get("needs_state_verification"):
                                needs_state_verif_count += 1

                            total_scheme_count += entry.get("matched_scheme_count", 0)
                    except Exception:
                        continue

    needs_state_verification_rate = 0.0
    avg_matched_scheme_count = 0.0
    groq_degradation_rate = 0.0

    if total_queries > 0:
        needs_state_verification_rate = needs_state_verif_count / total_queries
        avg_matched_scheme_count = total_scheme_count / total_queries
        groq_degradation_rate = (reranker_modes["cross_encoder"] + reranker_modes["retrieval_only"]) / total_queries

    sorted_schemes = sorted(scheme_counts.items(), key=lambda x: x[1], reverse=True)
    top_5 = [{"scheme_id": k, "count": v} for k, v in sorted_schemes[:5]]

    res = {
        "period": "last_24h",
        "total_queries": total_queries,
        "reranker_mode_distribution": reranker_modes,
        "response_type_distribution": response_types,
        "top_5_schemes": top_5,
        "needs_state_verification_rate": needs_state_verification_rate,
        "avg_matched_scheme_count": avg_matched_scheme_count,
        "groq_degradation_rate": groq_degradation_rate
    }

    if groq_degradation_rate > 0.20:
        res["warning"] = "Groq rate limits degrading 20%+ of queries"

    return res
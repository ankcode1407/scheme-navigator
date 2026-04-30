import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from app.agent.graph import agent
from app.agent.state import AgentState

app = FastAPI(title="Scheme Navigator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store
# Stores user_context + last_question_field across turns
sessions: dict = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    context_complete: bool
    schemes_found: int
    language_detected: str


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    # Create or retrieve session
    session_id = request.session_id or str(uuid.uuid4())
    session_data = sessions.get(session_id, {})

    existing_context = session_data.get("user_context", {})
    last_question_field = session_data.get("last_question_field", None)

    # Build state
    state: AgentState = {
        "user_input": request.message,
        "conversation_history": [],
        "user_context": existing_context,
        "missing_fields": [],
        "context_complete": False,
        "followup_question": None,
        "last_question_field": last_question_field,
        "matched_schemes": [],
        "response_to_user": None,
        "user_language": "en-IN",
        "translate_response": False,
    }

    # Run the agent
    result = agent.invoke(state)

    # Persist updated context AND last_question_field for next turn
    sessions[session_id] = {
        "user_context": result["user_context"],
        "last_question_field": result.get("last_question_field"),
    }

    return ChatResponse(
        session_id=session_id,
        response=result["response_to_user"],
        context_complete=result["context_complete"],
        schemes_found=len(result.get("matched_schemes", [])),
        language_detected=result.get("user_language", "en-IN"),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
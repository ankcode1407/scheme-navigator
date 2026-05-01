from __future__ import annotations

from typing import Any, Optional, Literal
from pydantic import BaseModel, Field


class UserContextModel(BaseModel):
    problem_statement: Optional[str] = None
    problem_category: Optional[str] = None
    specific_problem: Optional[str] = None

    occupation: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    block: Optional[str] = None
    residence: Optional[str] = None
    land_hectares: Optional[float] = None
    income_category: Optional[str] = None
    family_size: Optional[int] = None
    has_aadhaar: Optional[bool] = None
    has_bank_account: Optional[bool] = None
    has_ration_card: Optional[bool] = None


class CaseContextModel(BaseModel):
    case_id: Optional[str] = None
    scheme_id: Optional[str] = None
    scheme_name: Optional[str] = None
    application_status: Optional[str] = None
    rejection_reason: Optional[str] = None
    missing_documents: list[str] = Field(default_factory=list)
    last_followup_date: Optional[str] = None
    next_action: Optional[str] = None
    district: Optional[str] = None
    block: Optional[str] = None
    office_type: Optional[str] = None


class SchemeCandidate(BaseModel):
    scheme_id: str = ""
    scheme_name: str = ""
    category: list[str] = Field(default_factory=list)
    eligibility: dict[str, Any] = Field(default_factory=dict)
    benefit: str = ""
    documents_required: list[str] = Field(default_factory=list)
    portal: str = ""
    helpline: str = ""
    application_mode: str = ""
    state: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    brief_description: str = ""
    close_date: Optional[str] = None


class SchemeMatch(BaseModel):
    scheme_id: str = ""
    scheme_name: str = ""
    confidence: Literal["HIGH", "LIKELY", "NEEDS_VERIFICATION"] = "NEEDS_VERIFICATION"
    reason: str = ""
    documents_required: list[str] = Field(default_factory=list)
    action_steps: list[str] = Field(default_factory=list)
    portal: Optional[str] = None
    helpline: Optional[str] = None


class ResponseEnvelope(BaseModel):
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
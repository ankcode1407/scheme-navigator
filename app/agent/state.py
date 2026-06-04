from __future__ import annotations

from typing import TypedDict, Optional, List, Dict, Any


class UserContext(TypedDict, total=False):
    problem_statement: Optional[str]
    problem_category: Optional[str]
    specific_problem: Optional[str]

    occupation: Optional[str]
    state: Optional[str]
    district: Optional[str]
    block: Optional[str]
    residence: Optional[str]
    land_hectares: Optional[float]
    income_category: Optional[str]
    family_size: Optional[int]
    has_aadhaar: Optional[bool]
    has_bank_account: Optional[bool]
    has_ration_card: Optional[bool]

    # Missing fields from extracted citizen context
    age: Optional[float]
    gender: Optional[str]
    caste: Optional[str]
    income: Optional[float]
    land_owned: Optional[float]
    aadhaar_linked: Optional[bool]
    bank_account: Optional[bool]
    ration_card: Optional[bool]
    bpl_status: Optional[bool]
    disability_status: Optional[bool]
    marital_status: Optional[str]


class CaseContext(TypedDict, total=False):
    case_id: Optional[str]
    scheme_id: Optional[str]
    scheme_name: Optional[str]
    application_status: Optional[str]
    rejection_reason: Optional[str]
    missing_documents: List[str]
    last_followup_date: Optional[str]
    next_action: Optional[str]
    district: Optional[str]
    block: Optional[str]
    office_type: Optional[str]


class SchemeMatch(TypedDict, total=False):
    scheme_id: str
    scheme_name: str
    confidence: str
    reason: str
    needs_state_verification: bool
    passed_criteria: List[str]
    failed_criteria: List[str]
    missing_data: List[str]
    documents_required: List[str]
    action_steps: List[str]
    portal: Optional[str]
    helpline: Optional[str]


class AgentState(TypedDict, total=False):
    session_id: str
    user_input: str
    conversation_history: List[Dict[str, Any]]

    preferred_language: Optional[str]
    user_language: str
    translate_response: bool
    awaiting_language_selection: bool
    language_selected: bool

    user_context: UserContext
    case_context: CaseContext
    missing_fields: List[str]
    context_complete: bool
    followup_question: Optional[str]
    last_question_field: Optional[str]

    matched_schemes: List[SchemeMatch]
    
    # --- Response Payload Variables ---
    response_to_user: Optional[str]
    response_tts_text: Optional[str]
    response_language: str              # Added this line
    response_source_language: str       # Added this line
    should_play_tts: bool
    reranker_mode: Optional[str]        # Added this line

    stop_after_language_gate: bool
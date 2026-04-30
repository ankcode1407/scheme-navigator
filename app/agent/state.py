from typing import TypedDict, List, Optional


class UserContext(TypedDict):
    occupation: Optional[str]
    state: Optional[str]
    land_hectares: Optional[float]
    income_category: Optional[str]
    residence: Optional[str]
    family_size: Optional[int]
    has_aadhaar: Optional[bool]
    has_bank_account: Optional[bool]
    has_ration_card: Optional[bool]
    specific_problem: Optional[str]


class SchemeMatch(TypedDict):
    scheme_id: str
    scheme_name: str
    confidence: str
    reason: str
    documents_required: List[str]
    action_steps: List[str]
    portal: str
    helpline: str


class AgentState(TypedDict):
    # What the user said
    user_input: str
    conversation_history: List[dict]

    # What we know about the user so far
    user_context: UserContext

    # What information is still missing
    missing_fields: List[str]

    # Whether we have enough to reason
    context_complete: bool

    # Follow-up question to ask if context incomplete
    followup_question: Optional[str]

    # Tracks which field the last question was about
    # Used to interpret short single-word replies correctly
    last_question_field: Optional[str]

    # Final output
    matched_schemes: List[SchemeMatch]
    response_to_user: Optional[str]

    # Language detection
    user_language: str
    translate_response: bool
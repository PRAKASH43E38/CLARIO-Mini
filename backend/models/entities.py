from dataclasses import dataclass
from typing import Optional


@dataclass
class UserEntity:
    id: str
    email: str
    password_hash: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class ResearchQueryEntity:
    id: str
    session_id: str
    query_text: str
    requested_by: str = "nova"
    parameters_json: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class OrchestrationRunEntity:
    id: str
    session_id: str
    current_stage: str
    status: str
    state_snapshot_json: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

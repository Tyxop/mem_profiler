from pydantic import BaseModel, Field
from typing import Optional


class Triple(BaseModel):
    subject: str
    subject_type: str = "ENTIDAD"
    predicate: str
    object: str
    object_type: str = "ENTIDAD"
    confidence: float = 1.0


class ConversationInput(BaseModel):
    message: str
    session_id: str = "default"
    speaker: str = "usuario"
    model: Optional[str] = None


class QueryInput(BaseModel):
    query: str
    session_id: str = "default"
    max_hops: int = Field(default=2, ge=1, le=4)
    max_nodes: int = Field(default=15, ge=1, le=50)
    model: Optional[str] = None


class ContextResponse(BaseModel):
    context: str
    triples_found: int
    nodes: list[str]
    raw_triples: list[dict]


class StoreResponse(BaseModel):
    triples_extracted: int
    triples_stored: int
    triples: list[Triple]


class ProfileBranch(BaseModel):
    branch: str
    nodes: list[dict]
    triples: list[dict]

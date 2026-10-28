from typing import Literal

from pydantic import BaseModel, Field


class WorkflowDocument(BaseModel):
    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    reviewed_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class KnowledgeQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    audience: Literal["scheduling", "front-desk", "care-operations"]


class OperationalNotification(BaseModel):
    channel: Literal["internal-ops"] = "internal-ops"
    message: str
    patient_safe: bool


class KnowledgeAnswer(BaseModel):
    answer: str
    source_ids: list[str]
    notification: OperationalNotification

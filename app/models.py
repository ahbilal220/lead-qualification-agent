from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field


class WorkflowStatus(StrEnum):
    RECEIVED = "received"
    QUALIFYING = "qualifying"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SYNCED = "synced"


class AuditAction(StrEnum):
    LEAD_RECEIVED = "lead_received"
    ENRICHMENT_COMPLETED = "enrichment_completed"
    SCORE_COMPUTED = "score_computed"
    OUTREACH_DRAFTED = "outreach_drafted"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    CRM_SYNCED = "crm_synced"


class LeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    company: str = Field(min_length=2, max_length=160)
    company_size: int = Field(ge=1, le=1_000_000)
    budget_usd: int = Field(ge=0, le=100_000_000)
    need: str = Field(min_length=10, max_length=2_000)
    authority: bool = False
    timeline_days: int = Field(ge=1, le=730)


class AuditEvent(BaseModel):
    action: AuditAction
    detail: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LeadRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    lead: LeadCreate
    status: WorkflowStatus = WorkflowStatus.RECEIVED
    score: int | None = Field(default=None, ge=0, le=100)
    score_reasons: list[str] = Field(default_factory=list)
    outreach_draft: str | None = None
    crm_record_id: str | None = None
    audit: list[AuditEvent] = Field(default_factory=list)


class DecisionRequest(BaseModel):
    reviewer: str = Field(min_length=2, max_length=120)
    note: str | None = Field(default=None, max_length=500)


class HealthResponse(BaseModel):
    status: str
    leads: int


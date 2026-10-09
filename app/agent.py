from __future__ import annotations

from uuid import UUID

from app.models import (
    AuditAction,
    AuditEvent,
    DecisionRequest,
    LeadCreate,
    LeadRecord,
    WorkflowStatus,
)
from app.store import LeadStore
from app.tools import DemoCRM, enrich_company


class InvalidTransitionError(RuntimeError):
    pass


class LeadQualificationAgent:
    """Bounded lead workflow with a mandatory approval gate before CRM writes."""

    def __init__(self, store: LeadStore, crm: DemoCRM) -> None:
        self.store = store
        self.crm = crm

    def qualify(self, payload: LeadCreate) -> LeadRecord:
        record = LeadRecord(lead=payload, status=WorkflowStatus.QUALIFYING)
        record.audit.append(
            AuditEvent(action=AuditAction.LEAD_RECEIVED, detail="Validated lead intake payload.")
        )

        enrichment = enrich_company(payload.company, payload.company_size)
        record.audit.append(
            AuditEvent(
                action=AuditAction.ENRICHMENT_COMPLETED,
                detail=f"Classified company as {enrichment['segment']} using offline enrichment.",
            )
        )

        record.score, record.score_reasons = self._score(payload)
        record.audit.append(
            AuditEvent(
                action=AuditAction.SCORE_COMPUTED,
                detail=f"Computed transparent qualification score of {record.score}/100.",
            )
        )

        record.outreach_draft = self._draft_outreach(payload, record.score)
        record.audit.append(
            AuditEvent(
                action=AuditAction.OUTREACH_DRAFTED,
                detail="Prepared an outreach draft; no message was sent.",
            )
        )
        record.status = WorkflowStatus.AWAITING_APPROVAL
        record.audit.append(
            AuditEvent(
                action=AuditAction.APPROVAL_REQUESTED,
                detail="Paused before the external CRM write for human review.",
            )
        )
        return self.store.save(record)

    def approve(self, lead_id: UUID, decision: DecisionRequest) -> LeadRecord:
        record = self._require_status(lead_id, WorkflowStatus.AWAITING_APPROVAL)
        record.status = WorkflowStatus.APPROVED
        record.audit.append(
            AuditEvent(
                action=AuditAction.APPROVED,
                detail=f"Approved by {decision.reviewer}. {decision.note or ''}".strip(),
            )
        )
        record.crm_record_id = self.crm.sync(
            record.id,
            {
                "lead": record.lead.model_dump(mode="json"),
                "score": record.score,
                "score_reasons": record.score_reasons,
                "outreach_draft": record.outreach_draft,
            },
            approved=True,
        )
        record.status = WorkflowStatus.SYNCED
        record.audit.append(
            AuditEvent(
                action=AuditAction.CRM_SYNCED,
                detail=f"Synced approved lead to record {record.crm_record_id}.",
            )
        )
        return self.store.save(record)

    def reject(self, lead_id: UUID, decision: DecisionRequest) -> LeadRecord:
        record = self._require_status(lead_id, WorkflowStatus.AWAITING_APPROVAL)
        record.status = WorkflowStatus.REJECTED
        record.audit.append(
            AuditEvent(
                action=AuditAction.REJECTED,
                detail=f"Rejected by {decision.reviewer}. {decision.note or ''}".strip(),
            )
        )
        return self.store.save(record)

    def _require_status(self, lead_id: UUID, expected: WorkflowStatus) -> LeadRecord:
        record = self.store.get(lead_id)
        if record is None:
            raise KeyError(str(lead_id))
        if record.status is not expected:
            raise InvalidTransitionError(
                f"Lead is {record.status.value}; expected {expected.value}."
            )
        return record

    @staticmethod
    def _score(payload: LeadCreate) -> tuple[int, list[str]]:
        score = 0
        reasons: list[str] = []
        if payload.budget_usd >= 25_000:
            score += 30
            reasons.append("Budget is at least $25,000.")
        elif payload.budget_usd >= 5_000:
            score += 20
            reasons.append("Budget is between $5,000 and $24,999.")
        elif payload.budget_usd > 0:
            score += 8
            reasons.append("A budget is defined but below $5,000.")
        if payload.authority:
            score += 25
            reasons.append("Contact identifies as a decision-maker.")
        if payload.timeline_days <= 30:
            score += 25
            reasons.append("Timeline is within 30 days.")
        elif payload.timeline_days <= 90:
            score += 15
            reasons.append("Timeline is within 90 days.")
        if payload.company_size >= 100:
            score += 15
            reasons.append("Company has at least 100 employees.")
        else:
            score += 8
            reasons.append("Company is in the SMB segment.")
        if len(payload.need.split()) >= 8:
            score += 5
            reasons.append("Need statement contains useful detail.")
        return min(score, 100), reasons

    @staticmethod
    def _draft_outreach(payload: LeadCreate, score: int) -> str:
        first_name = payload.name.split()[0]
        return (
            f"Hi {first_name}, thanks for outlining {payload.company}'s requirements. "
            f"I understand the priority is {payload.need.rstrip('.')}. "
            f"Based on the information provided, this lead scored {score}/100. "
            "Would you be open to a short discovery call to confirm the workflow "
            "and success criteria?"
        )

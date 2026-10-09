from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, HTTPException, status

from app.agent import InvalidTransitionError, LeadQualificationAgent
from app.models import DecisionRequest, HealthResponse, LeadCreate, LeadRecord
from app.store import LeadStore
from app.tools import DemoCRM

store = LeadStore()
crm = DemoCRM()
agent = LeadQualificationAgent(store, crm)

app = FastAPI(
    title="Human-Approved Lead Qualification Agent",
    version="0.1.0",
    description="Qualifies leads and drafts outreach, then pauses before CRM writes.",
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", leads=len(store.records))


@app.post("/leads", response_model=LeadRecord, status_code=status.HTTP_201_CREATED)
async def create_lead(payload: LeadCreate) -> LeadRecord:
    return agent.qualify(payload)


@app.get("/leads/{lead_id}", response_model=LeadRecord)
async def get_lead(lead_id: UUID) -> LeadRecord:
    record = store.get(lead_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return record


@app.post("/leads/{lead_id}/approve", response_model=LeadRecord)
async def approve_lead(lead_id: UUID, payload: DecisionRequest) -> LeadRecord:
    return _decide(agent.approve, lead_id, payload)


@app.post("/leads/{lead_id}/reject", response_model=LeadRecord)
async def reject_lead(lead_id: UUID, payload: DecisionRequest) -> LeadRecord:
    return _decide(agent.reject, lead_id, payload)


def _decide(handler: object, lead_id: UUID, payload: DecisionRequest) -> LeadRecord:
    try:
        return handler(lead_id, payload)  # type: ignore[operator]
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Lead not found") from error
    except InvalidTransitionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

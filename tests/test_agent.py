from app.agent import LeadQualificationAgent
from app.models import DecisionRequest, LeadCreate, WorkflowStatus
from app.store import LeadStore
from app.tools import ApprovalRequiredError, DemoCRM


def payload() -> LeadCreate:
    return LeadCreate(
        name="Sam Carter",
        email="sam@example.com",
        company="Northstar Logistics",
        company_size=240,
        budget_usd=30_000,
        need="Automate inbound lead routing and draft responses for the sales team",
        authority=True,
        timeline_days=21,
    )


def test_agent_pauses_before_external_write() -> None:
    store = LeadStore()
    crm = DemoCRM()
    record = LeadQualificationAgent(store, crm).qualify(payload())

    assert record.status is WorkflowStatus.AWAITING_APPROVAL
    assert record.score == 100
    assert record.outreach_draft
    assert crm.records == {}


def test_approval_executes_exactly_one_crm_write() -> None:
    store = LeadStore()
    crm = DemoCRM()
    agent = LeadQualificationAgent(store, crm)
    record = agent.qualify(payload())

    approved = agent.approve(record.id, DecisionRequest(reviewer="A. Reviewer"))

    assert approved.status is WorkflowStatus.SYNCED
    assert approved.crm_record_id in crm.records
    assert len(crm.records) == 1


def test_crm_adapter_rejects_unapproved_write() -> None:
    crm = DemoCRM()

    try:
        crm.sync(LeadQualificationAgent(LeadStore(), crm).qualify(payload()).id, {}, approved=False)
    except ApprovalRequiredError as error:
        assert "explicit approval" in str(error)
    else:
        raise AssertionError("Unapproved write was not blocked")


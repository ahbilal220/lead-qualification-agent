from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


class ApprovalRequiredError(RuntimeError):
    """Raised when an external write is attempted without human approval."""


@dataclass
class DemoCRM:
    """Deterministic CRM adapter used by the local demo and tests."""

    records: dict[str, dict[str, Any]] = field(default_factory=dict)

    def sync(self, lead_id: UUID, payload: dict[str, Any], *, approved: bool) -> str:
        if not approved:
            raise ApprovalRequiredError("CRM writes require an explicit approval decision.")
        record_id = f"demo-crm-{str(lead_id)[:8]}"
        self.records[record_id] = payload
        return record_id


def enrich_company(company: str, company_size: int) -> dict[str, str]:
    """Offline enrichment tool that is predictable and safe for demonstrations."""

    if company_size >= 1_000:
        segment = "enterprise"
    elif company_size >= 100:
        segment = "mid-market"
    else:
        segment = "SMB"
    domain_hint = "".join(character for character in company.lower() if character.isalnum())
    return {"segment": segment, "domain_hint": f"{domain_hint}.example"}

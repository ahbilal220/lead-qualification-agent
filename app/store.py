from __future__ import annotations

from uuid import UUID

from app.models import LeadRecord


class LeadStore:
    def __init__(self) -> None:
        self.records: dict[UUID, LeadRecord] = {}

    def save(self, record: LeadRecord) -> LeadRecord:
        self.records[record.id] = record
        return record

    def get(self, lead_id: UUID) -> LeadRecord | None:
        return self.records.get(lead_id)


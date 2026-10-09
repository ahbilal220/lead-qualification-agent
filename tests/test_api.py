import asyncio

import httpx

from app.api import app, crm, store


def test_end_to_end_approval_flow() -> None:
    async def run() -> None:
        store.records.clear()
        crm.records.clear()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/leads",
                json={
                    "name": "Sam Carter",
                    "email": "sam@example.com",
                    "company": "Northstar Logistics",
                    "company_size": 240,
                    "budget_usd": 30000,
                    "need": (
                        "Automate inbound lead routing and draft responses for the sales team"
                    ),
                    "authority": True,
                    "timeline_days": 21,
                },
            )

            lead_id = created.json()["id"]
            approved = await client.post(
                f"/leads/{lead_id}/approve",
                json={"reviewer": "A. Reviewer", "note": "Scope reviewed."},
            )
            duplicate = await client.post(
                f"/leads/{lead_id}/approve",
                json={"reviewer": "A. Reviewer"},
            )

        assert created.status_code == 201
        assert created.json()["status"] == "awaiting_approval"
        assert approved.status_code == 200
        assert approved.json()["status"] == "synced"
        assert duplicate.status_code == 409

    asyncio.run(run())

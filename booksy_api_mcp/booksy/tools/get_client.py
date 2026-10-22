"""Get client: one client card with its visit history, newest first."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.clients import CLIENT_EXAMPLE, api, client_out, visit_out
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "client_id": {"type": "integer", "description": "From list_clients or find_client."},
        "visits_limit": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": "Visits to return. Default: 20.",
        },
    },
    "required": ["client_id"],
    "additionalProperties": False,
}

VISIT_EXAMPLE: dict[str, Any] = {
    "appointment_uid": 785492644,
    "start": "2026-10-21T10:00",
    "end": "2026-10-21T10:20",
    "status": "finished",
    "services": ["Beard trim"],
    "staff": ["Tom Baker"],
    "total": "40,00 zł",
}


@tool(
    name="get_client",
    title="Get client",
    access="read",
    confirm=False,
    description="One client card: contact details, private note, counts and visit history.",
    details=(
        "Reads one client card of the business by ID: name, email, phone, birthday, private note, tags, "
        "whether the client is blocked or uses the Booksy app, visit, no-show and cancellation counts, revenue, "
        "and the visits (past and upcoming appointments) with times, services, staff, status and total. A "
        "visit's appointment_uid is the appointment_id of get_appointment."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /clients/{client_id}",
    example_response={**CLIENT_EXAMPLE, "visits_total": 1, "visit_history": [VISIT_EXAMPLE]},
)
async def get_client(ctx: ToolContext, args: dict[str, Any]) -> Any:
    client_id = int(args["client_id"])
    missing = "No client card with this ID in this business."
    card = await api(ctx, "GET", f"/customers/{client_id}", not_found=missing)
    out = client_out(card)
    count = min(int(args.get("visits_limit", 20)), 100)
    visits: dict[str, Any] = {"bookings": [], "count": 0}
    if count:
        visits = await api(
            ctx,
            "GET",
            f"/customers/{client_id}/bookings",
            params={"page": 1, "per_page": count, "inlcude_extra_bookings": "true"},
            not_found=missing,
        )
    out["visits_total"] = int(visits.get("count") or 0)
    out["visit_history"] = [visit_out(b) for b in visits.get("bookings") or []]
    return out

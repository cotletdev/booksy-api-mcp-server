"""Add client note: append a dated line to the card's private note (Booksy keeps one note per card)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.clients import CLIENT_EXAMPLE, api, client_out
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "client_id": {"type": "integer", "description": "From list_clients or find_client."},
        "text": {"type": "string", "minLength": 1, "maxLength": 1000, "description": "The line to add."},
    },
    "required": ["client_id", "text"],
    "additionalProperties": False,
}


@tool(
    name="add_client_note",
    title="Add client note",
    access="write",
    confirm=False,
    description="Add a dated line to a client's private note, keeping what is there.",
    details=(
        "Booksy keeps one private note per client card, seen only by the business. This adds a new line "
        "starting with today's date under the existing text. The client is not told."
    ),
    input_schema=INPUT_SCHEMA,
    route="POST /clients/{client_id}/notes",
    example_response=CLIENT_EXAMPLE,
)
async def add_client_note(ctx: ToolContext, args: dict[str, Any]) -> Any:
    path = f"/customers/{int(args['client_id'])}"
    missing = "No client card with this ID in this business."
    card = await api(ctx, "GET", path, not_found=missing)
    old = client_out(card)["note"].rstrip()
    line = f"{datetime.now(UTC).date().isoformat()}: {args['text'].strip()}"
    note = f"{old}\n{line}" if old else line
    return client_out(await api(ctx, "PUT", path, payload={"business_secret_note": note}, not_found=missing))

"""Add client: a new card in the Clients list, never invited to the Booksy app."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.clients import CLIENT_EXAMPLE, api, client_out, contact_fields
from booksy_api_mcp.core.errors import ErrorCode, ToolError
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1, "description": "Full name; the last word is the last name."},
        "phone": {"type": "string", "description": "Mobile phone, best in international format (+48 600 100 200)."},
        "email": {"type": "string", "format": "email", "description": "Email address."},
        "note": {"type": "string", "description": "Private note, seen only by the business."},
        "birthday": {"type": "string", "format": "date", "description": "YYYY-MM-DD."},
    },
    "required": ["name"],
    "additionalProperties": False,
}


@tool(
    name="add_client",
    title="Add client",
    access="write",
    confirm=False,
    description="Add a client card to your client list. Needs a phone or an email.",
    details=(
        "Adds one client card with a name, a phone or an email (Booksy needs one of them), and optionally a "
        "private note and a birthday. The client is not invited to the Booksy app and gets no message, so "
        "add_client runs without asking first. delete_client removes the card again. A card deleted earlier "
        "with the same email or phone comes back with its old visits, note and birthday unless new ones are given."
    ),
    input_schema=INPUT_SCHEMA,
    route="POST /clients",
    example_response=CLIENT_EXAMPLE,
)
async def add_client(ctx: ToolContext, args: dict[str, Any]) -> Any:
    if not args.get("phone") and not args.get("email"):
        raise ToolError("Booksy needs a phone or an email for a client card.", ErrorCode.INVALID_INPUT)
    fields = contact_fields(args)
    card = client_out(await api(ctx, "POST", "/customers", payload={**fields, "invite": False}))
    # A card deleted before with the same email or phone comes back as it was, ignoring the new fields
    # (21.10.2026): write them over it.
    theirs = {
        "first_name": "first_name",
        "last_name": "last_name",
        "business_secret_note": "note",
        "birthday": "birthday",
    }
    if any(card.get(ours) != fields[key] for key, ours in theirs.items() if key in fields):
        card = client_out(await api(ctx, "PUT", f"/customers/{card['client_id']}", payload=fields))
    return card

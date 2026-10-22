"""Delete client: remove a card from the Clients list."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.clients import api
from booksy_api_mcp.core.errors import ErrorCode, ToolError
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"client_id": {"type": "integer", "description": "From list_clients or find_client."}},
    "required": ["client_id"],
    "additionalProperties": False,
}


@tool(
    name="delete_client",
    title="Delete client",
    access="write",
    confirm=False,
    description="Remove a client card from your client list.",
    details=(
        "Deletes the card the way the panel's Delete button does. The client is not told. Past appointments "
        "stay in the calendar."
    ),
    input_schema=INPUT_SCHEMA,
    route="DELETE /clients/{client_id}",
    example_response={"client_id": 132355511, "deleted": True},
)
async def delete_client(ctx: ToolContext, args: dict[str, Any]) -> Any:
    client_id = int(args["client_id"])
    path = f"/customers/{client_id}"
    missing = "No client card with this ID in this business."
    try:
        await api(ctx, "DELETE", path, not_found=missing)
    except ToolError as exc:
        if exc.code != ErrorCode.TARGET_ERROR:
            raise
        # Booksy deletes the card and still answers 500 (21.10.2026): the card's own read decides.
        try:
            await api(ctx, "GET", path, not_found=missing)
        except ToolError as gone:
            if gone.code == ErrorCode.INVALID_INPUT:
                return {"client_id": client_id, "deleted": True}
            raise
        raise
    return {"client_id": client_id, "deleted": True}

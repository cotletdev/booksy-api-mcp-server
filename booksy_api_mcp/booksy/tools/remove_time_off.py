"""Remove time off: delete a Shifts time off or a calendar block made by add_time_off."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.calendar import int_id, parse_time_off_id, problem, request
from booksy_api_mcp.core.errors import ErrorCode, ToolError
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "staff_id": {"type": "string", "description": "Staff ID the time off belongs to."},
        "time_off_id": {"type": "string", "description": "ID from add_time_off or list_time_off (off-… or block-…)."},
    },
    "required": ["staff_id", "time_off_id"],
    "additionalProperties": False,
}


@tool(
    name="remove_time_off",
    title="Remove time off",
    access="write",
    confirm=False,
    description="Remove time off or a blocked period so the time can be booked again.",
    details="Deletes one time off (off-…) or one calendar block (block-…). It reaches no client.",
    input_schema=INPUT_SCHEMA,
    route="DELETE /staffs/{staff_id}/time-offs/{time_off_id}",
    example_response={"removed": "off-49254738"},
)
async def remove_time_off(ctx: ToolContext, args: dict[str, Any]) -> Any:
    staff = int_id(args["staff_id"], "staff_id")
    kind, raw = parse_time_off_id(args["time_off_id"])
    if kind == "time_off":
        response = await request(ctx, "DELETE", f"/shifts/resources/{staff}/time_offs/{raw}")
    else:
        response = await request(ctx, "DELETE", f"/reservations/{raw}/", business=False)
    if response.status == 404:
        raise ToolError("Booksy has no such time off. It may be removed already.", ErrorCode.TARGET_ERROR)
    if (text := problem(response)) is not None:
        raise ToolError(text, ErrorCode.TARGET_ERROR)
    return {"removed": args["time_off_id"].strip()}

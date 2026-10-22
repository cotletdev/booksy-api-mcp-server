"""Get report: one Stats & Reports category, or one report of it, for a day, week, month or year."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.engagement import CATEGORIES, business_api, header_out, period, table_out
from booksy_api_mcp.core.errors import ErrorCode, ToolError
from booksy_api_mcp.core.tools import tool

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": list(CATEGORIES),
            "description": (
                "dashboard (totals), appointments, clients, revenue, cash_flow, staff_members, marketing, tips or "
                "inventory."
            ),
        },
        "from": {"type": "string", "format": "date", "description": "First day, inclusive."},
        "to": {
            "type": "string",
            "format": "date",
            "description": "Last day, inclusive: the same day, a Monday-to-Sunday week, a calendar month or year.",
        },
        "report": {
            "type": "string",
            "description": "Report key from `reports` of the category (e.g. appointments_summary) for its full tables.",
        },
        "staff_id": {"type": "integer", "description": "Staff member, only for the report performance_per_staffer."},
    },
    "required": ["category", "from", "to"],
    "additionalProperties": False,
}

EXAMPLE_SECTION: dict[str, Any] = {
    "key": "top_10_staff_members_revenue",
    "title": "Top 10 staff members by revenue",
    "columns": {"staffer": "Staff member", "subbookings_count": "Appointments", "total_revenue": "Revenue"},
    "rows": [{"staffer": "Tom", "subbookings_count": 41, "total_revenue": "$2,310.00"}],
    "total": None,
}


@tool(
    name="get_report",
    title="Get report",
    access="read",
    description="Numbers from Stats & Reports for a day, week, month or year, as JSON.",
    details=(
        "Returns one Stats & Reports category for a period: dashboard gives the totals for appointments, revenue "
        "and clients with the change against the previous period; any other category gives its highlight tables "
        "and the list of its reports. Pass report with a key from that list for the full report. Booksy counts "
        "one day, one Monday-to-Sunday week, one calendar month or one calendar year, so from and to must be such "
        "a period. Amounts come formatted in the business's currency. Booksy Biz Lite has the dashboard, revenue, "
        "appointments and clients; cash_flow, inventory, staff_members and marketing need Booksy Biz Pro."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /reports/{category}",
    example_response={
        "category": "staff_members",
        "from": "2026-10-05",
        "to": "2026-10-11",
        "period": "week",
        "totals": {},
        "sections": [EXAMPLE_SECTION],
        "reports": [{"key": "performance_per_staffer", "title": "Staff performance details"}],
        "report": None,
    },
)
async def get_report(ctx: ToolContext, args: dict[str, Any]) -> Any:
    category = args["category"]
    if category not in CATEGORIES:
        raise ToolError(f"Unknown category {category}.", ErrorCode.INVALID_INPUT)
    span, start, end = period(args["from"], args["to"])
    query: dict[str, Any] = {"date_from": start, "date_till": end, "time_span": span}
    out: dict[str, Any] = {"category": category, "from": start, "to": end, "period": span}

    if category == "dashboard":
        found = await business_api(ctx, "GET", "/dashboard/main", params=query, stats=True)
        out["totals"] = {
            "appointments": found.get("appointments_stats") or {},
            "revenue": found.get("revenue_stats") or {},
            "clients": found.get("clients_stats") or {},
        }
        out.update(sections=[], reports=[], report=None)
        return out

    query["dashboard"] = CATEGORIES[category]
    found = await business_api(ctx, "GET", "/dashboard", params=query, stats=True)
    del query["dashboard"]
    out["totals"] = header_out(found.get("header_box"))
    out["sections"] = [table_out(s) for s in found.get("preview_sections") or []]
    out["reports"] = [{"key": r.get("key"), "title": r.get("title")} for r in found.get("reports") or []]
    out["report"] = None
    if key := args.get("report"):
        if key not in {r["key"] for r in out["reports"]}:
            raise ToolError(f"{category} has no report {key}; pick one from reports.", ErrorCode.INVALID_INPUT)
        params = {**query, "report_key": key}
        if args.get("staff_id") is not None:
            params["staffer_id"] = int(args["staff_id"])
        report = await business_api(ctx, "GET", "/report", params=params, stats=True)
        out["report"] = {
            "key": key,
            "title": report.get("title"),
            "subtitle": report.get("subtitle") or None,
            "sections": [table_out(s) for s in report.get("sections") or []],
        }
    return out

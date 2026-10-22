"""Requests of the reviews, Message Blasts, Stats & Reports and business settings tools.

`business_api` builds `<cc>.booksy.com/core/v2/business_api/me/...` from the signed-in identity and turns
Booksy's 400/404 answers into a ToolError with Booksy's own description.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.client import Session, headers, session
from booksy_api_mcp.core.errors import AuthExpiredError, ErrorCode, ToolError

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext


def _signed_in(ctx: ToolContext) -> Session:
    s = session(ctx)
    if s is None or s.business_id is None:
        raise AuthExpiredError("Sign in to Booksy Biz again.")
    return s


def _message(body: Any) -> str | None:
    """Booksy's first readable error: `{"errors": [{"description"}]}` or DRF `{"field": ["..."]}`."""
    if not isinstance(body, dict):
        return None
    errors = body.get("errors")
    if isinstance(errors, list):
        for error in errors:
            if isinstance(error, dict) and error.get("description"):
                return str(error["description"])
    if isinstance(body.get("detail"), str):
        return body["detail"]
    for field, value in body.items():
        if isinstance(value, list) and value and isinstance(value[0], str):
            return f"{field}: {value[0]}"
    return None


async def business_api(
    ctx: ToolContext,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    payload: Any = None,
    stats: bool = False,
) -> Any:
    """One call under `~` (`/business_api/me/businesses/{id}`), or under the stats root with `stats=True`."""
    s = _signed_in(ctx)
    root = "stats/businesses" if stats else "businesses"
    url = f"{s.api}/business_api/me/{root}/{s.business_id}{path}"
    kwargs: dict[str, Any] = {"headers": headers(ctx, s)}
    if params:
        kwargs["params"] = {k: v for k, v in params.items() if v is not None}
    if payload is not None:
        kwargs["json"] = payload
    response = await ctx.call(method, url, **kwargs)
    if response.status >= 400:
        try:
            body = response.json()
        except ToolError:
            body = None
        if response.status == 404:
            raise ToolError(_message(body) or "Booksy has no such record.", ErrorCode.INVALID_INPUT)
        if response.status in (400, 409, 422):
            raise ToolError(_message(body) or "Booksy refused the request.", ErrorCode.INVALID_INPUT)
        raise ToolError(_message(body) or f"Booksy answered {response.status}.", ErrorCode.TARGET_ERROR)
    return response.json() if response.text.strip() else {}


# --- Stats & Reports -------------------------------------------------------------------------------------

# Catalog category -> the stats app's `dashboard` key; `dashboard` itself is `dashboard/main`.
CATEGORIES: dict[str, str] = {
    "dashboard": "",
    "appointments": "appointments",
    "clients": "clients",
    "revenue": "revenue",
    "cash_flow": "cash_flow",
    "staff_members": "staff",
    "marketing": "promotion",
    "tips": "tips",
    "inventory": "inventory",
}


def period(start: str, end: str) -> tuple[str, str, str]:
    """`(time_span, from, to)` for Booksy's stats, which only take a day, a Monday-Sunday week, a month or a year.

    Booksy widens any other range to the period of its first day, so a range that is none of these is refused.
    """
    try:
        first, last = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError as exc:
        raise ToolError("from and to must be dates as YYYY-MM-DD.", ErrorCode.INVALID_INPUT) from exc
    if first == last:
        return "day", start, end
    if first.weekday() == 0 and last == first + timedelta(days=6):
        return "week", start, end
    if first.day == 1 and last == first.replace(day=calendar.monthrange(first.year, first.month)[1]):
        return "month", start, end
    if (first.month, first.day, last.month, last.day) == (1, 1, 12, 31) and first.year == last.year:
        return "year", start, end
    raise ToolError(
        "Booksy reports one day, one Monday-to-Sunday week, one calendar month or one calendar year. "
        "Set from and to to such a period.",
        ErrorCode.INVALID_INPUT,
    )


def table_out(section: dict[str, Any]) -> dict[str, Any]:
    """A stats section as `{key, title, columns, rows, total}`, rows keyed by column key, Booksy's `_meta` dropped."""
    table = section.get("table") or {}
    columns = {h["key"]: h.get("label") or h["key"] for h in table.get("headers") or [] if h.get("key")}
    rows = [{k: v for k, v in row.items() if k != "_meta"} for row in table.get("rows") or []]
    total = table.get("total_row")
    found: dict[str, Any] = {
        "key": section.get("key"),
        "title": section.get("title") or None,
        "columns": columns,
        "rows": rows,
        "total": total if isinstance(total, dict) and total else None,
    }
    paging = section.get("pagination")
    if isinstance(paging, dict) and paging:
        found["pagination"] = paging
    return found


def header_out(box: Any) -> dict[str, Any]:
    """`header_box.rows[].entries[{label, entry_value}]` as one `{label: value}` dict."""
    found: dict[str, Any] = {}
    if isinstance(box, dict):
        for row in box.get("rows") or []:
            for entry in row.get("entries") or []:
                if entry.get("label"):
                    found[entry["label"]] = entry.get("entry_value")
    return found


# --- Message Blasts --------------------------------------------------------------------------------------

CHANNELS = ("email", "sms", "push")


def channel_priority(channel: str) -> dict[str, bool]:
    """The panel's `channel_priority` for one channel; `default` would let Booksy pick SMS, push and email."""
    if channel not in CHANNELS:
        raise ToolError("channel must be email, sms or push.", ErrorCode.INVALID_INPUT)
    return {"default": False, "prefer_push": False, **{c: c == channel for c in CHANNELS}}


def client_ids(args: dict[str, Any]) -> list[int]:
    """Recipients as Booksy's card ids. Never empty: Booksy reads an empty `ids` as every client."""
    raw = args.get("client_ids") or []
    try:
        ids = sorted({int(i) for i in raw})
    except (TypeError, ValueError) as exc:
        raise ToolError("client_ids are client IDs from list_clients.", ErrorCode.INVALID_INPUT) from exc
    if not ids:
        raise ToolError("Give at least one client in client_ids.", ErrorCode.INVALID_INPUT)
    return ids


async def estimate(ctx: ToolContext, ids: list[int], channel: str, message: str) -> dict[str, Any]:
    """`cost_estimation` for the chosen clients: Booksy checks the ids (400 "Not all clients exists")."""
    found = await business_api(
        ctx,
        "POST",
        "/message_blast/cost_estimation/",
        payload={"ids": ids, "excluded": [], "body_short": message, "channel_priority": channel_priority(channel)},
    )
    return found.get("receivers") or {}


def audience(data: dict[str, Any]) -> dict[str, Any]:
    d = data.get("data") or {}
    return {
        "recipients": d.get("receivers_amount", 0),
        "emails": d.get("estimated_email", 0),
        "sms": d.get("estimated_sms", 0),
        "pushes": d.get("estimated_push", 0),
        "sms_parts_per_recipient": d.get("sms_parts_per_receiver"),
        "sms_cost_total": d.get("sms_cost_total", 0),
        "sms_limit_reached": bool(d.get("sms_empty")),
    }

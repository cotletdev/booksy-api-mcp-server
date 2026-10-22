"""Calendar, appointments, open slots and time off: requests and shapes shared by those tools."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from booksy_api_mcp.booksy.client import headers, session
from booksy_api_mcp.core.errors import AuthExpiredError, ErrorCode, ToolError

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import HttpResponse, ToolContext


async def request(
    ctx: ToolContext,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    body: Any = None,
    business: bool = True,
) -> HttpResponse:
    """One API call; `path` is under the open business (`~`) unless `business` is False."""
    s = session(ctx)
    if s is None or s.business_id is None:
        raise AuthExpiredError("Booksy is signed out.")
    base = f"{s.api}/business_api/me/businesses/{s.business_id}" if business else f"{s.api}/business_api/me"
    kwargs: dict[str, Any] = {"headers": headers(ctx, s)}
    if params:
        kwargs["params"] = params
    if body is not None:
        kwargs["json"] = body
    return await ctx.call(method, f"{base}{path}", **kwargs)


def problem(response: HttpResponse) -> str | None:
    """Booksy's own words for a refused request, or None when it went through."""
    if response.status < 400:
        return None
    try:
        data = response.json()
    except ToolError:
        return f"Booksy refused the request ({response.status})."
    if isinstance(data, dict):
        errors = data.get("errors")
        if isinstance(errors, list) and errors:
            texts = [_error_text(e) for e in errors if isinstance(e, dict)]
            if any(texts):
                return " ".join(t for t in texts if t)
        if data.get("detail"):
            return str(data["detail"])
        for field, value in data.items():
            if isinstance(value, list) and value and isinstance(value[0], str):
                return f"{field}: {value[0]}"
    return f"Booksy refused the request ({response.status})."


def _error_text(error: dict[str, Any]) -> str:
    text = str(error.get("description") or error.get("code") or "")
    field = error.get("field")
    return f"{field}: {text}" if field and field != "non_field_errors" and text else text


async def ok_json(ctx: ToolContext, method: str, path: str, **kwargs: Any) -> Any:
    response = await request(ctx, method, path, **kwargs)
    if response.status == 404:
        raise ToolError("Booksy has no such record.", ErrorCode.TARGET_ERROR)
    if (text := problem(response)) is not None:
        raise ToolError(text, ErrorCode.TARGET_ERROR)
    return response.json() if response.text.strip() else {}


async def business_zone(ctx: ToolContext) -> ZoneInfo:
    """The business's time zone; times in the API are local to it."""
    cached = await ctx.cache_get(f"tz:{_business_key(ctx)}")
    if cached:
        return ZoneInfo(cached)
    data = await ok_json(ctx, "GET", "")
    business = data.get("business") or data
    name = ((business.get("location") or {}).get("time_zone_name")) or business.get("timezone_name") or "UTC"
    await ctx.cache_set(f"tz:{_business_key(ctx)}", name, 3600)
    return ZoneInfo(name)


def _business_key(ctx: ToolContext) -> str:
    s = session(ctx)
    return f"{s.country}:{s.business_id}" if s else "none"


def iso(local: str | None, zone: ZoneInfo) -> str | None:
    """`YYYY-MM-DDTHH:MM` local to the business as ISO 8601 with its offset."""
    if not local:
        return None
    return datetime.fromisoformat(local).replace(tzinfo=zone).isoformat()


def local(value: str, zone: ZoneInfo) -> datetime:
    """An ISO 8601 input as naive business-local time; a time without a zone is taken as local."""
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ToolError(f"Not an ISO 8601 date-time: {value}.", ErrorCode.INVALID_INPUT) from exc
    if moment.tzinfo is not None:
        moment = moment.astimezone(zone).replace(tzinfo=None)
    return moment


def stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M")


def day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ToolError(f"Not a date (YYYY-MM-DD): {value}.", ErrorCode.INVALID_INPUT) from exc


def days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def int_id(value: Any, what: str) -> int:
    try:
        return int(str(value).strip())
    except ValueError as exc:
        raise ToolError(f"{what} must be a number from Booksy.", ErrorCode.INVALID_INPUT) from exc


async def service_variant(ctx: ToolContext, service_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """The service and its first variant (duration, price, staffers); a variant id also finds its service."""
    wanted = int_id(service_id, "service_id")
    for service in (await ok_json(ctx, "GET", "/services")).get("services") or []:
        variants = service.get("variants") or []
        if service.get("id") == wanted and variants:
            return service, variants[0]
        for variant in variants:
            if variant.get("id") == wanted:
                return service, variant
    raise ToolError("No service with this ID in Booksy. Take one from list_services.", ErrorCode.INVALID_INPUT)


# Booksy's appointment status letters, as the calendar legend names them.
STATUSES = {
    "A": "confirmed",
    "W": "pending",
    "C": "cancelled",
    "D": "declined",
    "N": "no_show",
    "F": "finished",
    "P": "payment_pending",
    "V": "pending_payment",
    "R": "rejected",
    "M": "modified",
}


def status_name(code: Any) -> str:
    return STATUSES.get(str(code), str(code or "unknown").lower())


def appointment_view(appointment: dict[str, Any], customer: dict[str, Any] | None, zone: ZoneInfo) -> dict[str, Any]:
    """One appointment as the tools return it."""
    subs = appointment.get("subbookings") or []
    merged = (customer or {}).get("merged_data") or {}
    client = None
    if merged or (appointment.get("customer") or {}).get("id"):
        client = {
            "client_id": str(merged.get("id") or (appointment.get("customer") or {}).get("id") or ""),
            "name": merged.get("full_name") or (appointment.get("customer") or {}).get("name") or "",
        }
    services = [
        {
            "service_id": str((sub.get("service") or {}).get("id") or ""),
            "name": (sub.get("service") or {}).get("name") or "",
            "price": ((sub.get("service") or {}).get("variant") or {}).get("price"),
            "duration_minutes": ((sub.get("service") or {}).get("variant") or {}).get("duration"),
            "staff_id": str(sub.get("staffer_id") or ""),
            "staff": (sub.get("staffer") or {}).get("name") or "",
            "start": iso(sub.get("booked_from"), zone),
            "end": iso(sub.get("booked_till"), zone),
        }
        for sub in subs
    ]
    actions = appointment.get("actions") or {}
    return {
        "appointment_id": str(appointment.get("appointment_uid") or ""),
        "status": status_name(appointment.get("status")),
        "client": client,
        "services": services,
        "staff": services[0]["staff"] if services else "",
        "start": iso(appointment.get("booked_from"), zone),
        "end": iso(appointment.get("booked_till"), zone),
        "total": appointment.get("total_value"),
        "total_text": appointment.get("total"),
        "note": appointment.get("business_secret_note") or "",
        "client_note": appointment.get("business_note") or "",
        "can": sorted(name for name, allowed in actions.items() if allowed),
    }


async def read_appointment(ctx: ToolContext, appointment_id: str) -> dict[str, Any]:
    """The raw answer of GET appointments/{uid}/: `appointment` and `customer`."""
    uid = int_id(appointment_id, "appointment_id")
    return await ok_json(ctx, "GET", f"/appointments/{uid}/")


MAX_DAYS = 31


async def calendar(ctx: ToolContext, start: date, end: date) -> dict[str, Any]:
    """The calendar grid for a day range: every resource, booking, block and time off."""
    if end < start:
        raise ToolError("The last day is before the first day.", ErrorCode.INVALID_INPUT)
    if (end - start).days >= MAX_DAYS:
        raise ToolError(f"Ask for at most {MAX_DAYS} days at a time.", ErrorCode.INVALID_INPUT)
    params = {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "include_unconfirmed": "true",
        "version": "3",
        "resources_per_page": "500",
    }
    return await ok_json(ctx, "GET", "/calendar", params=params)


def staff_names(grid: dict[str, Any]) -> dict[int, str]:
    return {r["id"]: r.get("name") or "" for r in grid.get("resources") or [] if isinstance(r.get("id"), int)}


# Time off is Shifts' whole-day absence, a block is the calendar's time reservation; one id names both.
TIME_OFF_REASONS = ("vacation", "sick_day", "personal_day", "training", "early", "late", "no_show", "other")


def time_off_id(kind: str, raw: Any) -> str:
    return f"{'off' if kind == 'time_off' else 'block'}-{raw}"


def parse_time_off_id(value: str) -> tuple[str, int]:
    kind, _, raw = value.strip().partition("-")
    if kind not in ("off", "block") or not raw.isdigit():
        raise ToolError(
            "time_off_id comes from add_time_off or list_time_off (off-… or block-…).", ErrorCode.INVALID_INPUT
        )
    return ("time_off" if kind == "off" else "block"), int(raw)

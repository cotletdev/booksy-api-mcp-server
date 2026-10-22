"""Requests and shapes shared by the clients, services, staff and business hours tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from booksy_api_mcp.booksy.calendar import status_name
from booksy_api_mcp.booksy.client import headers, session
from booksy_api_mcp.core.errors import AuthExpiredError, ErrorCode, ToolError

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext


def _message(body: Any) -> str | None:
    """Booksy's own words from a 400: `{"errors": [{"description"}]}` or DRF `{"field": ["..."]}`."""
    if isinstance(body, dict):
        for item in body.get("errors") or []:
            if isinstance(item, dict) and item.get("description"):
                return str(item["description"])
        for key, value in body.items():
            if isinstance(value, list) and value and isinstance(value[0], str):
                return f"{key}: {value[0]}"
    return None


async def api(
    ctx: ToolContext,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    payload: Any = None,
    not_found: str = "Booksy has no such record in this business.",
) -> Any:
    """One call under the open business (`path` after `~`); the answer's JSON.

    404 and 400 become INVALID_INPUT with Booksy's message, any other failure TARGET_ERROR.
    """
    s = session(ctx)
    if s is None or s.business_id is None:
        raise AuthExpiredError("Booksy is signed out.")
    url = f"{s.api}/business_api/me/businesses/{s.business_id}{path}"
    kwargs: dict[str, Any] = {"headers": headers(ctx, s)}
    if params:
        kwargs["params"] = {k: v for k, v in params.items() if v is not None}
    if payload is not None:
        kwargs["json"] = payload
    response = await ctx.call(method, url, **kwargs)
    if response.status in (200, 201):
        return response.json() if response.text else {}
    if response.status == 204:
        return {}
    if response.status == 404:
        raise ToolError(not_found, ErrorCode.INVALID_INPUT)
    if response.status == 400:
        try:
            body = response.json()
        except ToolError:
            body = None
        raise ToolError(_message(body) or "Booksy refused the request.", ErrorCode.INVALID_INPUT)
    raise ToolError(f"Booksy answered {response.status}.", ErrorCode.TARGET_ERROR)


def split_name(full: str) -> tuple[str, str]:
    """`Anna Maria Nowak` -> (`Anna Maria`, `Nowak`); one word is a first name."""
    parts = full.strip().split()
    if not parts:
        raise ToolError("name must not be empty.", ErrorCode.INVALID_INPUT)
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def client_out(entry: dict[str, Any]) -> dict[str, Any]:
    """A client card from `customers` (list, search, one card, create, update): the fields a salon uses.

    GET `customers/{id}` wraps the card in `customer` (next to `bookings`); the others answer it bare.
    """
    if isinstance(entry.get("customer"), dict):
        entry = entry["customer"]
    card = entry.get("merged_data") or entry.get("business_customer") or {}
    recent = entry.get("recent_visit")
    return {
        "client_id": card.get("id") or entry.get("_id"),
        "name": card.get("full_name") or f"{card.get('first_name') or ''} {card.get('last_name') or ''}".strip(),
        "first_name": card.get("first_name") or "",
        "last_name": card.get("last_name") or "",
        "email": card.get("email") or None,
        "phone": card.get("cell_phone") or None,
        "birthday": card.get("birthday"),
        "note": card.get("business_secret_note") or "",
        "tags": [t.get("name", t) if isinstance(t, dict) else t for t in card.get("tags") or []],
        "blocked": bool(card.get("blacklisted") or entry.get("blacklisted")),
        "booksy_user": card.get("user") is not None,
        "created": card.get("created"),
        "last_visit": (recent.get("booked_from") if isinstance(recent, dict) else recent) or None,
        "visits": entry.get("booking_count") or 0,
        "no_shows": entry.get("no_shows") or 0,
        "cancellations": entry.get("canceled") or 0,
        "revenue": entry.get("revenue") or 0,
    }


def contact_fields(args: dict[str, Any]) -> dict[str, Any]:
    """Tool input -> Booksy's card fields; only what the caller gave."""
    body: dict[str, Any] = {}
    if args.get("name") is not None:
        body["first_name"], body["last_name"] = split_name(str(args["name"]))
    for ours, theirs in (("phone", "cell_phone"), ("email", "email"), ("note", "business_secret_note")):
        if args.get(ours) is not None:
            body[theirs] = args[ours]
    if args.get("birthday") is not None:
        body["birthday"] = args["birthday"]
    return body


CLIENT_EXAMPLE: dict[str, Any] = {
    "client_id": 132355511,
    "name": "Anna Novak",
    "first_name": "Anna",
    "last_name": "Novak",
    "email": "anna.novak@example.com",
    "phone": None,
    "birthday": None,
    "note": "Prefers mornings.",
    "tags": [],
    "blocked": False,
    "booksy_user": False,
    "created": "2026-10-21T19:55:28",
    "last_visit": None,
    "visits": 0,
    "no_shows": 0,
    "cancellations": 0,
    "revenue": 0.0,
}

# Booksy's day_of_week: 0 is Sunday.
WEEKDAYS = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")


def ranges(hours: list[dict[str, Any]] | None) -> list[str]:
    """`[{hour_from, hour_till}]` -> `["10:00-19:00"]`; closed is an empty list."""
    return [f"{h['hour_from']}-{h['hour_till']}" for h in hours or [] if h.get("hour_from") and h.get("hour_till")]


def visit_out(booking: dict[str, Any]) -> dict[str, Any]:
    """One entry of `customers/{id}/bookings`: an appointment with its subbookings (services, staff)."""
    subs = booking.get("subbookings") or [booking]
    services, staff = [], []
    for sub in subs:
        service = sub.get("service") or {}
        name = sub.get("service_name") or (service.get("name") if isinstance(service, dict) else None)
        if name and name not in services:
            services.append(name)
        staffer = sub.get("staffer") or {}
        names = [sub.get("staffer_name") or (staffer.get("name") if isinstance(staffer, dict) else None)]
        # The bookings list names the staff only in `resources[]` (type S; A is an appliance), 21.10.2026.
        names += [r.get("name") for r in sub.get("resources") or [] if isinstance(r, dict) and r.get("type") == "S"]
        for who in names:
            if who and who not in staff:
                staff.append(who)
    total = booking.get("total")
    return {
        "appointment_uid": booking.get("appointment_uid") or booking.get("id"),
        "start": booking.get("booked_from") or subs[0].get("booked_from"),
        "end": booking.get("booked_till") or subs[-1].get("booked_till"),
        "status": status_name(booking.get("status")),
        "services": services,
        "staff": staff,
        "total": total.get("formatted") if isinstance(total, dict) else total,
    }

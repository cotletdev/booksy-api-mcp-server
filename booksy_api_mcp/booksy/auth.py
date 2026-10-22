"""Who is signed in: Booksy's own answer for the account (business_api/me) and its businesses."""

from __future__ import annotations

from typing import TYPE_CHECKING

from booksy_api_mcp.booksy.client import headers, session
from booksy_api_mcp.core.errors import AuthExpiredError, ErrorCode, ToolError

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext


async def whoami(ctx: ToolContext) -> str | None:
    """None when the gateway holds no identity or Booksy says signed out; any other failure raises."""
    s = session(ctx)
    if s is None:
        return None
    sent = headers(ctx, s)
    try:
        me = await ctx.call("GET", f"{s.api}/business_api/me/", headers=sent)
        if me.status != 200:
            raise ToolError(f"Booksy answered {me.status} to who am I.", ErrorCode.TARGET_ERROR)
        owned = await ctx.call("GET", f"{s.api}/business_api/me/businesses/", headers=sent)
    except AuthExpiredError:
        return None
    account = me.json().get("account") or {}
    name = f"{account.get('first_name') or ''} {account.get('last_name') or ''}".strip() or account.get("email")
    businesses = (owned.json().get("businesses") or []) if owned.status == 200 else []
    # The identity's businessId is the one the panel has open; name it first.
    businesses.sort(key=lambda b: b.get("id") != s.business_id)
    names = ", ".join(b["name"] for b in businesses if b.get("name"))
    return f"{name} ({names})" if name and names else name or None

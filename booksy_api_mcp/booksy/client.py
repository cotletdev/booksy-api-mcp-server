"""Booksy Biz's session and API, recorded 21.10.2026.

The session is not a cookie. The panel on booksy.com keeps its identity in the `web-gateway.booksy.com` iframe:
localStorage key `_<country>_identity` (`_pl_identity`), JSON `{accessToken, loginType, profileType, profile}`.
The gateway script builds the key as `_${country}_identity` and deletes it on sign-out (CLEAR_IDENTITY).
booksy.com's own storage has no token. Every API call carries the token as `X-Access-Token`, the public
`X-Api-Key` of the web panel and `X-Fingerprint` (the `_bf` cookie on .booksy.com).

The API host is the country: `https://<country>.booksy.com/core/v2/...` (the bundle's `core` subdomain is
`{country}`), so the country comes from the identity key and a US account goes to us.booksy.com.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from booksy_api_mcp.core.context import ToolContext

WEB = "https://booksy.com"
GATEWAY = "https://web-gateway.booksy.com"
# Public key of the web panel (frontdesk), the same in every country.
API_KEY = "frontdesk-76661e2b-25f0-49b4-b33a-9d78957a58e3"
_IDENTITY_KEY = re.compile(r"^_([a-z]{2})_identity$")


@dataclass(frozen=True)
class Session:
    country: str
    token: str
    profile: dict[str, Any]

    @property
    def api(self) -> str:
        return f"https://{self.country}.booksy.com/core/v2"

    @property
    def business_id(self) -> int | None:
        return self.profile.get("businessId")


def _identity(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(value, dict) or not isinstance(value.get("accessToken"), str):
        return None
    return value if value["accessToken"] and isinstance(value.get("profile"), dict) else None


def session_of(local_storage: dict[str, dict[str, str]]) -> Session | None:
    """The signed-in identity in a jar's or a tab's `local_storage`; None when the gateway holds none.

    One browser can hold identities of several countries; the panel's last country (`app.country` on
    booksy.com) wins, else the first one found.
    """
    stored = local_storage.get(GATEWAY) or {}
    found: dict[str, dict[str, Any]] = {}
    for key, raw in stored.items():
        match = _IDENTITY_KEY.match(key)
        if match and (identity := _identity(raw)) is not None:
            found[match.group(1)] = identity
    if not found:
        return None
    last = (local_storage.get(WEB) or {}).get("app.country", "").strip('"').lower()
    country = last if last in found else sorted(found)[0]
    return Session(country=country, token=found[country]["accessToken"], profile=found[country]["profile"])


def session(ctx: ToolContext) -> Session | None:
    return session_of(ctx.profile.local_storage)


def headers(ctx: ToolContext, s: Session) -> dict[str, str]:
    """What the panel sends with every API call."""
    found = {
        "x-api-key": API_KEY,
        "x-access-token": s.token,
        "x-app-version": "3.0",
        "accept": "application/json",
        "origin": WEB,
        "referer": f"{WEB}/",
    }
    fingerprint = next((c.value for c in ctx.profile.cookies if c.name == "_bf" and c.value), None)
    if fingerprint:
        found["x-fingerprint"] = fingerprint
    return found


def request_headers(ctx: ToolContext) -> dict[str, str]:
    """The tools' identity headers for one request; only the public
    api key when the gateway holds no identity, so Booksy answers its signed-out 403."""
    s = session(ctx)
    return headers(ctx, s) if s is not None else {"x-api-key": API_KEY}

"""Everything the server knows about Booksy outside `booksy/`: names, domains and where the session lives.

The rest of the package reads these values and never names the app itself.
"""

from __future__ import annotations

NAME = "Booksy"
SLUG = "booksy"
# The command and the prefix of every environment variable (BOOKSY_MCP_HOME, BOOKSY_MCP_TOKEN ...).
CLI = "booksy-mcp"
ENV = "BOOKSY"
# Requests may reach only these hosts and their subdomains. Their cookies are read from Chrome.
DOMAINS = ("booksy.com",)
# Cookies present only while signed in. Booksy has none that carries the session, so a token cannot be pasted.
SESSION_COOKIES: tuple[str, ...] = ()
COOKIE_DOMAIN = ".booksy.com"
# localStorage read from Chrome at `connect`, by origin. The session is the `_<country>_identity` key of the
# web-gateway.booksy.com frame the panel embeds; booksy.com's `app.country` says which country the panel has open.
STORAGE_ORIGINS = ("https://web-gateway.booksy.com", "https://booksy.com")
# Present only while signed in: origin -> key pattern (regex).
SESSION_STORAGE = {"https://web-gateway.booksy.com": r"^_[a-z]{2}_identity$"}
LOGIN_URL = "https://booksy.com/pro/en-us/onboarding/Login"
# A final URL with one of these means the app signed the session out.
LOGGED_OUT_MARKERS: tuple[str, ...] = ()
# Text in a 403 body that means "sign in again": Booksy never answers 401, it names the token field that failed.
RELOGIN_MARKERS = ('"field":"auth_header_token"', '"field":"access_token"')
# URL path patterns of the account itself (sign-in, password, deletion): only GET may reach them.
ACCOUNT_PATHS = (
    r"/business_api/account(/|$)",
    r"/business_api/me/?$",
    r"/business_api/me/(businesses/\d+/)?account_deletion",
    r"/utils/(password_check|phone_check)",
)
# REST routes live under this path, the same as on cotlet.dev.
API_PREFIX = "/api/v1/booksy"
# Prepended to the MCP server's instructions: where an agent starts.
AGENT_START = (
    "Start with list_services and list_staff: their ids are what the calendar tools take. "
    "Times are local to the business."
)

# Booksy API and MCP server, self-hosted

<!-- mcp-name: dev.cotlet/booksy -->

A **Booksy API** and a **Booksy MCP server** you run on your own computer, in Python, on the session of your own Google Chrome. All 28 Booksy Biz tools we run in production at [Cotlet](https://cotlet.dev/integrations/booksy-api-mcp-server): the calendar, open slots, time off, clients, services and staff, reviews, Message Blasts and Stats & Reports.

Booksy has no self-serve API for business owners and no official MCP server. This repo gives you both:

- **MCP server** for Claude Code, Claude Desktop, Cursor, Codex and any MCP client, over stdio or HTTP. [Setup](#mcp-server)
- **REST API** on `http://127.0.0.1:8787/api/v1/booksy`, with OpenAPI docs at `/docs`. [Setup](#rest-api)
- **Python**: `call("list_appointments", {"from": "2026-10-27", "to": "2026-10-27"})`, plus 9 ready scripts in [`examples/`](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/examples/).

It is for technical people who want to run it themselves, **for noncommercial use only** ([license](#license)). If you want it running 24/7 on a server, kept working when Booksy changes its panel, for a team or a business, use the [hosted version at cotlet.dev](https://cotlet.dev/integrations/booksy-api-mcp-server).

[![Booksy MCP server](https://img.shields.io/badge/Booksy%20MCP-28%20tools-6d4aef)](#all-28-tools)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-141318)](#requirements)
[![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/license-PolyForm%20Noncommercial-141318)](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/LICENSE)
[![MCP Badge](https://lobehub.com/badge/mcp/cotletdev-booksy-api-mcp-server)](https://lobehub.com/mcp/cotletdev-booksy-api-mcp-server)

```bash
uv tool install booksy-api-mcp                  # or: pip install booksy-api-mcp
booksy-mcp connect                                 # reads your Booksy Biz session from Chrome
booksy-mcp call list_services
claude mcp add booksy -- uvx booksy-api-mcp mcp
```

## Contents

- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Install](#install)
- [Connect your Chrome](#connect-your-chrome)
- [MCP server](#mcp-server)
- [REST API](#rest-api)
- [Python and the example scripts](#python-and-the-example-scripts)
- [All 28 tools](#all-28-tools)
- [Configuration](#configuration)
- [Security and your Booksy account](#security-and-your-booksy-account)
- [Errors](#errors)
- [Self-hosted or hosted](#self-hosted-or-hosted)
- [FAQ](#faq)
- [License](#license)

## How it works

```text
AI agent (MCP) / script (REST, Python) ──▶ booksy-mcp on your computer ──your Booksy session──▶ <country>.booksy.com
                                                   ▲
                         booksy-mcp connect ───────┘ reads it once from your Chrome (DevTools Protocol)
```

1. You sign in to Booksy Biz in your own Chrome at [booksy.com/pro](https://booksy.com/pro/en-us/onboarding/Login), the way you always do.
2. `booksy-mcp connect` attaches to that Chrome through the Chrome DevTools Protocol and reads your session. Booksy does not keep it in a cookie. The panel stores it in the localStorage of its `web-gateway.booksy.com` frame, so `connect` reads that storage, the booksy.com cookies and the panel's country, and saves them to `~/.config/booksy-api-mcp/session.json`, readable by your user only. It never sees or stores your password.
3. Every tool call is a request to the API the Booksy Biz web panel calls (`<country>.booksy.com/core/v2`, so `us.booksy.com` for a US business and `pl.booksy.com` for a Polish one), sent with [curl_cffi](https://github.com/lexiforest/curl_cffi), which copies Chrome's TLS fingerprint. No headless browser runs.

When Booksy signs you out, the server reads the session from Chrome again, if Chrome is open with remote debugging on.

## Requirements

- Python 3.11 or newer.
- Google Chrome 144 or newer, signed in to Booksy Biz. Any Chrome or Chromium works with a [debugging port](#option-b-a-chrome-with-a-debugging-port).
- macOS, Linux or Windows.
- A Booksy Biz owner account. Some reports, such as Staff Members, need Booksy Biz Pro. Booksy sends one-time Message Blasts on a paid plan only, not during the free trial.

## Install

From [PyPI](https://pypi.org/project/booksy-api-mcp/):

```bash
uv tool install booksy-api-mcp       # or: pipx install booksy-api-mcp, or: pip install booksy-api-mcp
booksy-mcp --version
```

MCP clients can also run it with no install: `uvx booksy-api-mcp mcp`.

From source:

```bash
git clone https://github.com/cotletdev/booksy-api-mcp-server.git
cd booksy-api-mcp-server
python3 -m venv .venv
. .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -e .
booksy-mcp --version
```

With [uv](https://docs.astral.sh/uv/): `uv venv && uv pip install -e .`, then `uv run booksy-mcp ...`.

Setting it up with an AI agent (Claude Code, Codex, Cursor)? Open it in this folder and ask it to set up the repo: [`AGENTS.md`](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/AGENTS.md) tells it every step, and it asks you only for the steps in Chrome.

To update: `uv tool upgrade booksy-api-mcp` (or `pip install -U booksy-api-mcp`), from source `git pull && pip install -e .`. We copy every change of the hosted Booksy tools into this repo.

## Connect your Chrome

### Option A: your everyday Chrome (recommended)

1. Open `chrome://inspect/#remote-debugging` in Chrome and switch **remote debugging** on. Chrome then accepts DevTools connections from programs on this computer, and asks you before each one.
2. Make sure you are signed in to Booksy Biz at [booksy.com/pro](https://booksy.com/pro/en-us/onboarding/Login). Keep a tab of the panel open, because `connect` reads the session in it. With no Booksy tab open, it opens one in the background and closes it again.
3. Run:

   ```bash
   booksy-mcp connect
   ```

4. Chrome asks whether to allow the connection. Click **Allow**.

```text
Saved 41 Booksy cookies and 50 localStorage keys to /Users/you/.config/booksy-api-mcp/session.json
Signed in to Booksy as Maria Lopez (Studio Maria)
```

You can switch remote debugging off again afterwards. Leave it on if you want the server to pick up a new session by itself after Booksy signs you out.

`connect` looks for Chrome's `DevToolsActivePort` file in the default profile folder. For Chrome Beta, Canary or a custom profile folder, pass `--profile-dir "<folder>"`.

### Option B: a Chrome with a debugging port

Chrome does not open a debugging port on your default profile, so start a separate one, sign in to Booksy Biz there once, and connect to it:

```bash
# macOS
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-booksy"
# Linux
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-booksy"
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\.chrome-booksy"

booksy-mcp connect --cdp http://127.0.0.1:9222
```

`--cdp` also takes a `ws://` DevTools URL, for example of a Chrome on another machine reached over an SSH tunnel.

There is no option to paste a cookie by hand, since Booksy has no session cookie. A server with no Chrome can use a `session.json` copied from a machine where `connect` ran.

Check the session at any time:

```bash
booksy-mcp status
```

## MCP server

The MCP server lists every tool with its input schema, a description written for agents, and hints. Read tools are marked read-only, and tools that reach clients (bookings, reschedules, cancellations, review replies, blasts) are marked so your client asks before running them.

### Claude Code

```bash
claude mcp add booksy -- uvx booksy-api-mcp mcp
# read only:
claude mcp add booksy -- uvx booksy-api-mcp mcp --read-only
```

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "booksy": {
      "command": "uvx",
      "args": ["booksy-api-mcp", "mcp"]
    }
  }
}
```

### Cursor

`~/.cursor/mcp.json`, the same block as Claude Desktop. A ready copy is in [`mcp.json`](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/mcp.json).

### Codex

`~/.codex/config.toml`:

```toml
[mcp_servers.booksy]
command = "uvx"
args = ["booksy-api-mcp", "mcp"]
```

### Over HTTP

`booksy-mcp serve` also serves MCP over streamable HTTP at `http://127.0.0.1:8787/mcp`, for clients that take a URL:

```bash
booksy-mcp serve
claude mcp add --transport http booksy http://127.0.0.1:8787/mcp
```

Then ask your agent things like:

> *What does tomorrow look like? List the appointments and any gaps longer than an hour.*
>
> *Tom is off on Friday. Move his bookings to whoever is free at about the same time, and show me the plan first.*
>
> *Compare last week's revenue per staff member with the week before.*
>
> *Which clients have not been in for 60 days and have nothing booked?*

## REST API

```bash
booksy-mcp serve                   # http://127.0.0.1:8787, MCP at /mcp, docs at /docs
```

Each tool has its own route under `/api/v1/booksy`, the same paths as the hosted API at cotlet.dev, so code written against one works with the other. Path parts and the query string are arguments, and a JSON body adds the rest.

```bash
curl 'http://127.0.0.1:8787/api/v1/booksy/services'
curl 'http://127.0.0.1:8787/api/v1/booksy/appointments?from=2026-10-27&to=2026-10-31'
curl 'http://127.0.0.1:8787/api/v1/booksy/services/8307205/open-slots?date=2026-10-27'
curl -X POST http://127.0.0.1:8787/api/v1/booksy/staffs/882081/time-offs \
  -H 'Content-Type: application/json' \
  -d '{"start": "2026-11-02", "end": "2026-11-06", "reason": "vacation"}'
```

Any tool by name, body as its arguments:

```bash
curl -X POST http://127.0.0.1:8787/api/v1/booksy/tools/find_client -d '{"query": "nowak"}'
```

- `GET /api/v1/booksy/tools`: every tool with its route, input schema and an example answer.
- `GET /docs`: interactive OpenAPI docs, `GET /openapi.json` the schema, for n8n, Postman or a generated client.
- Answers are JSON. `list_clients` returns `next_cursor`; pass it back as `cursor` for the next page. Reviews and notifications take `page`.

The server listens on `127.0.0.1` only. To reach it from another device of yours, set a token, and every request then needs `Authorization: Bearer <token>`:

```bash
BOOKSY_MCP_TOKEN=$(openssl rand -hex 24) booksy-mcp serve --host 0.0.0.0
```

## Python and the example scripts

Straight from Python, no server needed:

```python
from booksy_api_mcp import call
from booksy_api_mcp.scripting import paginate, write_rows

services = call("list_services")["services"]
day = call("list_appointments", {"from": "2026-10-27", "to": "2026-10-27"})["appointments"]
clients = list(paginate("list_clients", {"not_visited_days": 60, "limit": 100}, "clients"))
write_rows(clients, "slipping-away.csv")
call("add_time_off", staff_id="882081", start="2026-11-02T13:00", end="2026-11-02T14:00", reason="Lunch")
```

Or one tool from the shell: `booksy-mcp call find_open_slots service_id=8307205 date=2026-10-27`, or with a JSON object. An ID stays text where the tool takes text.

Times are local to the business. A date-time without a zone is read in the business's time zone, and answers carry its offset.

Ready scripts in [`examples/`](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/examples/). Each prints JSON or a short list, takes `--out file.csv` or `--out file.json` where it makes sense, and `--help`:

| Script | What it does |
|---|---|
| [`tomorrows_appointments.py`](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/examples/tomorrows_appointments.py) | Tomorrow's appointments, one line each, and the open slots left for a service. `--date`, `--staff-id`. |
| [`reschedule_day.py`](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/examples/reschedule_day.py) | Moves one staff member's appointments on a day to colleagues free within an hour of the original time. Prints the plan; `--apply` moves them, asking each time. |
| [`block_time_off.py`](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/examples/block_time_off.py) | Adds whole days off or blocks hours on one day, or removes a time off. |
| [`export_clients.py`](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/examples/export_clients.py) | Clients to CSV or JSON: contact, note, visits, no-shows, revenue, last visit. `--search`, `--not-visited-days`. |
| [`lapsed_clients.py`](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/examples/lapsed_clients.py) | Clients not seen for N days, minus anyone booked in the next 30 days. |
| [`win_back_blast.py`](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/examples/win_back_blast.py) | One Message Blast to those lapsed clients, after it shows the reach and SMS cost and asks. |
| [`weekly_staff_report.py`](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/examples/weekly_staff_report.py) | Appointments and revenue per staff member, last week against the week before, big moves flagged. |
| [`unanswered_reviews.py`](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/examples/unanswered_reviews.py) | Reviews without a reply, lowest rating first; `--reply-to` posts a reply. |
| [`add_client.py`](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/examples/add_client.py) | Adds a client card with no invitation, or a note to an existing one. |

```bash
python examples/tomorrows_appointments.py --open-slots-for 8307205
python examples/reschedule_day.py --staff-id 882081 --date 2026-10-27
python examples/export_clients.py --not-visited-days 60 --out slipping-away.csv
```

On a schedule, cron on your own computer works while it is on: `0 19 * * * cd ~/booksy-api-mcp-server && .venv/bin/python examples/tomorrows_appointments.py`.

## All 28 tools

IDs come from the list tools: `service_id` from `list_services`, `staff_id` from `list_staff`, `client_id` from `list_clients` or `find_client`, `appointment_id` from `list_appointments`. `booksy-mcp tools` prints this list, `booksy-mcp tools --json` adds the input schemas.

### Calendar

| Tool | Access | REST route | What it does |
|---|---|---|---|
| `list_appointments` | read | `GET /appointments` | Appointments in a date range with client, service, staff, time and status. |
| `get_appointment` | read | `GET /appointments/{appointment_id}` | One appointment: services, staff, times, price, client and notes. |
| `find_open_slots` | read | `GET /services/{service_id}/open-slots` | Free start times for a service on one day, from working hours, bookings, blocks and time off. |
| `create_appointment` | write | `POST /clients/{client_id}/appointments` | Book a client for one service at a start time; Booksy checks the slot first. |
| `reschedule_appointment` | write | `POST /appointments/{appointment_id}/reschedule` | Move an appointment to a new start time, and optionally to another staff member. |
| `cancel_appointment` | write | `POST /appointments/{appointment_id}/cancel` | Cancel an appointment and free its time in the calendar. |

### Time off

| Tool | Access | REST route | What it does |
|---|---|---|---|
| `list_time_off` | read | `GET /time-offs` | Staff time off and blocked hours in a date range. |
| `add_time_off` | write | `POST /staffs/{staff_id}/time-offs` | Block a staff member's calendar so no one can book it: whole days off or a few hours. |
| `remove_time_off` | write | `DELETE /staffs/{staff_id}/time-offs/{time_off_id}` | Remove time off or a blocked period so the time can be booked again. |

### Clients

| Tool | Access | REST route | What it does |
|---|---|---|---|
| `list_clients` | read | `GET /clients` | Clients with contact details, visit counts and last visit, plus Booksy's client groups. |
| `find_client` | read | `GET /clients/search` | Client cards matching a name, email or phone. |
| `get_client` | read | `GET /clients/{client_id}` | One client card: contact details, private note, counts and visit history. |
| `add_client` | write | `POST /clients` | Add a client card to your client list. Needs a phone or an email. |
| `update_client` | write | `PATCH /clients/{client_id}` | Change a client card's name, phone, email, birthday or private note. |
| `add_client_note` | write | `POST /clients/{client_id}/notes` | Add a dated line to a client's private note, keeping what is there. |
| `delete_client` | write | `DELETE /clients/{client_id}` | Remove a client card from your client list. |

### Business setup

| Tool | Access | REST route | What it does |
|---|---|---|---|
| `list_services` | read | `GET /services` | Your service menu with category, variants, duration, price and the staff who offer each. |
| `list_staff` | read | `GET /staff` | Staff members with their working hours for a week and the services they offer. |
| `get_business_hours` | read | `GET /business-hours` | Weekly opening hours, time zone and booking lead times of the business. |
| `get_business_profile` | read | `GET /business` | Your business's name, address, contact, opening hours, booking policy, rating and plan status. |
| `get_settings` | read | `GET /settings` | Text message allowance and usage, client message channels and your notification settings. |
| `list_notifications` | read | `GET /notifications` | Notifications from the panel's bell: new bookings, changes, cancellations, reviews. |

### Reviews

| Tool | Access | REST route | What it does |
|---|---|---|---|
| `list_reviews` | read | `GET /reviews` | Client reviews of your business with rating, text, services, staff and your reply. |
| `reply_to_review` | write | `PUT /reviews/{review_id}/reply` | Post or change your public reply to a client's review. |

### Message Blasts

| Tool | Access | REST route | What it does |
|---|---|---|---|
| `list_message_blasts` | read | `GET /message-blasts` | Message Blast templates (automated and one-time) and the blasts scheduled to go out. |
| `estimate_message_blast` | read | `GET /message-blasts/estimate` | Count who a Message Blast would reach and its SMS cost, without sending it. |
| `send_message_blast` | write | `POST /message-blasts` | Send one message to chosen clients by email, SMS or push notification. |

### Stats & Reports

| Tool | Access | REST route | What it does |
|---|---|---|---|
| `get_report` | read | `GET /reports/{category}` | Numbers from Stats & Reports for a day, week, month or year, as JSON. |

Writes run Booksy's own dry run first, and send the client no notice unless you pass `notify_client`. New clients get no invitation. `send_message_blast` refuses an empty client list, because Booksy reads an empty list as every client.

Never built, on purpose: your Booksy sign-in, email, password and account deletion, and anything that moves money (subscription, payments, payouts, billing). Every request passes a guard that refuses those Booksy paths.

## Configuration

| Variable | Default | What it does |
|---|---|---|
| `BOOKSY_MCP_HOME` | `~/.config/booksy-api-mcp` | Folder of `session.json`. |
| `BOOKSY_PROXY` | | Proxy for every request to Booksy, e.g. `http://user:pass@host:port`. |
| `BOOKSY_MCP_READ_ONLY` | | `1` hides and refuses every tool that changes Booksy (same as `--read-only`). |
| `BOOKSY_MCP_TOKEN` | | Bearer token required by `serve`; needed to listen beyond `127.0.0.1`. |
| `BOOKSY_MCP_HOST`, `BOOKSY_MCP_PORT` | `127.0.0.1`, `8787` | Address of `serve`. |

## Security and your Booksy account

- **Your password never reaches this code.** Only the session the panel already keeps is read, and only that of booksy.com.
- **The session file is yours.** `session.json` is created with mode 0600 and holds your Booksy access token. Anyone who has it can act as you in Booksy Biz, so keep it out of git and shared folders.
- **Local by default.** `serve` binds to `127.0.0.1` and refuses another address without `BOOKSY_MCP_TOKEN`.
- **booksy.com only.** Requests and redirects outside booksy.com are refused.
- **Read-only mode.** `--read-only` or `BOOKSY_MCP_READ_ONLY=1` exposes the 17 read tools only.
- **Actions reach real people.** A booking, a move with `notify_client`, a cancellation, a review reply and a blast reach your clients. MCP clients ask before running them; a script does not, so try it on a test client of your own first.
- **Do not spam.** Blasts to people who did not agree break Booksy's rules and the law in many countries. You are responsible for what runs in your account.

## Errors

The REST API answers `{"error": "<code>", "message": "..."}`. The MCP server returns the same code and message as a tool error.

| Status | Code | What to do |
|---|---|---|
| 401 | `auth_required`, `auth_expired` | No session, or Booksy signed you out. Sign in to Booksy Biz in Chrome and run `booksy-mcp connect`. |
| 403 | `app_permission_denied` | Your Booksy plan or role cannot do this, e.g. a Pro report on Booksy Biz Lite. |
| 403 | `scope_denied` | The server runs read-only, or the request would change your Booksy account itself. |
| 403 | `target_blocked` | Booksy refused the request or showed a bot check. Open the panel in Chrome once, then retry. |
| 409 | `captcha_required` | Booksy asks for a CAPTCHA. Solve it in Chrome. |
| 422 | `invalid_input` | An argument is missing or wrong; the message names it. |
| 429 | `rate_limited` | Booksy is limiting the account. Wait a few minutes. |
| 502 | `target_error` | Booksy answered with an error, or changed its panel. `git pull` for the latest tools, or [open an issue](https://github.com/cotletdev/booksy-api-mcp-server/issues). |

## Self-hosted or hosted

| | This repo | [Cotlet, hosted](https://cotlet.dev/integrations/booksy-api-mcp-server) |
|---|---|---|
| Tools | the same 28 | the same 28 |
| Runs | on your computer, while it is on | in the cloud, 24/7 |
| Booksy session | your Chrome, saved in a local file | your own Cloud Browser in the EU, profile encrypted with AES-256-GCM |
| When Booksy changes its panel | `git pull` once we have fixed it | fixed for you, every tool tested daily |
| Approvals | your MCP client asks per call | bookings, reschedules, replies and blasts wait for your OK, switchable per tool |
| Works with | MCP clients on your machine, local scripts | Claude.ai and ChatGPT connectors, n8n, Make, Zapier, any HTTP client |
| Who may use it | you, for noncommercial use | teams, businesses, agencies |
| Price | free | free 7-day trial with 2,000 credits, no card; then one-time packs from $29 for 5,000 credits |

On the hosted version a successful call uses 20 to 30 credits (25 for most tools), failed calls are free, and the Cloud Browser uses 50 credits a day while it has an app enabled for agents. [Full pricing](https://cotlet.dev/pricing).

## FAQ

**Does Booksy have an official API?**
Not one a business owner can use. Booksy runs a partner API whose docs at docs.booksy.com ask for a login, so you cannot get keys for your own account (checked 11 Oct 2026). Stats & Reports and Message Blasts are not among its public areas. Details: [cotlet.dev/integrations/booksy-api-mcp-server](https://cotlet.dev/integrations/booksy-api-mcp-server).

**Is there a Booksy MCP server for Claude, ChatGPT or Cursor?**
Yes, this one runs on your machine: `booksy-mcp mcp` for Claude Code, Claude Desktop, Cursor and Codex. ChatGPT and Claude.ai connectors need a public HTTPS URL, which the [hosted Booksy MCP server](https://cotlet.dev/integrations/booksy-api-mcp-server) gives you.

**Is there a Booksy Zapier app?**
We could not confirm one. Owners who want bookings elsewhere forward Booksy confirmation emails to a Zapier email parser. That copies new bookings one way and cannot change anything in Booksy.

**Can I export my Booksy clients to CSV?**
Yes: `python examples/export_clients.py --out clients.csv`. Every client card with contact details, note, visits, no-shows, revenue and last visit, across all pages.

**Can it find free slots and book for me?**
`find_open_slots` gives the free starts for a service on a day, per staff member, each checked with Booksy's own dry run. `create_appointment` books one of them for a client, and the client hears about it only with `notify_client`.

**Can it send Message Blasts?**
Yes, `send_message_blast` by email, SMS or push, on a paid Booksy plan. Run `estimate_message_blast` first for the reach and the SMS cost. In the EU only clients who gave marketing consent get it.

**Does it work outside the US?**
Yes. Booksy runs a separate API per country, and the server picks it from your session: `us.booksy.com`, `pl.booksy.com`, `es.booksy.com` and so on.

**Why does it need my Chrome?**
To read your Booksy session without your password. Chrome is used once per sign-in, not for each call.

**What happens when Booksy signs me out?**
Calls fail with `auth_expired`. With Chrome remote debugging on, the server reads the new session on the next call (click Allow when Chrome asks). Otherwise run `booksy-mcp connect` again.

**Can it run on a VPS or in Docker?**
Technically yes, with a `session.json` copied from your computer. Booksy then sees your session from a datacenter IP, which looks less like you. For an always-on setup the hosted version keeps your session in your own Cloud Browser on a fixed IP.

**Will my Booksy account get banned?**
Requests carry Chrome's fingerprint and go out one at a time, as you would click. Nobody can promise a platform never acts. Keep to your normal use and do not blast people who did not agree.

**Can I use it for my salon or for my clients?**
No. The license allows noncommercial use only, and running your own business counts as business use. For a salon, a team or client work, use [Cotlet](https://cotlet.dev) or write to [contact@cotlet.dev](mailto:contact@cotlet.dev).

**Is it open source?**
The source is public, the license is not an open source license: noncommercial use only, no business use.

**A tool broke or I need another one.**
[Open an issue](https://github.com/cotletdev/booksy-api-mcp-server/issues) with the tool name and the error message.

## License

[PolyForm Noncommercial License 1.0.0](https://github.com/cotletdev/booksy-api-mcp-server/blob/main/LICENSE). In short:

- **Allowed:** noncommercial use: you, for your own personal purposes with your own Booksy account, or a charity, school, public research or government body. Changing the code, and sharing it under the same license.
- **Not allowed:** any commercial use, your own business included; client work; selling or offering it, or a service built on it.

---

<p>
  <a href="https://cotlet.dev">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="assets/logo-white.svg">
      <img src="https://raw.githubusercontent.com/cotletdev/booksy-api-mcp-server/main/assets/logo.svg" alt="Cotlet" width="120">
    </picture>
  </a>
</p>

Maintained by [Cotlet](https://cotlet.dev) ([@cotletdev](https://x.com/cotletdev)). Booksy is a trademark of its owner. This project is unofficial and not affiliated with, endorsed or sponsored by Booksy.

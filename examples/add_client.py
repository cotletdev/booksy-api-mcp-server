#!/usr/bin/env python3
"""Add a client card to Booksy, or add a note to one that exists. The client gets no invitation.

    python add_client.py --name "Anna Nowak" --phone "+48 600 100 200" --email anna@example.com
    python add_client.py --client-id 132355511 --note "Allergic to ammonia dyes"

Use it to move clients from a spreadsheet: one call per row.
"""

import argparse
import json

from booksy_api_mcp.scripting import call, run


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--name")
    parser.add_argument("--phone")
    parser.add_argument("--email")
    parser.add_argument("--client-id", type=int, help="Add --note to this client instead")
    parser.add_argument("--note")
    args = parser.parse_args()

    if args.client_id:
        if not args.note:
            parser.error("--note is required with --client-id")
        result = call("add_client_note", {"client_id": args.client_id, "text": args.note})
    else:
        if not args.name:
            parser.error("--name is required")
        result = call("add_client", {"name": args.name, "phone": args.phone, "email": args.email, "note": args.note})
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run(main)

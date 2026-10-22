#!/usr/bin/env python3
"""List Booksy reviews you have not replied to yet, lowest rating first, and optionally reply to one.

    python unanswered_reviews.py
    python unanswered_reviews.py --reply-to 4410925 --text "Thanks, see you next month!"

A reply is public on your Booksy profile.
"""

import argparse
import json

from booksy_api_mcp.scripting import call, run


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--reply-to", type=int, metavar="REVIEW_ID")
    parser.add_argument("--text", help="The reply")
    args = parser.parse_args()

    if args.reply_to:
        if not args.text:
            parser.error("--text is required with --reply-to")
        print(json.dumps(call("reply_to_review", {"review_id": args.reply_to, "reply": args.text}), indent=2))
        return
    pending, page = [], 1
    while page:
        found = call("list_reviews", {"sort": "lowest", "page": page, "per_page": 50})
        pending += [r for r in found["reviews"] if not r.get("reply")]
        page = found.get("next_page")
    print(f"{len(pending)} reviews without a reply")
    for r in pending:
        print(f"  [{r['review_id']}] {r['rating']}/5 {r['client']}: {(r.get('text') or r.get('title') or '')[:80]}")


if __name__ == "__main__":
    run(main)

#!/usr/bin/env python3
"""Send one Message Blast to clients who have not been in for N days. Shows the reach and cost, asks, then sends.

    python win_back_blast.py --days 45 --channel email --subject "We miss you" --message "20% off your next cut this month."
    python win_back_blast.py --days 60 --channel sms --message "Salon X: 20% off this week. Book in the app." --yes

Clients with a visit booked in the next 30 days are skipped. Where the law asks for marketing consent (EU), only
clients who agreed get it. Booksy sends one-time blasts on a paid plan only, not during the free trial.
"""

import argparse
import sys

from lapsed_clients import lapsed

from booksy_api_mcp.scripting import call, run


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--days", type=int, default=45)
    parser.add_argument("--channel", choices=["email", "sms", "push"], default="email")
    parser.add_argument("--subject", help="Email subject")
    parser.add_argument("--message", required=True)
    parser.add_argument("--yes", action="store_true", help="Send without asking")
    args = parser.parse_args()

    clients = lapsed(args.days)
    if not clients:
        sys.exit("Nobody to send to.")
    ids = [c["client_id"] for c in clients]
    estimate = call("estimate_message_blast", {"channel": args.channel, "message": args.message, "client_ids": ids})
    reach = estimate["consented"] if estimate["consent_required"] else estimate["all"]
    print(
        f"{len(ids)} lapsed clients, {reach['recipients']} reachable by {args.channel}, SMS cost {reach['sms_cost_total']}"
    )
    print("Sample:", ", ".join(c["name"] for c in clients[:5]))
    print("Message:", args.message)
    if not args.yes and input("Send? [y/N] ").strip().lower() != "y":
        sys.exit("Not sent.")
    params = {"channel": args.channel, "subject": args.subject, "message": args.message, "client_ids": ids}
    sent = call("send_message_blast", params)
    print(f"{sent['status']}: {sent['recipients']} recipients")


if __name__ == "__main__":
    run(main)

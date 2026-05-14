from __future__ import annotations

import argparse
import sys
import time
from typing import Iterable

from .config import KNOWN_ZONES, ConfigError, load_config
from .mailjet import MailjetError, MailjetNotifier
from .recreation import AvailabilityResult, RecreationClient, RecreationError, check_availability


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "zones":
            print_zones()
            return 0
        if args.command == "check":
            return run_check(args)
        if args.command == "watch":
            return run_watch(args)
    except (ConfigError, RecreationError, MailjetError, KeyboardInterrupt) as exc:
        if isinstance(exc, KeyboardInterrupt):
            print("\nStopped.", file=sys.stderr)
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="passfinder", description="Watch Recreation.gov permit availability.")
    subparsers = parser.add_subparsers(dest="command")

    check = subparsers.add_parser("check", help="Run one availability check")
    check.add_argument("--config", default="passfinder.config.json", help="Path to config JSON")
    check.add_argument("--notify", action="store_true", help="Send Mailjet email if availability is found")

    watch = subparsers.add_parser("watch", help="Poll availability and send new-match alerts")
    watch.add_argument("--config", default="passfinder.config.json", help="Path to config JSON")

    subparsers.add_parser("zones", help="Print known zone names and IDs")
    return parser


def run_check(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    results = check_availability(config, RecreationClient())
    print_results(results)
    if args.notify:
        send_notifications(config, [result for result in results if result.available])
    return 0


def run_watch(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    seen: set[tuple[str, str]] = set()
    client = RecreationClient()
    notifier = MailjetNotifier()

    print(f"Watching {len(config.targets)} targets every {config.poll_minutes} minutes. Press Ctrl+C to stop.")
    while True:
        results = check_availability(config, client)
        print_results(results)

        new_matches = [result for result in results if result.available and result.key not in seen]
        if new_matches:
            sent = notifier.send(config, new_matches)
            seen.update(result.key for result in new_matches)
            if sent:
                print(f"Sent Mailjet notification for {len(new_matches)} new match(es).")
            else:
                print("Mailjet notifications are disabled; marked new matches as seen.")
        else:
            print("No new availability alerts.")

        time.sleep(config.poll_minutes * 60)


def send_notifications(config, matches: list[AvailabilityResult]) -> None:
    if not matches:
        print("No available targets, so no email was sent.")
        return
    sent = MailjetNotifier().send(config, matches)
    if sent:
        print(f"Sent Mailjet notification for {len(matches)} match(es).")
    else:
        print("Mailjet notifications are disabled; no email was sent.")


def print_zones() -> None:
    for name, zone_id in sorted(KNOWN_ZONES.items()):
        print(f"{zone_id}  {name}")


def print_results(results: Iterable[AvailabilityResult]) -> None:
    results = list(results)
    if not results:
        print("No targets configured.")
        return

    headers = ("Date", "Zone", "Status", "Parties", "People", "Reason")
    rows = [
        (
            result.date.isoformat(),
            result.zone_name,
            "AVAILABLE" if result.available else "closed",
            f"{result.party_remaining}/{result.total_parties}",
            f"{result.people_remaining}/{result.total_people}",
            result.reason,
        )
        for result in results
    ]
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))

    available_count = sum(1 for result in results if result.available)
    print(f"\n{available_count} available target(s) found.")

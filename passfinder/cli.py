from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from typing import Iterable

from .config import ConfigError, load_config
from .config_init import DEFAULT_END_DATE, DEFAULT_PERMIT_ID, DEFAULT_START_DATE, write_starter_config
from .known_zones import KNOWN_ZONES
from .mailjet import MailjetError, MailjetNotifier
from .permit_content import PermitContentClient, PermitContentError
from .permit_search import PermitSearchClient, PermitSearchError, PermitSearchResult
from .recreation import AvailabilityResult, RecreationClient, RecreationError, check_availability


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "zones":
            print_zones()
            return 0
        if args.command == "init-config":
            return run_init_config(args)
        if args.command == "search-permits":
            return run_search_permits(args)
        if args.command == "check":
            return run_check(args)
        if args.command == "watch":
            return run_watch(args)
    except (
        ConfigError,
        RecreationError,
        PermitContentError,
        PermitSearchError,
        MailjetError,
        KeyboardInterrupt,
    ) as exc:
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

    init_config = subparsers.add_parser("init-config", help="Create a starter local config file")
    init_config.add_argument("--config", default="passfinder.config.json", help="Path to write")
    init_config.add_argument("--permit-id", help="Recreation.gov permit ID")
    init_config.add_argument("--start-date", help="First target date, YYYY-MM-DD")
    init_config.add_argument("--end-date", help="Last target date, YYYY-MM-DD")
    init_config.add_argument("--group-size", type=int, help="Minimum people quota needed")
    init_config.add_argument("--poll-minutes", type=int, help="Watch polling interval")
    init_config.add_argument("--yes", action="store_true", help="Use defaults for missing prompts")
    init_config.add_argument("--force", action="store_true", help="Overwrite an existing config file")

    search_permits = subparsers.add_parser("search-permits", help="Search Recreation.gov permits")
    search_permits.add_argument("query", help="Park or permit search text")
    search_permits.add_argument("--limit", type=int, default=10, help="Maximum results to print")

    subparsers.add_parser("zones", help="Print known zone names and IDs")
    return parser


def run_search_permits(args: argparse.Namespace) -> int:
    if args.limit < 1:
        raise ConfigError("search-permits limit must be at least 1")

    results = PermitSearchClient().search(args.query, args.limit)
    print_permit_search_results(results)
    return 0


def run_init_config(args: argparse.Namespace) -> int:
    permit_id = _resolve_init_permit_id(args.permit_id, args.yes)
    start_date_text = _prompt_value(
        args.start_date,
        "Start date",
        DEFAULT_START_DATE.isoformat(),
        args.yes,
    )
    end_date_text = _prompt_value(
        args.end_date,
        "End date",
        DEFAULT_END_DATE.isoformat(),
        args.yes,
    )
    group_size = _prompt_int(args.group_size, "Group size", 1, args.yes)
    poll_minutes = _prompt_int(args.poll_minutes, "Poll minutes", 10, args.yes)

    try:
        start_date = date.fromisoformat(start_date_text)
        end_date = date.fromisoformat(end_date_text)
    except ValueError as exc:
        raise ConfigError("init-config dates must use YYYY-MM-DD format") from exc

    if end_date < start_date:
        raise ConfigError("init-config end date must be on or after start date")
    if group_size < 1:
        raise ConfigError("init-config group size must be at least 1")
    if poll_minutes < 1:
        raise ConfigError("init-config poll minutes must be at least 1")

    zones = PermitContentClient().fetch_zones(permit_id)

    try:
        path = write_starter_config(
            path=args.config,
            permit_id=permit_id,
            zones=zones,
            start_date=start_date,
            end_date=end_date,
            group_size=group_size,
            poll_minutes=poll_minutes,
            force=args.force,
        )
    except FileExistsError as exc:
        raise ConfigError(f"{exc}. Use --force to overwrite it.") from exc

    print(f"Wrote starter config to {path}")
    return 0


def _resolve_init_permit_id(value: str | None, use_default: bool) -> str:
    if value is not None:
        return value
    if use_default:
        return DEFAULT_PERMIT_ID

    query = _prompt_value(None, "Search park or permit name", "Grand Teton", False)
    results = PermitSearchClient().search(query, 10)
    if not results:
        return _prompt_value(None, "Permit ID", DEFAULT_PERMIT_ID, False)

    print_numbered_permit_results(results)
    choice = input("Choose permit number or enter permit ID [1]: ").strip()
    if not choice:
        return results[0].permit_id
    if choice.isdigit():
        index = int(choice)
        if 1 <= index <= len(results):
            return results[index - 1].permit_id
    return choice


def _prompt_value(value: str | None, label: str, default: str, use_default: bool) -> str:
    if value is not None:
        return value
    if use_default:
        return default
    response = input(f"{label} [{default}]: ").strip()
    return response or default


def _prompt_int(value: int | None, label: str, default: int, use_default: bool) -> int:
    if value is not None:
        return value
    if use_default:
        return default
    response = input(f"{label} [{default}]: ").strip()
    if not response:
        return default
    try:
        return int(response)
    except ValueError as exc:
        raise ConfigError(f"{label} must be an integer") from exc


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


def print_permit_search_results(results: list[PermitSearchResult]) -> None:
    if not results:
        print("No permit results found.")
        return

    headers = ("Permit ID", "Name", "Park/Area", "Location")
    rows = [
        (
            result.permit_id,
            result.name,
            result.parent_name,
            result.location,
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


def print_numbered_permit_results(results: list[PermitSearchResult]) -> None:
    headers = ("#", "Permit ID", "Name", "Park/Area", "Location")
    rows = [
        (
            str(index),
            result.permit_id,
            result.name,
            result.parent_name,
            result.location,
        )
        for index, result in enumerate(results, start=1)
    ]
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))


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

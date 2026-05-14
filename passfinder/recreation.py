from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Any

from .config import AppConfig, Target


BASE_URL = "https://www.recreation.gov/api/permititinerary"
PARTY_QUOTA = "ConstantQuotaUsageDaily"
PEOPLE_QUOTA = "QuotaUsageByMemberDaily"


class RecreationError(RuntimeError):
    """Raised when Recreation.gov data cannot be fetched or parsed."""


@dataclass(frozen=True)
class AvailabilityResult:
    date: date
    zone_name: str
    zone_id: str
    available: bool
    party_remaining: int
    people_remaining: int
    total_parties: int
    total_people: int
    season_type: str
    reason: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.date.isoformat(), self.zone_id)


class RecreationClient:
    def __init__(self, opener: Any | None = None) -> None:
        self._opener = opener or urllib.request.urlopen

    def fetch_month(
        self,
        permit_id: str,
        zone_id: str,
        year: int,
        month: int,
        commercial: bool = False,
    ) -> dict[str, Any]:
        query = urllib.parse.urlencode(
            {
                "month": month,
                "year": year,
                "commercial": str(commercial).lower(),
            }
        )
        url = f"{BASE_URL}/{permit_id}/division/{zone_id}/availability/month?{query}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "PassFinder/0.1 (+local availability checker)",
            },
        )

        try:
            with self._opener(request, timeout=30) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise RecreationError(f"Failed to fetch availability for zone {zone_id}: {exc}") from exc

        try:
            payload = json.loads(body).get("payload")
        except json.JSONDecodeError as exc:
            raise RecreationError("Recreation.gov returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise RecreationError("Recreation.gov response did not include a payload object")
        return payload


def check_availability(config: AppConfig, client: RecreationClient | None = None) -> list[AvailabilityResult]:
    client = client or RecreationClient()
    payloads: dict[tuple[str, int, int], dict[str, Any]] = {}
    results: list[AvailabilityResult] = []

    for target in config.targets:
        key = (target.zone_id, target.date.year, target.date.month)
        if key not in payloads:
            payloads[key] = client.fetch_month(
                permit_id=config.permit_id,
                zone_id=target.zone_id,
                year=target.date.year,
                month=target.date.month,
            )
        results.append(evaluate_target(target, payloads[key], config.group_size))

    return results


def evaluate_target(target: Target, payload: dict[str, Any], group_size: int) -> AvailabilityResult:
    date_key = target.date.isoformat()
    quota_maps = payload.get("quota_type_maps", {})
    party = quota_maps.get(PARTY_QUOTA, {}).get(date_key)
    people = quota_maps.get(PEOPLE_QUOTA, {}).get(date_key)

    if not isinstance(party, dict):
        return _result(target, False, 0, 0, 0, 0, "", "Missing party quota")
    if not isinstance(people, dict):
        return _result(target, False, 0, 0, 0, 0, "", "Missing people quota")

    party_remaining = _int_value(party.get("remaining"))
    people_remaining = _int_value(people.get("remaining"))
    total_parties = _int_value(party.get("total"))
    total_people = _int_value(people.get("total"))
    season_type = str(party.get("season_type") or people.get("season_type") or "")

    if party.get("is_hidden") or people.get("is_hidden"):
        reason = "Hidden by Recreation.gov"
        available = False
    elif party_remaining <= 0:
        reason = "No party quota remaining"
        available = False
    elif people_remaining < group_size:
        reason = f"Only {people_remaining} people quota remaining for group size {group_size}"
        available = False
    else:
        reason = "Available"
        available = True

    return _result(
        target,
        available,
        party_remaining,
        people_remaining,
        total_parties,
        total_people,
        season_type,
        reason,
    )


def _result(
    target: Target,
    available: bool,
    party_remaining: int,
    people_remaining: int,
    total_parties: int,
    total_people: int,
    season_type: str,
    reason: str,
) -> AvailabilityResult:
    return AvailabilityResult(
        date=target.date,
        zone_name=target.zone_name,
        zone_id=target.zone_id,
        available=available,
        party_remaining=party_remaining,
        people_remaining=people_remaining,
        total_parties=total_parties,
        total_people=total_people,
        season_type=season_type,
        reason=reason,
    )


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

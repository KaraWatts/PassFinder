from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


PERMIT_CONTENT_URL = "https://www.recreation.gov/api/permitcontent/{permit_id}"


class PermitContentError(RuntimeError):
    """Raised when permit metadata cannot be fetched or parsed."""


class PermitContentClient:
    def __init__(self, opener: Any | None = None) -> None:
        self._opener = opener or urllib.request.urlopen

    def fetch_zones(self, permit_id: str) -> dict[str, str]:
        request = urllib.request.Request(
            PERMIT_CONTENT_URL.format(permit_id=permit_id),
            headers={
                "Accept": "application/json",
                "User-Agent": "PassFinder/0.1 (+local availability checker)",
            },
        )

        try:
            with self._opener(request, timeout=30) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise PermitContentError(f"Failed to fetch permit metadata for {permit_id}: {exc}") from exc

        try:
            payload = json.loads(body).get("payload")
        except json.JSONDecodeError as exc:
            raise PermitContentError("Recreation.gov returned invalid permit metadata JSON") from exc

        if not isinstance(payload, dict):
            raise PermitContentError("Permit metadata response did not include a payload object")

        divisions = payload.get("divisions", [])
        if isinstance(divisions, dict):
            divisions = list(divisions.values())
        if not isinstance(divisions, list):
            raise PermitContentError("Permit metadata response did not include a divisions list or map")

        zones = {
            str(division["name"]).strip(): str(division["id"]).strip()
            for division in divisions
            if isinstance(division, dict)
            and division.get("type") == "Camp Area"
            and str(division.get("name", "")).strip()
            and str(division.get("id", "")).strip()
        }
        if not zones:
            raise PermitContentError(f"No camp-area zones found for permit {permit_id}")
        return dict(sorted(zones.items()))

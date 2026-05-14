from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


SEARCH_URL = "https://www.recreation.gov/api/search"


class PermitSearchError(RuntimeError):
    """Raised when Recreation.gov permit search cannot be fetched or parsed."""


@dataclass(frozen=True)
class PermitSearchResult:
    permit_id: str
    name: str
    location: str
    parent_name: str
    url: str


class PermitSearchClient:
    def __init__(self, opener: Any | None = None) -> None:
        self._opener = opener or urllib.request.urlopen

    def search(self, query: str, limit: int = 10) -> list[PermitSearchResult]:
        query = query.strip()
        if not query:
            raise PermitSearchError("Search query must not be blank")

        results = self._search_once(query, limit)
        if results:
            return results
        if "permit" not in query.lower():
            return self._search_once(f"{query} permits", limit)
        return []

    def _search_once(self, query: str, limit: int) -> list[PermitSearchResult]:
        params = urllib.parse.urlencode(
            {
                "q": query,
                "entity_type": "permit",
                "size": limit,
            }
        )
        request = urllib.request.Request(
            f"{SEARCH_URL}?{params}",
            headers={
                "Accept": "application/json",
                "User-Agent": "PassFinder/0.1 (+local availability checker)",
            },
        )

        try:
            with self._opener(request, timeout=30) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise PermitSearchError(f"Failed to search Recreation.gov permits: {exc}") from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise PermitSearchError("Recreation.gov returned invalid search JSON") from exc

        results = payload.get("results")
        if not isinstance(results, list):
            raise PermitSearchError("Recreation.gov search response did not include a results list")

        permits: list[PermitSearchResult] = []
        for result in results:
            if not isinstance(result, dict):
                continue
            entity_type = str(result.get("entity_type") or result.get("type") or "").lower()
            if entity_type != "permit":
                continue
            permit_id = str(result.get("entity_id") or "").strip()
            name = str(result.get("name") or "").strip()
            if not permit_id or not name:
                continue
            permits.append(
                PermitSearchResult(
                    permit_id=permit_id,
                    name=name,
                    location=str(result.get("location") or "").strip(),
                    parent_name=str(result.get("parent_name") or "").strip(),
                    url=f"https://www.recreation.gov/permits/{permit_id}",
                )
            )
        return permits[:limit]

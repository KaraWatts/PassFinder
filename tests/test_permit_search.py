from __future__ import annotations

import json
import unittest

from passfinder.permit_search import PermitSearchClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class PermitSearchTests(unittest.TestCase):
    def test_search_returns_permit_results_only(self):
        client = PermitSearchClient(
            opener=lambda request, timeout=30: FakeResponse(
                {
                    "results": [
                        {
                            "entity_id": "4675342",
                            "entity_type": "permit",
                            "name": "Grand Teton National Park Backcountry Permits",
                            "parent_name": "Grand Teton National Park",
                            "location": "Jackson, Wyoming",
                        },
                        {
                            "entity_id": "13525",
                            "entity_type": "recarea",
                            "name": "Grand Teton National Park",
                        },
                    ]
                }
            )
        )

        results = client.search("Grand Teton")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].permit_id, "4675342")
        self.assertEqual(results[0].url, "https://www.recreation.gov/permits/4675342")

    def test_search_retries_with_permits_suffix_for_park_name(self):
        calls = []

        def opener(request, timeout=30):
            calls.append(request.full_url)
            if len(calls) == 1:
                return FakeResponse({"results": []})
            return FakeResponse(
                {
                    "results": [
                        {
                            "entity_id": "4675342",
                            "entity_type": "permit",
                            "name": "Grand Teton National Park Backcountry Permits",
                        }
                    ]
                }
            )

        client = PermitSearchClient(opener=opener)

        results = client.search("Grand Teton")

        self.assertEqual(len(results), 1)
        self.assertIn("Grand+Teton", calls[0])
        self.assertIn("Grand+Teton+permits", calls[1])


if __name__ == "__main__":
    unittest.main()

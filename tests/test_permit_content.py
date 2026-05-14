from __future__ import annotations

import json
import unittest

from passfinder.permit_content import PermitContentClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class PermitContentTests(unittest.TestCase):
    def test_fetch_zones_extracts_camp_area_divisions_from_list(self):
        client = PermitContentClient(
            opener=lambda request, timeout=30: FakeResponse(
                {
                    "payload": {
                        "divisions": [
                            {"name": "Death Canyon Shelf", "id": "4675342030", "type": "Camp Area"},
                            {"name": "Jenny Lake Ranger Station", "id": "office", "type": "Issue Station"},
                        ]
                    }
                }
            )
        )

        zones = client.fetch_zones("4675342")

        self.assertEqual(zones, {"Death Canyon Shelf": "4675342030"})

    def test_fetch_zones_extracts_camp_area_divisions_from_map(self):
        client = PermitContentClient(
            opener=lambda request, timeout=30: FakeResponse(
                {
                    "payload": {
                        "divisions": {
                            "4675342030": {
                                "name": "Death Canyon Shelf",
                                "id": "4675342030",
                                "type": "Camp Area",
                            }
                        }
                    }
                }
            )
        )

        zones = client.fetch_zones("4675342")

        self.assertEqual(zones, {"Death Canyon Shelf": "4675342030"})


if __name__ == "__main__":
    unittest.main()

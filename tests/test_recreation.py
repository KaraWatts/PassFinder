from __future__ import annotations

import unittest
from datetime import date

from passfinder.config import AppConfig, MailjetConfig, Target
from passfinder.recreation import check_availability, evaluate_target


TARGET = Target(date=date(2026, 7, 26), zone_name="Death Canyon Shelf", zone_id="4675342030")


def payload(party_remaining=1, people_remaining=1, hidden=False):
    return {
        "quota_type_maps": {
            "ConstantQuotaUsageDaily": {
                "2026-07-26": {
                    "total": 2,
                    "remaining": party_remaining,
                    "is_hidden": hidden,
                    "season_type": "High",
                }
            },
            "QuotaUsageByMemberDaily": {
                "2026-07-26": {
                    "total": 12,
                    "remaining": people_remaining,
                    "is_hidden": hidden,
                    "season_type": "High",
                }
            },
        }
    }


class FakeClient:
    def __init__(self):
        self.calls = []

    def fetch_month(self, permit_id, zone_id, year, month, commercial=False):
        self.calls.append((permit_id, zone_id, year, month, commercial))
        return payload()


class RecreationTests(unittest.TestCase):
    def test_available_when_party_and_people_quota_are_sufficient(self):
        result = evaluate_target(TARGET, payload(party_remaining=1, people_remaining=4), group_size=4)

        self.assertTrue(result.available)
        self.assertEqual(result.reason, "Available")

    def test_not_available_when_party_quota_is_zero(self):
        result = evaluate_target(TARGET, payload(party_remaining=0, people_remaining=6), group_size=2)

        self.assertFalse(result.available)
        self.assertEqual(result.reason, "No party quota remaining")

    def test_not_available_when_people_quota_is_below_group_size(self):
        result = evaluate_target(TARGET, payload(party_remaining=1, people_remaining=1), group_size=2)

        self.assertFalse(result.available)
        self.assertIn("group size 2", result.reason)

    def test_not_available_when_hidden(self):
        result = evaluate_target(TARGET, payload(party_remaining=1, people_remaining=6, hidden=True), group_size=2)

        self.assertFalse(result.available)
        self.assertEqual(result.reason, "Hidden by Recreation.gov")

    def test_requests_are_grouped_by_zone_month(self):
        config = AppConfig(
            permit_id="4675342",
            group_size=1,
            poll_minutes=10,
            availability_link="https://example.com",
            mailjet=MailjetConfig(True, "from@example.com", "PassFinder", "to@example.com", "Watcher"),
            zones={"Death Canyon Shelf": "4675342030"},
            targets=(
                TARGET,
                Target(date=date(2026, 7, 27), zone_name="Death Canyon Shelf", zone_id="4675342030"),
            ),
        )
        client = FakeClient()

        check_availability(config, client)

        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0], ("4675342", "4675342030", 2026, 7, False))


if __name__ == "__main__":
    unittest.main()

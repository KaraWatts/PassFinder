from __future__ import annotations

import os
import unittest
from datetime import date
from unittest.mock import patch

from passfinder.config import AppConfig, ConfigError, MailjetConfig
from passfinder.mailjet import build_payload, MailjetNotifier
from passfinder.recreation import AvailabilityResult


def config():
    return AppConfig(
        permit_id="4675342",
        group_size=1,
        poll_minutes=10,
        availability_link="https://www.recreation.gov/example",
        mailjet=MailjetConfig(True, "from@example.com", "PassFinder", "to@example.com", "Watcher"),
        targets=(),
    )


def result():
    return AvailabilityResult(
        date=date(2026, 7, 26),
        zone_name="Death Canyon Shelf",
        zone_id="4675342030",
        available=True,
        party_remaining=1,
        people_remaining=4,
        total_parties=2,
        total_people=12,
        season_type="High",
        reason="Available",
    )


def unavailable_result():
    available = result()
    return AvailabilityResult(
        date=available.date,
        zone_name=available.zone_name,
        zone_id=available.zone_id,
        available=False,
        party_remaining=0,
        people_remaining=4,
        total_parties=2,
        total_people=12,
        season_type="High",
        reason="No party quota remaining",
    )


class MailjetTests(unittest.TestCase):
    def test_payload_includes_required_mailjet_fields(self):
        payload = build_payload(config(), [result()])
        message = payload["Messages"][0]

        self.assertEqual(message["From"]["Email"], "from@example.com")
        self.assertEqual(message["To"][0]["Email"], "to@example.com")
        self.assertIn("Subject", message)
        self.assertIn("TextPart", message)
        self.assertIn("HTMLPart", message)
        self.assertIn("Death Canyon Shelf", message["TextPart"])

    def test_missing_mailjet_env_vars_fails_before_send(self):
        notifier = MailjetNotifier(opener=lambda *args, **kwargs: self.fail("opener should not be called"))

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError):
                notifier.send(config(), [result()])

    def test_no_email_is_sent_when_no_passes_are_available(self):
        notifier = MailjetNotifier(opener=lambda *args, **kwargs: self.fail("opener should not be called"))

        with patch.dict(os.environ, {}, clear=True):
            sent = notifier.send(config(), [unavailable_result()])

        self.assertFalse(sent)


if __name__ == "__main__":
    unittest.main()

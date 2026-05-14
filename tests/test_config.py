from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from passfinder.config import load_config


class ConfigTests(unittest.TestCase):
    def test_mailjet_email_fields_can_come_from_environment(self):
        raw_config = {
            "permit_id": "4675342",
            "group_size": 1,
            "poll_minutes": 10,
            "mailjet": {
                "enabled": True,
                "from_email": "",
                "from_name": "",
                "to_email": "",
                "to_name": "",
            },
            "targets": [
                {
                    "date": "2026-07-26",
                    "zones": ["Death Canyon Shelf"],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "config.json"
            config_path.write_text(json.dumps(raw_config), encoding="utf-8")

            with patch.dict(
                os.environ,
                {
                    "MAILJET_FROM_EMAIL": "from@example.com",
                    "MAILJET_FROM_NAME": "PassFinder",
                    "MAILJET_TO_EMAIL": "to@example.com",
                    "MAILJET_TO_NAME": "Watcher",
                },
                clear=True,
            ):
                config = load_config(config_path)

        self.assertEqual(config.mailjet.from_email, "from@example.com")
        self.assertEqual(config.mailjet.from_name, "PassFinder")
        self.assertEqual(config.mailjet.to_email, "to@example.com")
        self.assertEqual(config.mailjet.to_name, "Watcher")


if __name__ == "__main__":
    unittest.main()

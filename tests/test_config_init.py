from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from passfinder.config_init import build_starter_config, write_starter_config


class ConfigInitTests(unittest.TestCase):
    def test_build_starter_config_uses_first_zone_for_each_date(self):
        config = build_starter_config(
            zones={"First Zone": "1", "Second Zone": "2"},
            start_date=date(2026, 8, 15),
            end_date=date(2026, 8, 16),
            group_size=2,
            poll_minutes=5,
        )

        self.assertEqual(config["group_size"], 2)
        self.assertEqual(config["poll_minutes"], 5)
        self.assertEqual([target["date"] for target in config["targets"]], ["2026-08-15", "2026-08-16"])
        self.assertEqual(config["targets"][0]["zones"], ["First Zone"])

    def test_write_starter_config_does_not_overwrite_by_default(self):
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "passfinder.config.json"
            config_path.write_text("already here", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                write_starter_config(config_path)

    def test_write_starter_config_can_force_overwrite(self):
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "passfinder.config.json"
            config_path.write_text("already here", encoding="utf-8")

            write_starter_config(config_path, force=True)
            config = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(config["permit_id"], "4675342")
        self.assertIn("targets", config)
        self.assertEqual(config["targets"][0]["date"], "2026-08-15")


if __name__ == "__main__":
    unittest.main()

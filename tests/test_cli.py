from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from passfinder.cli import main


class FakePermitContentClient:
    def fetch_zones(self, permit_id):
        return {"Fetched Zone": "zone-1"}


class CliTests(unittest.TestCase):
    def test_init_config_yes_uses_defaults_and_fetches_zones(self):
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "passfinder.config.json"

            with patch("passfinder.cli.PermitContentClient", return_value=FakePermitContentClient()):
                with patch("builtins.print"):
                    exit_code = main(["init-config", "--config", str(config_path), "--yes"])

            config = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(config["permit_id"], "4675342")
        self.assertEqual([target["date"] for target in config["targets"]], [
            "2026-08-15",
            "2026-08-16",
            "2026-08-17",
            "2026-08-18",
        ])
        self.assertEqual(config["targets"][0]["zones"], ["Fetched Zone"])

    def test_init_config_prompts_for_missing_values(self):
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "passfinder.config.json"
            answers = iter(["12345", "2026-09-01", "2026-09-02", "3", "15"])

            with patch("passfinder.cli.PermitContentClient", return_value=FakePermitContentClient()):
                with patch("builtins.input", side_effect=lambda prompt: next(answers)):
                    with patch("builtins.print"):
                        exit_code = main(["init-config", "--config", str(config_path)])

            config = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(config["permit_id"], "12345")
        self.assertEqual(config["group_size"], 3)
        self.assertEqual(config["poll_minutes"], 15)
        self.assertEqual([target["date"] for target in config["targets"]], ["2026-09-01", "2026-09-02"])


if __name__ == "__main__":
    unittest.main()

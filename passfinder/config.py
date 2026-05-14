from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


PERMIT_ID = "4675342"
AVAILABILITY_LINK = (
    "https://www.recreation.gov/permits/4675342/registration/"
    "detailed-availability?date=2026-07-26"
)

KNOWN_ZONES = {
    "Death Canyon Shelf": "4675342030",
    "Cascade North Fork": "4675342027",
    "Cascade South Fork": "4675342028",
    "Paintbrush Upper": "4675342041",
    "Paintbrush Lower": "4675342040",
}

DEFAULT_ZONE_NAMES = (
    "Death Canyon Shelf",
    "Cascade North Fork",
    "Cascade South Fork",
    "Paintbrush Upper",
)


class ConfigError(ValueError):
    """Raised when user configuration is missing or invalid."""


@dataclass(frozen=True)
class MailjetConfig:
    enabled: bool
    from_email: str
    from_name: str
    to_email: str
    to_name: str


@dataclass(frozen=True)
class Target:
    date: date
    zone_name: str
    zone_id: str


@dataclass(frozen=True)
class AppConfig:
    permit_id: str
    group_size: int
    poll_minutes: int
    availability_link: str
    mailjet: MailjetConfig
    targets: tuple[Target, ...]


def load_config(path: str | Path) -> AppConfig:
    load_env_files()
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    try:
        permit_id = str(raw.get("permit_id", PERMIT_ID))
        group_size = int(raw.get("group_size", 1))
        poll_minutes = int(raw.get("poll_minutes", 10))
    except (TypeError, ValueError) as exc:
        raise ConfigError("permit_id, group_size, and poll_minutes must be valid values") from exc

    if group_size < 1:
        raise ConfigError("group_size must be at least 1")
    if poll_minutes < 1:
        raise ConfigError("poll_minutes must be at least 1")

    mailjet = _load_mailjet(raw.get("mailjet", {}))
    targets = tuple(_load_targets(raw.get("targets", [])))
    if not targets:
        raise ConfigError("At least one target date/zone must be configured")

    return AppConfig(
        permit_id=permit_id,
        group_size=group_size,
        poll_minutes=poll_minutes,
        availability_link=str(raw.get("availability_link", AVAILABILITY_LINK)),
        mailjet=mailjet,
        targets=targets,
    )


def _load_mailjet(raw: dict[str, Any]) -> MailjetConfig:
    if not isinstance(raw, dict):
        raise ConfigError("mailjet config must be an object")

    return MailjetConfig(
        enabled=bool(raw.get("enabled", True)),
        from_email=_env_or_config("MAILJET_FROM_EMAIL", raw, "from_email", ""),
        from_name=_env_or_config("MAILJET_FROM_NAME", raw, "from_name", "PassFinder"),
        to_email=_env_or_config("MAILJET_TO_EMAIL", raw, "to_email", ""),
        to_name=_env_or_config("MAILJET_TO_NAME", raw, "to_name", ""),
    )


def _env_or_config(env_name: str, raw: dict[str, Any], key: str, default: str) -> str:
    return str(os.environ.get(env_name) or raw.get(key, default)).strip()


def load_env_files(paths: tuple[str, ...] = (".env", "mailjet.env")) -> None:
    for path in paths:
        env_path = Path(path)
        if env_path.exists():
            _load_env_file(env_path)


def _load_env_file(path: Path) -> None:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("export "):
                stripped = stripped[len("export ") :].strip()
            if "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _load_targets(raw_targets: list[dict[str, Any]]) -> list[Target]:
    if not isinstance(raw_targets, list):
        raise ConfigError("targets must be a list")

    targets: list[Target] = []
    for raw_target in raw_targets:
        if not isinstance(raw_target, dict):
            raise ConfigError("Each target must be an object")

        target_date = _parse_date(raw_target.get("date"))
        zones = raw_target.get("zones")
        if not isinstance(zones, list) or not zones:
            raise ConfigError(f"Target {target_date.isoformat()} must include one or more zones")

        for zone in zones:
            zone_name = str(zone).strip()
            zone_id = KNOWN_ZONES.get(zone_name)
            if not zone_id:
                known = ", ".join(sorted(KNOWN_ZONES))
                raise ConfigError(f"Unknown zone '{zone_name}'. Known zones: {known}")
            targets.append(Target(date=target_date, zone_name=zone_name, zone_id=zone_id))

    return targets


def _parse_date(value: Any) -> date:
    if not isinstance(value, str):
        raise ConfigError("Target date must be a YYYY-MM-DD string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ConfigError(f"Invalid target date: {value}") from exc

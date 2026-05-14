from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .known_zones import KNOWN_ZONES


DEFAULT_PERMIT_ID = "4675342"
DEFAULT_START_DATE = date(2026, 8, 15)
DEFAULT_END_DATE = date(2026, 8, 18)


def build_starter_config(
    permit_id: str = DEFAULT_PERMIT_ID,
    zones: dict[str, str] | None = None,
    start_date: date = DEFAULT_START_DATE,
    end_date: date = DEFAULT_END_DATE,
    group_size: int = 1,
        check_interval: int = 10,
) -> dict:
    zone_map = dict(zones or KNOWN_ZONES)
    default_zones = list(zone_map)[:1]

    return {
        "permit_id": permit_id,
        "group_size": group_size,
            "check_interval": check_interval,
        "availability_link": _availability_link(permit_id, start_date),
        "mailjet": {
            "enabled": True,
        },
        "zones": zone_map,
        "targets": [
            {
                "date": target_date.isoformat(),
                "zones": default_zones,
            }
            for target_date in _date_range(start_date, end_date)
        ],
    }


def write_starter_config(
    path: str | Path,
    permit_id: str = DEFAULT_PERMIT_ID,
    zones: dict[str, str] | None = None,
    start_date: date = DEFAULT_START_DATE,
    end_date: date = DEFAULT_END_DATE,
    group_size: int = 1,
        check_interval: int = 10,
    force: bool = False,
) -> Path:
    config_path = Path(path)
    if config_path.exists() and not force:
        raise FileExistsError(f"{config_path} already exists")

    config = build_starter_config(
        permit_id=permit_id,
        zones=zones,
        start_date=start_date,
        end_date=end_date,
        group_size=group_size,
            check_interval=check_interval,
    )
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return config_path


def _availability_link(permit_id: str, start_date: date) -> str:
    return (
        f"https://www.recreation.gov/permits/{permit_id}/registration/"
        f"detailed-availability?date={start_date.isoformat()}"
    )


def _date_range(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)

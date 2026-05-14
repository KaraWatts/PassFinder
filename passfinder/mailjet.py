from __future__ import annotations

import base64
import html
import json
import os
import urllib.error
import urllib.request
from typing import Any

from .config import AppConfig, ConfigError
from .recreation import AvailabilityResult


MAILJET_SEND_URL = "https://api.mailjet.com/v3.1/send"


class MailjetError(RuntimeError):
    """Raised when Mailjet cannot send a notification."""


class MailjetNotifier:
    def __init__(self, opener: Any | None = None) -> None:
        self._opener = opener or urllib.request.urlopen

    def send(self, config: AppConfig, results: list[AvailabilityResult]) -> bool:
        matches = [result for result in results if result.available]
        if not matches or not config.mailjet.enabled:
            return False

        api_key = os.environ.get("MAILJET_API_KEY")
        api_secret = os.environ.get("MAILJET_API_SECRET")
        if not api_key or not api_secret:
            raise ConfigError("MAILJET_API_KEY and MAILJET_API_SECRET must be set to send email")
        if not config.mailjet.from_email or not config.mailjet.to_email:
            raise ConfigError("mailjet.from_email and mailjet.to_email must be set in the config")

        body = build_payload(config, matches)
        credentials = base64.b64encode(f"{api_key}:{api_secret}".encode("utf-8")).decode("ascii")
        request = urllib.request.Request(
            MAILJET_SEND_URL,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "PassFinder/0.1 (+local availability checker)",
            },
        )

        try:
            with self._opener(request, timeout=30) as response:
                status = response.getcode()
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise MailjetError(f"Mailjet returned HTTP {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise MailjetError(f"Failed to send Mailjet notification: {exc}") from exc

        if status < 200 or status >= 300:
            raise MailjetError(f"Mailjet returned HTTP {status}: {response_body}")
        return True


def build_payload(config: AppConfig, matches: list[AvailabilityResult]) -> dict[str, Any]:
    subject = f"PassFinder: {len(matches)} camp zone availability match"
    if len(matches) != 1:
        subject += "es"

    text_lines = [
        "PassFinder found availability:",
        "",
        *[_format_text_line(result) for result in matches],
        "",
        f"Open Recreation.gov: {config.availability_link}",
    ]
    html_lines = "".join(f"<li>{html.escape(_format_text_line(result))}</li>" for result in matches)
    html_part = (
        "<p>PassFinder found availability:</p>"
        f"<ul>{html_lines}</ul>"
        f'<p><a href="{html.escape(config.availability_link)}">Open Recreation.gov</a></p>'
    )

    return {
        "Messages": [
            {
                "From": {
                    "Email": config.mailjet.from_email,
                    "Name": config.mailjet.from_name,
                },
                "To": [
                    {
                        "Email": config.mailjet.to_email,
                        "Name": config.mailjet.to_name,
                    }
                ],
                "Subject": subject,
                "TextPart": "\n".join(text_lines),
                "HTMLPart": html_part,
            }
        ]
    }


def _format_text_line(result: AvailabilityResult) -> str:
    return (
        f"{result.date.isoformat()} - {result.zone_name}: "
        f"{result.party_remaining}/{result.total_parties} parties, "
        f"{result.people_remaining}/{result.total_people} people remaining"
    )

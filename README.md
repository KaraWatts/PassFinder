# PassFinder

PassFinder is a local Python CLI that checks Recreation.gov availability for Grand Teton National Park backcountry camp areas and can send Mailjet email alerts when matching dates become available.

It checks July 26-31, 2026 by default for:

- Death Canyon Shelf
- Cascade North Fork
- Cascade South Fork
- Paintbrush Upper

The app only monitors availability and links you to Recreation.gov. It does not log in, reserve, or automate checkout.

## Setup

Use Python 3.10 or newer. No third-party packages are required.

Copy the example env file and fill in your local Mailjet values:

```sh
cp .env.example .env
```

Set:

```sh
MAILJET_API_KEY="your-mailjet-api-key"
MAILJET_API_SECRET="your-mailjet-api-secret"
MAILJET_FROM_EMAIL="sender@example.com"
MAILJET_FROM_NAME="PassFinder"
MAILJET_TO_EMAIL="recipient@example.com"
MAILJET_TO_NAME="Permit Watcher"
```

The sender address must be verified in Mailjet.

## Commands

Print known camp-area IDs:

```sh
python -m passfinder zones
```

Run one availability check:

```sh
python -m passfinder check --config passfinder.config.json
```

Run one check and send a Mailjet email only if available passes are found:

```sh
python -m passfinder check --config passfinder.config.json --notify
```

Watch continuously and email only when new available passes are found during the run:

```sh
python -m passfinder watch --config passfinder.config.json
```

## Tests

```sh
python -m unittest discover -s tests
```

## Availability Rules

A target is treated as available when Recreation.gov reports:

- `ConstantQuotaUsageDaily.remaining > 0`
- `QuotaUsageByMemberDaily.remaining >= group_size`
- neither quota row is hidden

Recreation.gov page:
https://www.recreation.gov/permits/4675342/registration/detailed-availability?date=2026-07-26

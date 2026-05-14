# PassFinder

PassFinder is a local Python CLI that checks Recreation.gov permit availability using search criteria you define in `passfinder.config.json`. It can send Mailjet email alerts when matching passes become available.

The app only monitors availability and links you to Recreation.gov. It does not log in, reserve, or automate checkout.

## Recreation.gov API Usage

PassFinder uses the same Recreation.gov JSON endpoints that power the public permit availability pages.

During setup, `init-config` calls the permit content endpoint once to find camp-area zones for the configured permit:

```text
https://www.recreation.gov/api/permitcontent/{permit_id}
```

Find permit pages and IDs by searching Recreation.gov:
https://www.recreation.gov/search

The permit ID is the number in a permit page URL, such as `4675342` in `https://www.recreation.gov/permits/4675342`.

It saves those zone names and IDs into `passfinder.config.json`. Regular `check` and `watch` runs do not refetch zone metadata.

During checks, PassFinder calls the permit itinerary availability endpoint for each zone/month it needs:

```text
https://www.recreation.gov/api/permititinerary/{permit_id}/division/{zone_id}/availability/month?month={month}&year={year}&commercial=false
```

These Recreation.gov frontend endpoints are not the same as the officially documented RIDB API, so they may change. The app keeps the API logic isolated in `passfinder/permit_content.py` and `passfinder/recreation.py`.

## Setup

Use Python 3.10 or newer. No third-party packages are required.

Copy the example env file and fill in your local Mailjet values:

```sh
cp .env.example .env
```

Generate a starter config interactively:

```sh
python -m passfinder init-config
```

`init-config` asks for the permit ID, trip dates, group size, and polling interval. It fetches the permit's camp-area zones once and saves them into `passfinder.config.json`. Regular `check` and `watch` runs use the saved config and do not refetch zone metadata.

`passfinder.config.json` is ignored by git so your dates, zones, group size, and other local search criteria do not get pushed to GitHub.

Mailjet addresses and API credentials belong in `.env`; the JSON config only needs `mailjet.enabled`.

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

The known zone list is maintained in `passfinder/known_zones.py`.

Create or overwrite a starter config:

```sh
python -m passfinder init-config --force
```

Use defaults without prompts:

```sh
python -m passfinder init-config --yes
```

Script setup with explicit values:

```sh
python -m passfinder init-config --permit-id 4675342 --start-date 2026-08-15 --end-date 2026-08-18
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
https://www.recreation.gov/permits/4675342/registration/detailed-availability?date=2026-08-15

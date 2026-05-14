# PassFinder

PassFinder is a local Python CLI that checks Recreation.gov permit availability using search criteria saved in `passfinder.config.json`. It can send Mailjet email alerts when matching passes become available.

PassFinder only monitors availability and links you to Recreation.gov. It does not log in, reserve permits, or automate checkout.

## Requirements

- Python 3.10 or newer
- Internet access for Recreation.gov availability checks
- A Mailjet account if you want email alerts
- A verified Mailjet sender address

No third-party Python packages are required.

## Setup

1. Create and activate a virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
```

2. Create your local environment file:

```sh
cp .env.example .env
```

3. Edit `.env` with your Mailjet values:

```sh
MAILJET_API_KEY=your-mailjet-api-key
MAILJET_API_SECRET=your-mailjet-api-secret
MAILJET_FROM_EMAIL=sender@example.com
MAILJET_FROM_NAME=PassFinder
MAILJET_TO_EMAIL=recipient@example.com
MAILJET_TO_NAME=Permit Watcher
```

4. Generate your local PassFinder config:

```sh
python -m passfinder init-config
```

`init-config` asks for a park or permit name, shows matching Recreation.gov permits, and lets you choose one. It then asks for trip dates, group size, and polling interval. It fetches the permit's camp-area zones once and saves them into `passfinder.config.json`.

5. Edit `passfinder.config.json` if needed.

The generated config includes a `zones` map and starter `targets`. Adjust the `targets` list to the dates and zones you want to watch.

Local files such as `.env` and `passfinder.config.json` are ignored by git so your secrets and trip details do not get pushed to GitHub.

## Usage

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

## Command Reference

Search Recreation.gov permits by park or permit name:

```sh
python -m passfinder search-permits "Grand Teton"
```

Create or overwrite a starter config:

```sh
python -m passfinder init-config --force
```

Use default setup values without prompts:

```sh
python -m passfinder init-config --yes
```

Script setup with explicit values:

```sh
python -m passfinder init-config --permit-id 4675342 --start-date 2026-08-15 --end-date 2026-08-18
```

Print bundled fallback camp-area IDs:

```sh
python -m passfinder zones
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

If People has quota remaining but Parties is `0`, PassFinder treats the target as unavailable.

## Recreation.gov API Notes

PassFinder uses the same Recreation.gov JSON endpoints that power the public permit availability pages.

During setup, `init-config` calls the permit content endpoint once to find camp-area zones for the selected permit:

```text
https://www.recreation.gov/api/permitcontent/{permit_id}
```

It saves those zone names and IDs into `passfinder.config.json`. Regular `check` and `watch` runs use the saved config and do not refetch zone metadata.

During checks, PassFinder calls the permit itinerary availability endpoint for each zone/month it needs:

```text
https://www.recreation.gov/api/permititinerary/{permit_id}/division/{zone_id}/availability/month?month={month}&year={year}&commercial=false
```

These Recreation.gov frontend endpoints are not the same as the officially documented RIDB API, so they may change. The API-specific code is isolated in `passfinder/permit_search.py`, `passfinder/permit_content.py`, and `passfinder/recreation.py`.

You can also search manually on Recreation.gov:
https://www.recreation.gov/search

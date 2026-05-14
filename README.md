# PassFinder

PassFinder watches Recreation.gov permit availability for the exact dates, zones, and group size you care about, then alerts you when a matching opening appears.

It is a local Python CLI tool built for high-demand permits where the official release window is not the only chance to get outside. Save your trip criteria in `passfinder.config.json`, run a one-time check or continuous watcher, and optionally receive email alerts when cancellations create a new opportunity.

PassFinder only monitors availability and links you to Recreation.gov. It does not log in, reserve permits, or automate checkout.

## Background

PassFinder started with a real trip problem: my best friend and I were planning a backpacking route through Grand Teton National Park, but the advance backcountry permits were gone before we could reserve the itinerary we wanted.

That left us with the usual backup plan: keep checking Recreation.gov, hope someone cancels, or gamble on walk-up permits after we were already committed to the trip. None of those options were especially reassuring when the route depended on specific camp zones lining up across multiple nights.

So I built PassFinder to turn that anxious refresh loop into a focused watchlist. Instead of manually checking every date and camp area, PassFinder monitors the targets that would actually make the trip work and sends an alert when Recreation.gov reports enough remaining quota. It keeps the final booking step in your hands, but helps you notice the narrow window when a canceled permit becomes available.

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

## Example Config

`init-config` writes the full zone map for the selected permit. After that, the main fields you usually edit are `group_size`, `check_interval`, `availability_link`, and `targets`.

```json
{
  "permit_id": "4675342",
  "group_size": 2,
  "check_interval": 10,
  "availability_link": "https://www.recreation.gov/permits/4675342/registration/detailed-availability?date=2026-08-15",
  "mailjet": {
    "enabled": true
  },
  "zones": {
    "Cascade North Fork": "4675342027",
    "Death Canyon Shelf": "4675342030",
    "Paintbrush Upper": "4675342041"
  },
  "targets": [
    {
      "date": "2026-08-15",
      "zones": ["Cascade North Fork"]
    },
    {
      "date": "2026-08-16",
      "zones": ["Death Canyon Shelf", "Paintbrush Upper"]
    }
  ]
}
```

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

## Example Output

The `watch` command prints one row for each configured date and zone, then sends a Mailjet notification when a new match appears during the run.

![PassFinder watch output showing one available Granite Lower permit target](docs/images/passfinder-watch-output.svg)

```text
Watching 3 targets every 10 minutes. Press Ctrl+C to stop.
Date        Zone             Status     Parties  People  Reason
----------  ---------------  ---------  -------  ------  ------------------------
2026-07-27  Granite Lower    AVAILABLE  1/1      6/6     Available
2026-07-28  #1 Wilcox Point  closed     0/0      0/0     No party quota remaining
2026-07-29  #1 Wilcox Point  closed     0/0      0/0     No party quota remaining

1 available target(s) found.
Sent Mailjet notification for 1 new match(es).
```

## Example Email Alert

When `mailjet.enabled` is `true`, `watch` sends an email only for newly discovered matches during that run.

![PassFinder email alert showing a Granite Lower availability match](docs/images/passfinder-email-alert.svg)

```text
Subject: PassFinder: 1 camp zone availability match

PassFinder found availability:

2026-07-27 - Granite Lower: 1/1 parties, 6/6 people remaining

Open Recreation.gov: https://www.recreation.gov/permits/4675342/registration/detailed-availability?date=2026-07-27
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

## Ethics and Boundaries

PassFinder is meant to make cancellation checking less tedious, not to jump the line or automate the reservation process.

- It does not log in to Recreation.gov.
- It does not reserve, hold, or purchase permits.
- It does not automate checkout or bypass user decisions.
- It only reads public availability data and points you back to Recreation.gov to complete any booking yourself.
- Use a reasonable `check_interval` so your watcher is helpful without being noisy or abusive.

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

# Contributing

We welcome contributions! Please see our [contributing instructions](CONTRIBUTING.md) for guidelines.

If you have a feature request or find a bug, please [submit an issue](https://github.com/yourusername/PassFinder/issues) on GitHub.

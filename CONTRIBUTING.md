# Contributing to PassFinder

Thank you for your interest in contributing! Here’s how you can help:

## Getting Started
1. **Fork the repository** and clone your fork locally.
2. **No dependencies to install**: This project does not require any external packages by default.
   - Ensure you have Python 3.10+ installed.
   - (Optional) Create a virtual environment:
     ```sh
     python3 -m venv .venv
     source .venv/bin/activate
     ```
3. **Run tests** to verify your environment. See [Testing](#testing) for the command.

- Follow [PEP8 style guidelines](https://peps.python.org/pep-0008/).
- Write clear commit messages.
- Add or update tests for your changes.
- Run all tests before submitting a pull request.

## Testing

Run the full test suite before opening a pull request:

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

## Submitting a Pull Request
1. Push your branch to your fork.
2. Open a pull request against the `main` branch.
3. Describe your changes and reference any related issues.

## Code of Conduct
Be respectful and constructive. See the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for details.

## Need Help?
Open an issue or start a discussion!

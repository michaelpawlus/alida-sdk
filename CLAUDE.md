# Alida SDK

Python SDK and CLI for the Alida CXM platform API. Extracts survey data (surveys, questions, responses) in structured formats.

## CLI Commands

```bash
# List all surveys
alida-sdk surveys list [--json]

# Get survey details
alida-sdk surveys get SURVEY_ID [--json]

# Export survey responses (uses async batch workflow)
alida-sdk surveys responses SURVEY_ID [--json] [--csv] [--output FILE]
```

All commands support `--json` for machine-readable output to stdout. Human-readable output goes to stderr.

Exit codes: 0 = success, 1 = error, 2 = not found.

## Environment Variables

- `ALIDA_API_KEY` (required) — API key from Alida Platform > Product Settings > API
- `ALIDA_BASE_URL` (required) — e.g., `https://api.na1.alida.com/v2/applications/yourCommunity`
- `ALIDA_USERNAME` (optional) — Username for OAuth token flow
- `ALIDA_PASSWORD` (optional) — Password for OAuth token flow

When `ALIDA_USERNAME`/`ALIDA_PASSWORD` are set, the SDK uses the full OAuth bearer token flow. Otherwise, it uses the API key directly.

## Architecture

```
src/alida_sdk/
  exceptions.py  — Custom exception hierarchy (AlidaError base)
  output.py      — JSON stdout / error output helpers
  models.py      — Dataclasses: Survey, SurveyResponse, BatchExportStatus
  auth.py        — TokenManager: env-var config, token fetch/cache/refresh
  client.py      — AlidaClient: httpx wrapper, retry (429/5xx), pagination, batch polling
  surveys.py     — SurveyResource: list, get, get_responses (3-step batch export)
  cli.py         — Typer CLI with surveys sub-command group
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Alida API Notes

- Surveys are called "activities" in the API
- Response export uses an async batch workflow: POST to start -> poll status -> download from URL
- Pagination is offset-based with `limit` and `offset` query params

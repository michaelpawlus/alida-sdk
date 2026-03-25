# Alida SDK

Python SDK and CLI for the Alida CXM platform API. Extracts survey data (surveys, questions, responses) in structured formats.

## CLI Commands

```bash
# List all surveys
alida-sdk surveys list [--json] [--csv] [--output FILE]

# Get survey details
alida-sdk surveys get SURVEY_ID [--json]

# Export survey responses (uses async batch workflow)
alida-sdk surveys responses SURVEY_ID [--json] [--csv] [--output FILE] [--dataset-id DATASET_ID]

# List all datasets (needed to get dataset IDs for questions)
alida-sdk datasets list [--json] [--csv] [--output FILE]

# List all questions for a dataset
alida-sdk questions list DATASET_ID [--json] [--csv] [--output FILE]

# Get question details with answer options
alida-sdk questions get DATASET_ID QUESTION_ID [--json]
```

All commands support `--json` for machine-readable output to stdout. List commands also support `--csv` and `--output FILE`. Human-readable output goes to stderr.

The `--dataset-id` flag on `surveys responses` fetches question metadata to produce human-readable column headers (question text instead of concept names) and resolves choice IDs to text labels.

Exit codes: 0 = success, 1 = error, 2 = not found.

## Environment Variables

- `ALIDA_API_KEY` (required) — API key from Alida Platform > Product Settings > API
- `ALIDA_BASE_URL` (required, or `ALIDA_REGION`) — e.g., `https://api.na1.alida.com`
- `ALIDA_REGION` (alternative to `ALIDA_BASE_URL`) — e.g., `na1`, `eu1` — constructs base URL automatically
- `ALIDA_COMMUNITY_KEY` (required) — community/panel key, e.g., `panel_thebuckeyeroom`
- `ALIDA_CLIENT_ID` (optional) — OAuth2 client ID for client_credentials flow
- `ALIDA_CLIENT_SECRET` (optional) — OAuth2 client secret for client_credentials flow

When `ALIDA_CLIENT_ID`/`ALIDA_CLIENT_SECRET` are set, the SDK uses OAuth2 client_credentials to obtain a bearer token. Otherwise, it uses the API key directly.

## Architecture

```
src/alida_sdk/
  exceptions.py   — Custom exception hierarchy (AlidaError base)
  output.py       — JSON/CSV stdout helpers, output destination context manager
  models.py       — Dataclasses: Survey, SurveyResponse, Question, AnswerOption, BatchExportStatus
  auth.py         — TokenManager: env-var config, OAuth2 client_credentials, token cache/refresh
  client.py       — AlidaClient: httpx wrapper, retry (429/5xx), link-based pagination, batch polling
  surveys.py      — SurveyResource: list, get, get_responses (3-step batch export)
  questions.py    — QuestionResource: list, get (via datasets/concepts API)
  transforms.py   — Response flattening: column mapping, HTML stripping, choice resolution
  cli.py          — Typer CLI with surveys, datasets, and questions sub-command groups
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Alida API Notes

- Surveys are called "activities" in the API
- Response export uses an async batch workflow: POST to start -> poll status -> download from URL
- Pagination is link-based: follow `rel=next` links in the `links` array
- Auth uses OAuth2 client_credentials grant: POST to `/oauth2/token` with HTTP Basic (client_id:client_secret) + x-api-key header
- API paths are under `/v1/applications/{community_key}/`
- **Activities and datasets are separate ID spaces**: activities come from `/activities`, datasets from `/datasets`. They do not share IDs.
- **Questions** live under datasets as "concepts": `GET datasets/{id}/concepts` returns all concepts; filter by `"question"` tag to get questions. Each concept has `extraData` with `text`, `questionType`, and `choices` (answer options).
- System questions (DisplayType, RespondentLocale) are tagged `systemquestion` and excluded by default.

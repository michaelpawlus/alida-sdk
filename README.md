# Alida SDK

Python SDK and CLI for the [Alida CXM](https://www.alida.com/) platform API. Extracts survey data — surveys, questions, and responses — in structured formats.

Requires Python 3.11+.

## Installation

```bash
pip install -e .
```

This installs the `alida-sdk` CLI and the `alida_sdk` Python package.

## Configuration

Set the following environment variables (e.g. in `~/.bashrc`):

| Variable | Required | Description |
|---|---|---|
| `ALIDA_API_KEY` | Yes | API key from Alida Platform > Product Settings > API |
| `ALIDA_BASE_URL` | Yes (or `ALIDA_REGION`) | Root API URL, e.g. `https://api.na1.alida.com` |
| `ALIDA_REGION` | Alternative to `ALIDA_BASE_URL` | Region code (`na1`, `eu1`, etc.) — base URL is derived automatically |
| `ALIDA_COMMUNITY_KEY` | Yes | Community/panel key, e.g. `panel_thebuckeyeroom` |
| `ALIDA_CLIENT_ID` | No | OAuth2 client ID for client_credentials flow |
| `ALIDA_CLIENT_SECRET` | No | OAuth2 client secret for client_credentials flow |

### Authentication modes

- **OAuth2 (recommended):** When `ALIDA_CLIENT_ID` and `ALIDA_CLIENT_SECRET` are set, the SDK obtains a bearer token via the OAuth2 client_credentials grant. Tokens are cached and refreshed automatically.
- **Simple API-key:** When no client credentials are set, the SDK sends `ALIDA_API_KEY` directly in the `x-api-key` header.

## CLI Usage

Every command supports `--json` for machine-readable JSON output to stdout. List commands also support `--csv` and `--output FILE`. Human-readable output (Rich tables) goes to stderr.

Exit codes: `0` success, `1` error, `2` not found.

### Surveys

```bash
# List all surveys
alida-sdk surveys list
alida-sdk surveys list --json
alida-sdk surveys list --csv
alida-sdk surveys list --csv --output surveys.csv

# Get survey details
alida-sdk surveys get SURVEY_ID
alida-sdk surveys get SURVEY_ID --json
```

### Response export

```bash
# Export with raw concept names as column headers
alida-sdk surveys responses SURVEY_ID --csv
alida-sdk surveys responses SURVEY_ID --json

# Export with human-readable question text as column headers
# (requires the dataset ID — get it from `datasets list`)
alida-sdk surveys responses SURVEY_ID --csv --dataset-id DATASET_ID
alida-sdk surveys responses SURVEY_ID --csv --dataset-id DATASET_ID --output responses.csv

# JSON with enriched column names
alida-sdk surveys responses SURVEY_ID --json --dataset-id DATASET_ID
```

When `--dataset-id` is provided, the SDK fetches question metadata from the dataset's concepts API and:
- Replaces raw concept names (e.g. `Q1`, `Q2`) with the actual question text
- Resolves choice IDs to their text labels for single/multiple choice questions
- Strips HTML tags from question text

Response export uses Alida's async batch workflow (POST to initiate, poll for completion, download results).

### Datasets

Activities (surveys) and datasets are separate ID spaces in the Alida API. Use `datasets list` to find the dataset ID that corresponds to your survey.

```bash
alida-sdk datasets list
alida-sdk datasets list --json
alida-sdk datasets list --csv
```

### Questions

Questions are accessed via datasets (not surveys). Each question has a type, text, and optional answer choices.

```bash
# List all questions for a dataset
alida-sdk questions list DATASET_ID
alida-sdk questions list DATASET_ID --json
alida-sdk questions list DATASET_ID --csv

# Get question details with answer options
alida-sdk questions get DATASET_ID QUESTION_ID
alida-sdk questions get DATASET_ID QUESTION_ID --json
```

## Python SDK Usage

```python
from alida_sdk.client import AlidaClient
from alida_sdk.surveys import SurveyResource
from alida_sdk.questions import QuestionResource
from alida_sdk.transforms import transform_responses

with AlidaClient() as client:
    surveys = SurveyResource(client)
    questions_resource = QuestionResource(client)

    # List all surveys
    for s in surveys.list_surveys():
        print(s.id, s.name, s.status)

    # Export responses with human-readable headers
    responses = surveys.get_responses("some-survey-id")
    questions = questions_resource.list_questions("some-dataset-id")
    headers, rows = transform_responses(responses, questions)
    for row in rows:
        print(row)
```

The client reads configuration from environment variables by default. To configure programmatically:

```python
from alida_sdk.auth import TokenManager
from alida_sdk.client import AlidaClient

tm = TokenManager(
    api_key="your-api-key",
    base_url="https://api.na1.alida.com",
    client_id="your-client-id",
    client_secret="your-client-secret",
)

client = AlidaClient(
    base_url="https://api.na1.alida.com",
    community_key="panel_yourpanel",
    token_manager=tm,
)
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Architecture

```
src/alida_sdk/
  exceptions.py   — Custom exception hierarchy (AlidaError base)
  output.py       — JSON/CSV stdout helpers, output destination context manager
  models.py       — Dataclasses: Survey, SurveyResponse, Question, AnswerOption, BatchExportStatus
  auth.py         — TokenManager: OAuth2 client_credentials, token cache/refresh
  client.py       — AlidaClient: httpx wrapper, retry (429/5xx), link-based pagination, batch polling
  surveys.py      — SurveyResource: list, get, get_responses (3-step batch export)
  questions.py    — QuestionResource: list, get (via datasets/concepts API)
  transforms.py   — Response flattening: column mapping, HTML stripping, choice resolution
  cli.py          — Typer CLI with surveys, datasets, and questions sub-command groups
```

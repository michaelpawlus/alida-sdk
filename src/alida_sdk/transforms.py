"""Response transform utilities for flattening survey data into tabular rows."""

from __future__ import annotations

import html
import re

from alida_sdk.models import Question, SurveyResponse

_META_COLUMNS = ["id", "survey_id", "submitted_at"]


def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities from question text."""
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", text)
    return html.unescape(cleaned).strip()


def build_column_map(questions: list[Question]) -> dict[str, str]:
    """Map concept names (response data keys) to human-readable question text.

    If two questions produce identical cleaned text, disambiguate by
    appending the concept name in parentheses.
    """
    raw_map: dict[str, str] = {}
    for q in questions:
        raw_map[q.name] = strip_html(q.text)

    # Detect duplicate display texts and disambiguate
    text_counts: dict[str, int] = {}
    for text in raw_map.values():
        text_counts[text] = text_counts.get(text, 0) + 1

    result: dict[str, str] = {}
    for name, text in raw_map.items():
        if text_counts.get(text, 0) > 1:
            result[name] = f"{text} ({name})"
        else:
            result[name] = text
    return result


def build_choice_map(
    questions: list[Question],
) -> dict[str, dict[str, str]]:
    """Map concept names to {choice_id: choice_text} for choice questions."""
    result: dict[str, dict[str, str]] = {}
    for q in questions:
        if q.answer_options:
            result[q.name] = {opt.id: opt.text for opt in q.answer_options}
    return result


def transform_responses(
    responses: list[SurveyResponse],
    questions: list[Question] | None = None,
) -> tuple[list[str], list[dict[str, str]]]:
    """Flatten responses into (headers, rows) for tabular output.

    Without *questions*: headers use raw concept names (current behaviour).
    With *questions*: headers use human-readable question text, and choice
    values are resolved to text labels when possible.
    """
    # Collect all data keys across responses
    data_keys: set[str] = set()
    for r in responses:
        data_keys.update(r.data.keys())
    sorted_keys = sorted(data_keys)

    column_map: dict[str, str] = {}
    choice_map: dict[str, dict[str, str]] = {}
    if questions:
        column_map = build_column_map(questions)
        choice_map = build_choice_map(questions)

    # Build headers: meta columns + data columns (renamed if questions provided)
    headers = list(_META_COLUMNS)
    key_to_header: dict[str, str] = {}
    for key in sorted_keys:
        header = column_map.get(key, key)
        key_to_header[key] = header
        headers.append(header)

    # Build rows
    rows: list[dict[str, str]] = []
    for r in responses:
        row: dict[str, str] = {
            "id": r.id,
            "survey_id": r.survey_id,
            "submitted_at": r.submitted_at or "",
        }
        for key in sorted_keys:
            value = r.data.get(key, "")
            # Resolve choice IDs to text if mapping exists
            if key in choice_map and str(value) in choice_map[key]:
                value = choice_map[key][str(value)]
            row[key_to_header[key]] = str(value) if value is not None else ""
        rows.append(row)

    return headers, rows

"""Tests for the transforms module."""

from __future__ import annotations

from alida_sdk.models import AnswerOption, Question, SurveyResponse
from alida_sdk.transforms import (
    build_choice_map,
    build_column_map,
    strip_html,
    transform_responses,
)


# --- strip_html ---


class TestStripHtml:
    def test_strips_paragraph_tags(self):
        assert strip_html("<p>How satisfied?</p>") == "How satisfied?"

    def test_strips_br_tags(self):
        assert strip_html("Line one<br>Line two") == "Line oneLine two"
        assert strip_html("Line one<br/>Line two") == "Line oneLine two"

    def test_decodes_html_entities(self):
        assert strip_html("salt &amp; pepper") == "salt & pepper"
        assert strip_html("&lt;not a tag&gt;") == "<not a tag>"

    def test_plain_text_passthrough(self):
        assert strip_html("Just plain text") == "Just plain text"

    def test_empty_and_none(self):
        assert strip_html("") == ""
        assert strip_html(None) == ""  # type: ignore[arg-type]


# --- helpers to build test data ---


def _q(name: str, text: str, qtype: str = "OpenEnd", options: list[AnswerOption] | None = None) -> Question:
    return Question(
        id=f"id-{name}",
        survey_id="ds-001",
        name=name,
        text=text,
        type=qtype,
        answer_options=options or [],
        raw={"name": name},
    )


def _opt(oid: str, text: str) -> AnswerOption:
    return AnswerOption(id=oid, text=text, raw={})


def _resp(rid: str, data: dict, submitted_at: str = "2025-01-01T00:00:00Z") -> SurveyResponse:
    return SurveyResponse(
        id=rid,
        survey_id="survey-001",
        data=data,
        submitted_at=submitted_at,
        raw={},
    )


# --- build_column_map ---


class TestBuildColumnMap:
    def test_maps_names_to_text(self):
        questions = [
            _q("Q1", "<p>How satisfied?</p>"),
            _q("Q2", "<p>Any comments?</p>"),
        ]
        result = build_column_map(questions)
        assert result == {"Q1": "How satisfied?", "Q2": "Any comments?"}

    def test_disambiguates_duplicate_text(self):
        questions = [
            _q("Q1", "<p>Please rate:</p>"),
            _q("Q2", "<p>Please rate:</p>"),
        ]
        result = build_column_map(questions)
        assert result == {"Q1": "Please rate: (Q1)", "Q2": "Please rate: (Q2)"}

    def test_empty_list(self):
        assert build_column_map([]) == {}


# --- build_choice_map ---


class TestBuildChoiceMap:
    def test_maps_choice_questions(self):
        questions = [
            _q("Q1", "Permission?", "SingleChoice", [_opt("c1", "Yes"), _opt("c2", "No")]),
        ]
        result = build_choice_map(questions)
        assert result == {"Q1": {"c1": "Yes", "c2": "No"}}

    def test_skips_open_end(self):
        questions = [_q("Q1", "Tell us more", "OpenEnd")]
        assert build_choice_map(questions) == {}

    def test_empty_list(self):
        assert build_choice_map([]) == {}


# --- transform_responses ---


class TestTransformResponses:
    def test_without_questions_uses_raw_keys(self):
        responses = [
            _resp("r1", {"q1": "Good", "q2": 5}),
            _resp("r2", {"q1": "Bad", "q2": 1}),
        ]
        headers, rows = transform_responses(responses)
        assert headers == ["id", "survey_id", "submitted_at", "q1", "q2"]
        assert rows[0]["q1"] == "Good"
        assert rows[1]["q2"] == "1"

    def test_with_questions_renames_headers(self):
        questions = [
            _q("q1", "<p>How was it?</p>"),
            _q("q2", "<p>Rate 1-5</p>"),
        ]
        responses = [_resp("r1", {"q1": "Great", "q2": 5})]
        headers, rows = transform_responses(responses, questions)
        assert "How was it?" in headers
        assert "Rate 1-5" in headers
        assert rows[0]["How was it?"] == "Great"
        assert rows[0]["Rate 1-5"] == "5"

    def test_resolves_choice_ids(self):
        questions = [
            _q("q1", "Permission?", "SingleChoice", [_opt("c1", "Yes"), _opt("c2", "No")]),
        ]
        responses = [_resp("r1", {"q1": "c1"})]
        headers, rows = transform_responses(responses, questions)
        assert rows[0]["Permission?"] == "Yes"

    def test_preserves_unmatched_keys(self):
        questions = [_q("q1", "Known question")]
        responses = [_resp("r1", {"q1": "Answer", "extra_field": "value"})]
        headers, rows = transform_responses(responses, questions)
        assert "extra_field" in headers
        assert rows[0]["extra_field"] == "value"

    def test_empty_responses(self):
        headers, rows = transform_responses([])
        assert headers == ["id", "survey_id", "submitted_at"]
        assert rows == []

    def test_meta_columns_always_first(self):
        responses = [_resp("r1", {"z_field": "a", "a_field": "b"})]
        headers, _ = transform_responses(responses)
        assert headers[:3] == ["id", "survey_id", "submitted_at"]

    def test_choice_id_not_in_map_left_as_is(self):
        questions = [
            _q("q1", "Pick one", "SingleChoice", [_opt("c1", "Yes"), _opt("c2", "No")]),
        ]
        responses = [_resp("r1", {"q1": "unknown_value"})]
        _, rows = transform_responses(responses, questions)
        assert rows[0]["Pick one"] == "unknown_value"

"""Tests for the CLI module."""

from __future__ import annotations

import csv
import io
import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from alida_sdk.cli import app
from alida_sdk.exceptions import AlidaError, NotFoundError
from alida_sdk.models import AnswerOption, Question, Survey, SurveyResponse

runner = CliRunner()


def _make_surveys() -> list[Survey]:
    return [
        Survey(
            id="s1",
            name="Survey One",
            status="active",
            created_at="2025-01-01",
            type="survey",
            raw={},
        ),
        Survey(
            id="s2",
            name="Survey Two",
            status="draft",
            created_at="2025-02-01",
            type="poll",
            raw={},
        ),
    ]


class TestSurveysList:
    @patch("alida_sdk.cli.AlidaClient")
    @patch("alida_sdk.cli.SurveyResource")
    def test_json_output(self, mock_resource_cls: MagicMock, mock_client_cls: MagicMock):
        mock_resource = MagicMock()
        mock_resource.list_surveys.return_value = _make_surveys()
        mock_resource_cls.return_value = mock_resource
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["surveys", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        assert data[0]["id"] == "s1"

    @patch("alida_sdk.cli.AlidaClient")
    @patch("alida_sdk.cli.SurveyResource")
    def test_table_output(self, mock_resource_cls: MagicMock, mock_client_cls: MagicMock):
        mock_resource = MagicMock()
        mock_resource.list_surveys.return_value = _make_surveys()
        mock_resource_cls.return_value = mock_resource
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["surveys", "list"])
        assert result.exit_code == 0

    @patch("alida_sdk.cli.AlidaClient")
    @patch("alida_sdk.cli.SurveyResource")
    def test_csv_output(self, mock_resource_cls: MagicMock, mock_client_cls: MagicMock):
        mock_resource = MagicMock()
        mock_resource.list_surveys.return_value = _make_surveys()
        mock_resource_cls.return_value = mock_resource
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["surveys", "list", "--csv"])
        assert result.exit_code == 0
        reader = csv.DictReader(io.StringIO(result.output))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["id"] == "s1"
        assert rows[0]["name"] == "Survey One"
        assert "status" in reader.fieldnames


class TestSurveysGet:
    @patch("alida_sdk.cli.AlidaClient")
    @patch("alida_sdk.cli.SurveyResource")
    def test_not_found_exits_2(self, mock_resource_cls: MagicMock, mock_client_cls: MagicMock):
        mock_resource = MagicMock()
        mock_resource.get_survey.side_effect = NotFoundError("not found")
        mock_resource_cls.return_value = mock_resource
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["surveys", "get", "bad-id", "--json"])
        assert result.exit_code == 2
        data = json.loads(result.output)
        assert "error" in data

    @patch("alida_sdk.cli.AlidaClient")
    @patch("alida_sdk.cli.SurveyResource")
    def test_error_exits_1(self, mock_resource_cls: MagicMock, mock_client_cls: MagicMock):
        mock_resource = MagicMock()
        mock_resource.get_survey.side_effect = AlidaError("server broke")
        mock_resource_cls.return_value = mock_resource
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["surveys", "get", "s1", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"] == "server broke"


def _make_questions() -> list[Question]:
    return [
        Question(
            id="q1",
            survey_id="s1",
            name="Q1",
            text="How satisfied are you?",
            type="single_choice",
            answer_options=[
                AnswerOption(id="opt-1", text="Very satisfied", position=1, raw={}),
                AnswerOption(id="opt-2", text="Satisfied", position=2, raw={}),
            ],
            raw={"name": "Q1"},
        ),
        Question(
            id="q2",
            survey_id="s1",
            name="Q2",
            text="Any comments?",
            type="open_text",
            answer_options=[],
            raw={"name": "Q2"},
        ),
    ]


def _make_responses() -> list[SurveyResponse]:
    return [
        SurveyResponse(
            id="r1",
            survey_id="survey-001",
            data={"Q1": "opt-1", "Q2": "Great product!"},
            submitted_at="2025-01-20T14:30:00Z",
            raw={},
        ),
        SurveyResponse(
            id="r2",
            survey_id="survey-001",
            data={"Q1": "opt-2", "Q2": "Could be better"},
            submitted_at="2025-01-21T10:00:00Z",
            raw={},
        ),
    ]


class TestSurveysResponses:
    @patch("alida_sdk.cli.AlidaClient")
    @patch("alida_sdk.cli.SurveyResource")
    def test_csv_raw_headers(self, mock_resource_cls: MagicMock, mock_client_cls: MagicMock):
        """--csv without --dataset-id uses raw concept names as headers."""
        mock_resource = MagicMock()
        mock_resource.get_responses.return_value = _make_responses()
        mock_resource_cls.return_value = mock_resource
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["surveys", "responses", "survey-001", "--csv"])
        assert result.exit_code == 0
        reader = csv.DictReader(io.StringIO(result.output))
        rows = list(reader)
        assert len(rows) == 2
        assert "Q1" in reader.fieldnames
        assert "Q2" in reader.fieldnames

    @patch("alida_sdk.cli.QuestionResource")
    @patch("alida_sdk.cli.AlidaClient")
    @patch("alida_sdk.cli.SurveyResource")
    def test_csv_with_dataset_id(
        self,
        mock_resource_cls: MagicMock,
        mock_client_cls: MagicMock,
        mock_qr_cls: MagicMock,
    ):
        """--csv --dataset-id produces human-readable headers and resolves choices."""
        mock_resource = MagicMock()
        mock_resource.get_responses.return_value = _make_responses()
        mock_resource_cls.return_value = mock_resource

        mock_qr = MagicMock()
        mock_qr.list_questions.return_value = _make_questions()
        mock_qr_cls.return_value = mock_qr

        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(
            app,
            ["surveys", "responses", "survey-001", "--csv", "--dataset-id", "ds-001"],
        )
        assert result.exit_code == 0
        reader = csv.DictReader(io.StringIO(result.output))
        rows = list(reader)
        assert len(rows) == 2
        assert "How satisfied are you?" in reader.fieldnames
        assert "Any comments?" in reader.fieldnames
        # Choice ID should be resolved to text
        assert rows[0]["How satisfied are you?"] == "Very satisfied"


class TestDatasetsList:
    @patch("alida_sdk.cli.AlidaClient")
    def test_csv_output(self, mock_client_cls: MagicMock):
        mock_client = MagicMock()
        mock_client.get_paginated.return_value = [
            {"id": "ds1", "name": "Dataset One"},
            {"id": "ds2", "name": "Dataset Two"},
        ]
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["datasets", "list", "--csv"])
        assert result.exit_code == 0
        reader = csv.DictReader(io.StringIO(result.output))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["id"] == "ds1"
        assert rows[0]["name"] == "Dataset One"


class TestQuestionsList:
    @patch("alida_sdk.cli.AlidaClient")
    @patch("alida_sdk.cli.QuestionResource")
    def test_json_output(self, mock_resource_cls: MagicMock, mock_client_cls: MagicMock):
        mock_resource = MagicMock()
        mock_resource.list_questions.return_value = _make_questions()
        mock_resource_cls.return_value = mock_resource
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["questions", "list", "s1", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        assert data[0]["id"] == "q1"
        assert data[0]["text"] == "How satisfied are you?"
        assert len(data[0]["answer_options"]) == 2

    @patch("alida_sdk.cli.AlidaClient")
    @patch("alida_sdk.cli.QuestionResource")
    def test_table_output(self, mock_resource_cls: MagicMock, mock_client_cls: MagicMock):
        mock_resource = MagicMock()
        mock_resource.list_questions.return_value = _make_questions()
        mock_resource_cls.return_value = mock_resource
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["questions", "list", "s1"])
        assert result.exit_code == 0

    @patch("alida_sdk.cli.AlidaClient")
    @patch("alida_sdk.cli.QuestionResource")
    def test_not_found_exits_2(self, mock_resource_cls: MagicMock, mock_client_cls: MagicMock):
        mock_resource = MagicMock()
        mock_resource.list_questions.side_effect = NotFoundError("not found")
        mock_resource_cls.return_value = mock_resource
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["questions", "list", "s1", "--json"])
        assert result.exit_code == 2

    @patch("alida_sdk.cli.AlidaClient")
    @patch("alida_sdk.cli.QuestionResource")
    def test_csv_output(self, mock_resource_cls: MagicMock, mock_client_cls: MagicMock):
        mock_resource = MagicMock()
        mock_resource.list_questions.return_value = _make_questions()
        mock_resource_cls.return_value = mock_resource
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["questions", "list", "s1", "--csv"])
        assert result.exit_code == 0
        reader = csv.DictReader(io.StringIO(result.output))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["id"] == "q1"
        assert rows[0]["name"] == "Q1"
        assert rows[0]["text"] == "How satisfied are you?"
        assert rows[0]["num_options"] == "2"


class TestQuestionsGet:
    @patch("alida_sdk.cli.AlidaClient")
    @patch("alida_sdk.cli.QuestionResource")
    def test_json_output(self, mock_resource_cls: MagicMock, mock_client_cls: MagicMock):
        mock_resource = MagicMock()
        mock_resource.get_question.return_value = _make_questions()[0]
        mock_resource_cls.return_value = mock_resource
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["questions", "get", "s1", "q1", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "q1"
        assert data["text"] == "How satisfied are you?"

    @patch("alida_sdk.cli.AlidaClient")
    @patch("alida_sdk.cli.QuestionResource")
    def test_not_found_exits_2(self, mock_resource_cls: MagicMock, mock_client_cls: MagicMock):
        mock_resource = MagicMock()
        mock_resource.get_question.side_effect = NotFoundError("not found")
        mock_resource_cls.return_value = mock_resource
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["questions", "get", "s1", "q1", "--json"])
        assert result.exit_code == 2

    @patch("alida_sdk.cli.AlidaClient")
    @patch("alida_sdk.cli.QuestionResource")
    def test_error_exits_1(self, mock_resource_cls: MagicMock, mock_client_cls: MagicMock):
        mock_resource = MagicMock()
        mock_resource.get_question.side_effect = AlidaError("server broke")
        mock_resource_cls.return_value = mock_resource
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.invoke(app, ["questions", "get", "s1", "q1", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"] == "server broke"

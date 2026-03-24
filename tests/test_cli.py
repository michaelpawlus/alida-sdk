"""Tests for the CLI module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from alida_sdk.cli import app
from alida_sdk.exceptions import AlidaError, NotFoundError
from alida_sdk.models import AnswerOption, Question, Survey

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
            text="How satisfied are you?",
            type="single_choice",
            answer_options=[
                AnswerOption(id="opt-1", text="Very satisfied", position=1, raw={}),
                AnswerOption(id="opt-2", text="Satisfied", position=2, raw={}),
            ],
            raw={},
        ),
        Question(
            id="q2",
            survey_id="s1",
            text="Any comments?",
            type="open_text",
            answer_options=[],
            raw={},
        ),
    ]


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

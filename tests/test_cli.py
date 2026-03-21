"""Tests for the CLI module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from alida_sdk.cli import app
from alida_sdk.exceptions import AlidaError, NotFoundError
from alida_sdk.models import Survey

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

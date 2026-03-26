"""Tests for the survey resource module."""

from __future__ import annotations

from unittest.mock import MagicMock

from alida_sdk.models import Survey, SurveyResponse
from alida_sdk.surveys import SurveyResource


class TestToSurvey:
    def test_maps_camel_case_fields(self, sample_survey_data: dict):
        survey = SurveyResource._to_survey(sample_survey_data)
        assert isinstance(survey, Survey)
        assert survey.id == "survey-001"
        assert survey.name == "Customer Satisfaction Q1"
        assert survey.status == "active"
        assert survey.created_at == "2025-01-15T10:00:00Z"
        assert survey.updated_at == "2025-02-01T12:00:00Z"
        assert survey.type == "survey"

    def test_maps_snake_case_fields(self):
        data = {
            "id": "s2",
            "name": "Test",
            "status": "draft",
            "created_at": "2025-03-01",
            "updated_at": "2025-03-02",
        }
        survey = SurveyResource._to_survey(data)
        assert survey.created_at == "2025-03-01"
        assert survey.updated_at == "2025-03-02"

    def test_preserves_raw_data(self, sample_survey_data: dict):
        survey = SurveyResource._to_survey(sample_survey_data)
        assert survey.raw == sample_survey_data

    def test_to_dict_includes_all_fields(self, sample_survey_data: dict):
        survey = SurveyResource._to_survey(sample_survey_data)
        d = survey.to_dict()
        assert d["id"] == "survey-001"
        assert d["name"] == "Customer Satisfaction Q1"


class TestToResponse:
    def test_maps_response_fields(self, sample_response_data: dict):
        resp = SurveyResource._to_response("survey-001", sample_response_data)
        assert isinstance(resp, SurveyResponse)
        assert resp.id == "resp-001"
        assert resp.survey_id == "survey-001"
        assert resp.submitted_at == "2025-01-20T14:30:00Z"
        assert resp.data["q1"] == "Very satisfied"
        assert resp.data["q2"] == 5

    def test_excludes_meta_fields_from_data(self, sample_response_data: dict):
        resp = SurveyResource._to_response("survey-001", sample_response_data)
        assert "id" not in resp.data
        assert "submittedAt" not in resp.data

    def test_preserves_raw_data(self, sample_response_data: dict):
        resp = SurveyResource._to_response("survey-001", sample_response_data)
        assert resp.raw == sample_response_data


def _paginated_survey_data() -> list[dict]:
    return [
        {
            "id": "s1",
            "name": "Customer Satisfaction Q1",
            "status": "active",
            "createdAt": "2025-01-15T10:00:00Z",
            "type": "survey",
        },
        {
            "id": "s2",
            "name": "Employee Engagement",
            "status": "draft",
            "createdAt": "2025-02-01T12:00:00Z",
            "type": "survey",
        },
        {
            "id": "s3",
            "name": "Product Feedback Q1",
            "status": "active",
            "createdAt": "2025-03-10T08:00:00Z",
            "type": "poll",
        },
        {
            "id": "s4",
            "name": "NPS Annual",
            "status": "closed",
            "createdAt": "2024-06-01T00:00:00Z",
            "type": "survey",
        },
    ]


class TestListSurveysFiltering:
    def test_no_filters_returns_all(self):
        mock_client = MagicMock()
        mock_client.get_paginated.return_value = _paginated_survey_data()
        resource = SurveyResource(mock_client)
        assert len(resource.list_surveys()) == 4

    def test_filter_by_status(self):
        mock_client = MagicMock()
        mock_client.get_paginated.return_value = _paginated_survey_data()
        resource = SurveyResource(mock_client)
        results = resource.list_surveys(status="active")
        assert len(results) == 2
        assert all(s.status == "active" for s in results)

    def test_filter_by_status_case_insensitive(self):
        mock_client = MagicMock()
        mock_client.get_paginated.return_value = _paginated_survey_data()
        resource = SurveyResource(mock_client)
        results = resource.list_surveys(status="DRAFT")
        assert len(results) == 1
        assert results[0].id == "s2"

    def test_filter_by_search(self):
        mock_client = MagicMock()
        mock_client.get_paginated.return_value = _paginated_survey_data()
        resource = SurveyResource(mock_client)
        results = resource.list_surveys(search="feedback")
        assert len(results) == 1
        assert results[0].id == "s3"

    def test_filter_by_search_case_insensitive(self):
        mock_client = MagicMock()
        mock_client.get_paginated.return_value = _paginated_survey_data()
        resource = SurveyResource(mock_client)
        results = resource.list_surveys(search="CUSTOMER")
        assert len(results) == 1
        assert results[0].id == "s1"

    def test_filter_by_since(self):
        mock_client = MagicMock()
        mock_client.get_paginated.return_value = _paginated_survey_data()
        resource = SurveyResource(mock_client)
        results = resource.list_surveys(since="2025-02-01")
        assert len(results) == 2
        assert {s.id for s in results} == {"s2", "s3"}

    def test_filter_by_until(self):
        mock_client = MagicMock()
        mock_client.get_paginated.return_value = _paginated_survey_data()
        resource = SurveyResource(mock_client)
        results = resource.list_surveys(until="2025-01-31")
        assert len(results) == 2
        assert {s.id for s in results} == {"s1", "s4"}

    def test_filters_compose_with_and(self):
        mock_client = MagicMock()
        mock_client.get_paginated.return_value = _paginated_survey_data()
        resource = SurveyResource(mock_client)
        results = resource.list_surveys(status="active", search="Q1")
        assert len(results) == 2
        assert {s.id for s in results} == {"s1", "s3"}

    def test_all_filters_combined(self):
        mock_client = MagicMock()
        mock_client.get_paginated.return_value = _paginated_survey_data()
        resource = SurveyResource(mock_client)
        results = resource.list_surveys(
            status="active", search="Q1", since="2025-02-01"
        )
        assert len(results) == 1
        assert results[0].id == "s3"

    def test_no_matches_returns_empty(self):
        mock_client = MagicMock()
        mock_client.get_paginated.return_value = _paginated_survey_data()
        resource = SurveyResource(mock_client)
        results = resource.list_surveys(status="archived")
        assert results == []


class TestGetResponsesFiltering:
    def _setup_mock_client(self):
        mock_client = MagicMock()
        mock_client.post.return_value = {"batchId": "batch-1"}
        mock_client.poll_batch.return_value = {"status": "completed", "data": "http://download"}
        mock_client.get.return_value = [
            {"id": "r1", "submittedAt": "2025-01-15T10:00:00Z", "q1": "a"},
            {"id": "r2", "submittedAt": "2025-02-01T12:00:00Z", "q1": "b"},
            {"id": "r3", "submittedAt": "2025-03-10T08:00:00Z", "q1": "c"},
        ]
        return mock_client

    def test_no_filters_returns_all(self):
        mock_client = self._setup_mock_client()
        resource = SurveyResource(mock_client)
        results = resource.get_responses("s1")
        assert len(results) == 3

    def test_filter_since(self):
        mock_client = self._setup_mock_client()
        resource = SurveyResource(mock_client)
        results = resource.get_responses("s1", since="2025-02-01")
        assert len(results) == 2
        assert {r.id for r in results} == {"r2", "r3"}

    def test_filter_until(self):
        mock_client = self._setup_mock_client()
        resource = SurveyResource(mock_client)
        results = resource.get_responses("s1", until="2025-01-31")
        assert len(results) == 1
        assert results[0].id == "r1"

    def test_filter_date_range(self):
        mock_client = self._setup_mock_client()
        resource = SurveyResource(mock_client)
        results = resource.get_responses(
            "s1", since="2025-01-20", until="2025-03-01"
        )
        assert len(results) == 1
        assert results[0].id == "r2"

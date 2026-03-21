"""Tests for the survey resource module."""

from __future__ import annotations

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

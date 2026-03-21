"""Survey resource methods for the Alida API."""

from __future__ import annotations

from alida_sdk.client import AlidaClient
from alida_sdk.exceptions import AlidaError
from alida_sdk.models import Survey, SurveyResponse


class SurveyResource:
    """Operations on Alida surveys (activities)."""

    def __init__(self, client: AlidaClient):
        self._client = client

    def list_surveys(self) -> list[Survey]:
        """List all surveys with auto-pagination."""
        items = self._client.get_paginated("activities")
        return [self._to_survey(item) for item in items]

    def get_survey(self, survey_id: str) -> Survey:
        """Get a single survey by ID."""
        data = self._client.get(f"activities/{survey_id}")
        return self._to_survey(data)

    def get_responses(
        self,
        survey_id: str,
        field_ids: list[str] | None = None,
    ) -> list[SurveyResponse]:
        """Export all responses for a survey using the batch export workflow.

        Steps: POST to initiate batch -> poll status -> download results.
        """
        # Step 1: Initiate batch export
        body: dict = {}
        if field_ids:
            body["fieldIds"] = field_ids

        batch_data = self._client.post(
            f"data/activities/{survey_id}/responses/batch", json=body
        )
        batch_id = batch_data.get("batchId") or batch_data.get("id")
        if not batch_id:
            raise AlidaError("No batch ID returned from batch export request")

        # Step 2: Poll until ready
        result = self._client.poll_batch(
            f"data/activities/{survey_id}/responses/batch/{batch_id}"
        )

        # Step 3: Download from the provided URL
        download_url = result.get("data") or result.get("downloadUrl")
        if not download_url:
            raise AlidaError("Batch export completed but no download URL provided")

        response_data = self._client.get(download_url)
        items = (
            response_data
            if isinstance(response_data, list)
            else response_data.get("data", [])
        )
        return [self._to_response(survey_id, item) for item in items]

    @staticmethod
    def _to_survey(data: dict) -> Survey:
        """Map raw API response to Survey model."""
        return Survey(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            status=data.get("status", ""),
            created_at=data.get("createdAt") or data.get("created_at"),
            updated_at=data.get("updatedAt") or data.get("updated_at"),
            type=data.get("type"),
            raw=data,
        )

    @staticmethod
    def _to_response(survey_id: str, data: dict) -> SurveyResponse:
        """Map raw API response to SurveyResponse model."""
        return SurveyResponse(
            id=str(data.get("id", "")),
            survey_id=survey_id,
            data={
                k: v
                for k, v in data.items()
                if k not in ("id", "submittedAt", "submitted_at")
            },
            submitted_at=data.get("submittedAt") or data.get("submitted_at"),
            raw=data,
        )

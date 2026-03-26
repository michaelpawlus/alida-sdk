"""Survey resource methods for the Alida API."""

from __future__ import annotations

from alida_sdk.client import AlidaClient
from alida_sdk.exceptions import AlidaError
from alida_sdk.models import Survey, SurveyResponse


class SurveyResource:
    """Operations on Alida surveys (activities)."""

    def __init__(self, client: AlidaClient):
        self._client = client

    def list_surveys(
        self,
        *,
        status: str | None = None,
        since: str | None = None,
        until: str | None = None,
        search: str | None = None,
    ) -> list[Survey]:
        """List all surveys with auto-pagination and optional filtering.

        Filters compose with AND logic — all specified conditions must match.

        Args:
            status: Filter by survey status (case-insensitive).
            since: Include surveys created at or after this ISO 8601 date.
            until: Include surveys created at or before this ISO 8601 date.
            search: Case-insensitive substring match on survey name.
        """
        items = self._client.get_paginated("activities")
        surveys = [self._to_survey(item) for item in items]

        if status:
            status_lower = status.lower()
            surveys = [s for s in surveys if s.status.lower() == status_lower]
        if search:
            search_lower = search.lower()
            surveys = [s for s in surveys if search_lower in s.name.lower()]
        if since:
            surveys = [s for s in surveys if s.created_at and s.created_at >= since]
        if until:
            surveys = [s for s in surveys if s.created_at and s.created_at <= until]

        return surveys

    def get_survey(self, survey_id: str) -> Survey:
        """Get a single survey by ID."""
        data = self._client.get(f"activities/{survey_id}")
        return self._to_survey(data)

    def get_responses(
        self,
        survey_id: str,
        field_ids: list[str] | None = None,
        *,
        since: str | None = None,
        until: str | None = None,
    ) -> list[SurveyResponse]:
        """Export all responses for a survey using the batch export workflow.

        Steps: POST to initiate batch -> poll status -> download results.

        Args:
            survey_id: The survey (activity) ID.
            field_ids: Optional list of field IDs to include.
            since: Include responses submitted at or after this ISO 8601 date.
            until: Include responses submitted at or before this ISO 8601 date.
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
        responses = [self._to_response(survey_id, item) for item in items]

        if since:
            responses = [
                r for r in responses if r.submitted_at and r.submitted_at >= since
            ]
        if until:
            responses = [
                r for r in responses if r.submitted_at and r.submitted_at <= until
            ]

        return responses

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

"""Shared test fixtures for Alida SDK tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from alida_sdk.auth import TokenManager
from alida_sdk.client import AlidaClient


@pytest.fixture
def mock_token_manager() -> TokenManager:
    """TokenManager that returns a fixed token without HTTP calls."""
    tm = MagicMock(spec=TokenManager)
    tm.auth_headers.return_value = {"Authorization": "Bearer test-token-123"}
    tm.get_token.return_value = "test-token-123"
    return tm


@pytest.fixture
def mock_client(mock_token_manager: TokenManager) -> AlidaClient:
    """AlidaClient with a mock token manager and test base URL."""
    return AlidaClient(
        base_url="https://api.test.alida.com/v2/applications/testapp",
        token_manager=mock_token_manager,
    )


@pytest.fixture
def sample_survey_data() -> dict:
    return {
        "id": "survey-001",
        "name": "Customer Satisfaction Q1",
        "status": "active",
        "createdAt": "2025-01-15T10:00:00Z",
        "updatedAt": "2025-02-01T12:00:00Z",
        "type": "survey",
    }


@pytest.fixture
def sample_response_data() -> dict:
    return {
        "id": "resp-001",
        "submittedAt": "2025-01-20T14:30:00Z",
        "q1": "Very satisfied",
        "q2": 5,
        "q3": "Great product!",
    }

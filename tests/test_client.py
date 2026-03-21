"""Tests for the HTTP client module."""

from __future__ import annotations

import httpx
import pytest
import respx

from alida_sdk.client import AlidaClient
from alida_sdk.exceptions import (
    AlidaError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError,
)


BASE_URL = "https://api.test.alida.com/v2/applications/testapp"


class TestRequestAuthInjection:
    @respx.mock
    def test_injects_auth_headers(self, mock_client: AlidaClient):
        route = respx.get(f"{BASE_URL}/activities").mock(
            return_value=httpx.Response(200, json=[])
        )
        mock_client.get("activities")
        request = route.calls.last.request
        assert request.headers["Authorization"] == "Bearer test-token-123"


class TestRetryBehavior:
    @respx.mock
    def test_retries_on_429(self, mock_client: AlidaClient):
        route = respx.get(f"{BASE_URL}/activities").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0"}),
                httpx.Response(200, json={"items": []}),
            ]
        )
        result = mock_client.get("activities")
        assert route.call_count == 2
        assert result == {"items": []}

    @respx.mock
    def test_retries_on_500(self, mock_client: AlidaClient):
        route = respx.get(f"{BASE_URL}/activities").mock(
            side_effect=[
                httpx.Response(500, text="Internal Server Error"),
                httpx.Response(200, json={"ok": True}),
            ]
        )
        result = mock_client.get("activities")
        assert route.call_count == 2
        assert result == {"ok": True}


class TestErrorMapping:
    @respx.mock
    def test_401_raises_authentication_error(self, mock_client: AlidaClient):
        respx.get(f"{BASE_URL}/test").mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )
        with pytest.raises(AuthenticationError):
            mock_client.get("test")

    @respx.mock
    def test_404_raises_not_found_error(self, mock_client: AlidaClient):
        respx.get(f"{BASE_URL}/test").mock(
            return_value=httpx.Response(404, text="Not Found")
        )
        with pytest.raises(NotFoundError):
            mock_client.get("test")

    @respx.mock
    def test_429_after_retry_raises_rate_limit_error(self, mock_client: AlidaClient):
        respx.get(f"{BASE_URL}/test").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0"}),
                httpx.Response(429, headers={"Retry-After": "0"}),
            ]
        )
        with pytest.raises(RateLimitError):
            mock_client.get("test")

    @respx.mock
    def test_500_after_retry_raises_server_error(self, mock_client: AlidaClient):
        respx.get(f"{BASE_URL}/test").mock(
            side_effect=[
                httpx.Response(500, text="Error"),
                httpx.Response(500, text="Error"),
            ]
        )
        with pytest.raises(ServerError):
            mock_client.get("test")


class TestPagination:
    @respx.mock
    def test_paginates_through_multiple_pages(self, mock_client: AlidaClient):
        route = respx.get(f"{BASE_URL}/activities").mock(
            side_effect=[
                httpx.Response(200, json={"items": [{"id": "1"}, {"id": "2"}]}),
                httpx.Response(200, json={"items": [{"id": "3"}]}),
            ]
        )
        result = mock_client.get_paginated("activities", limit=2)
        assert len(result) == 3
        assert result[0]["id"] == "1"
        assert result[2]["id"] == "3"

    @respx.mock
    def test_handles_list_response(self, mock_client: AlidaClient):
        respx.get(f"{BASE_URL}/items").mock(
            return_value=httpx.Response(200, json=[{"id": "a"}])
        )
        result = mock_client.get_paginated("items", limit=100)
        assert result == [{"id": "a"}]

    @respx.mock
    def test_stops_on_empty_response(self, mock_client: AlidaClient):
        respx.get(f"{BASE_URL}/items").mock(
            return_value=httpx.Response(200, json={"items": []})
        )
        result = mock_client.get_paginated("items")
        assert result == []

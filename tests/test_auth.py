"""Tests for the authentication module."""

from __future__ import annotations

import os
from unittest.mock import patch

import httpx
import pytest
import respx

from alida_sdk.auth import TokenManager
from alida_sdk.exceptions import AuthenticationError, ConfigurationError


class TestTokenManagerFromEnv:
    def test_raises_when_api_key_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError, match="ALIDA_API_KEY"):
                TokenManager.from_env()

    def test_raises_when_base_url_and_region_missing(self):
        with patch.dict(os.environ, {"ALIDA_API_KEY": "key"}, clear=True):
            with pytest.raises(ConfigurationError, match="ALIDA_BASE_URL"):
                TokenManager.from_env()

    def test_derives_base_url_from_region(self):
        env = {
            "ALIDA_API_KEY": "my-key",
            "ALIDA_REGION": "eu1",
        }
        with patch.dict(os.environ, env, clear=True):
            tm = TokenManager.from_env()
            assert tm._base_url == "https://api.eu1.alida.com"

    def test_creates_simple_mode_without_credentials(self):
        env = {"ALIDA_API_KEY": "my-key", "ALIDA_BASE_URL": "https://api.test.com"}
        with patch.dict(os.environ, env, clear=True):
            tm = TokenManager.from_env()
            assert tm._simple_mode is True
            assert tm.get_token() == "my-key"

    def test_creates_oauth_mode_with_client_credentials(self):
        env = {
            "ALIDA_API_KEY": "my-key",
            "ALIDA_BASE_URL": "https://api.test.com",
            "ALIDA_CLIENT_ID": "client-id",
            "ALIDA_CLIENT_SECRET": "client-secret",
        }
        with patch.dict(os.environ, env, clear=True):
            tm = TokenManager.from_env()
            assert tm._simple_mode is False


class TestTokenManagerAuthHeaders:
    def test_simple_mode_returns_api_key_header(self):
        tm = TokenManager(api_key="my-key", base_url="https://api.test.com")
        headers = tm.auth_headers()
        assert headers == {"x-api-key": "my-key"}

    @respx.mock
    def test_oauth_mode_returns_bearer_header(self):
        respx.post("https://api.test.com/oauth2/token").mock(
            return_value=httpx.Response(
                200, json={"access_token": "bearer-abc", "expires_in": 3600}
            )
        )
        tm = TokenManager(
            api_key="my-key",
            base_url="https://api.test.com",
            client_id="cid",
            client_secret="csecret",
        )
        headers = tm.auth_headers()
        assert headers == {"Authorization": "Bearer bearer-abc"}

    @respx.mock
    def test_oauth_sends_client_credentials_grant(self):
        route = respx.post("https://api.test.com/oauth2/token").mock(
            return_value=httpx.Response(
                200, json={"access_token": "tok", "expires_in": 3600}
            )
        )
        tm = TokenManager(
            api_key="my-key",
            base_url="https://api.test.com",
            client_id="cid",
            client_secret="csecret",
        )
        tm.get_token()
        request = route.calls.last.request
        assert b"grant_type=client_credentials" in request.content
        assert request.headers["x-api-key"] == "my-key"


class TestTokenCaching:
    @respx.mock
    def test_second_call_uses_cached_token(self):
        route = respx.post("https://api.test.com/oauth2/token").mock(
            return_value=httpx.Response(
                200, json={"access_token": "bearer-abc", "expires_in": 3600}
            )
        )
        tm = TokenManager(
            api_key="my-key",
            base_url="https://api.test.com",
            client_id="cid",
            client_secret="csecret",
        )
        tm.get_token()
        tm.get_token()
        assert route.call_count == 1


class TestTokenFetchErrors:
    @respx.mock
    def test_raises_on_401(self):
        respx.post("https://api.test.com/oauth2/token").mock(
            return_value=httpx.Response(401, json={"error": "invalid credentials"})
        )
        tm = TokenManager(
            api_key="my-key",
            base_url="https://api.test.com",
            client_id="cid",
            client_secret="csecret",
        )
        with pytest.raises(AuthenticationError, match="401"):
            tm.get_token()

"""Authentication module for the Alida API.

Supports two modes:
1. Full OAuth flow: x-api-key + username/password to retrieve a bearer token
2. Simple API-key mode: uses ALIDA_API_KEY directly as bearer token (when no username/password set)
"""

from __future__ import annotations

import os
import time

import httpx

from alida_sdk.exceptions import AuthenticationError, ConfigurationError


class TokenManager:
    """Manages authentication tokens for the Alida API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._token: str | None = None
        self._token_expiry: float = 0.0
        self._simple_mode = not (username and password)

    @classmethod
    def from_env(cls) -> TokenManager:
        """Create a TokenManager from environment variables.

        Required: ALIDA_API_KEY, ALIDA_BASE_URL
        Optional: ALIDA_USERNAME, ALIDA_PASSWORD (if not set, uses simple API-key mode)
        """
        api_key = os.environ.get("ALIDA_API_KEY")
        base_url = os.environ.get("ALIDA_BASE_URL")
        if not api_key or not base_url:
            raise ConfigurationError(
                "ALIDA_API_KEY and ALIDA_BASE_URL environment variables must be set"
            )
        return cls(
            api_key=api_key,
            base_url=base_url,
            username=os.environ.get("ALIDA_USERNAME"),
            password=os.environ.get("ALIDA_PASSWORD"),
        )

    def get_token(self) -> str:
        """Return a valid bearer token, fetching or refreshing as needed."""
        if self._simple_mode:
            return self._api_key
        if self._token and not self._is_expired():
            return self._token
        self._fetch_token()
        return self._token  # type: ignore[return-value]

    def auth_headers(self) -> dict[str, str]:
        """Return headers dict with authentication."""
        if self._simple_mode:
            return {"x-api-key": self._api_key}
        return {"Authorization": f"Bearer {self.get_token()}"}

    def _fetch_token(self) -> None:
        """POST to the auth endpoint to retrieve a bearer token."""
        url = f"{self._base_url}/auth/token"
        headers = {"x-api-key": self._api_key}
        payload = {"username": self._username, "password": self._password}

        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise AuthenticationError(
                f"Authentication failed: {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise AuthenticationError(f"Authentication request failed: {e}") from e

        data = response.json()
        self._token = data.get("token") or data.get("access_token")
        if not self._token:
            raise AuthenticationError("No token found in authentication response")

        # Cache for slightly less than the reported expiry, or default to 1 hour
        expires_in = data.get("expires_in", 3600)
        self._token_expiry = time.time() + expires_in - 60

    def _is_expired(self) -> bool:
        """Check if the cached token has expired."""
        return time.time() >= self._token_expiry

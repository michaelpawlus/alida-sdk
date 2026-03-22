"""Authentication module for the Alida API.

Supports two modes:
1. OAuth2 client_credentials: client_id/client_secret + x-api-key to retrieve a bearer token
2. Simple API-key mode: uses ALIDA_API_KEY directly (when no client_id/client_secret set)
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
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._token_expiry: float = 0.0
        self._simple_mode = not (client_id and client_secret)

    @classmethod
    def from_env(cls) -> TokenManager:
        """Create a TokenManager from environment variables.

        Required: ALIDA_API_KEY, ALIDA_BASE_URL (or ALIDA_REGION)
        Optional: ALIDA_CLIENT_ID, ALIDA_CLIENT_SECRET (if not set, uses simple API-key mode)
        """
        api_key = os.environ.get("ALIDA_API_KEY")
        base_url = os.environ.get("ALIDA_BASE_URL")
        region = os.environ.get("ALIDA_REGION")

        if not api_key:
            raise ConfigurationError(
                "ALIDA_API_KEY environment variable must be set"
            )
        if not base_url:
            if region:
                base_url = f"https://api.{region}.alida.com"
            else:
                raise ConfigurationError(
                    "ALIDA_BASE_URL or ALIDA_REGION environment variable must be set"
                )

        return cls(
            api_key=api_key,
            base_url=base_url,
            client_id=os.environ.get("ALIDA_CLIENT_ID"),
            client_secret=os.environ.get("ALIDA_CLIENT_SECRET"),
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
        """POST to the OAuth2 token endpoint using client_credentials grant."""
        url = f"{self._base_url}/oauth2/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "x-api-key": self._api_key,
        }
        data = {"grant_type": "client_credentials"}

        try:
            response = httpx.post(
                url,
                auth=(self._client_id, self._client_secret),  # type: ignore[arg-type]
                headers=headers,
                data=data,
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise AuthenticationError(
                f"Authentication failed: {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise AuthenticationError(f"Authentication request failed: {e}") from e

        resp_data = response.json()
        self._token = resp_data.get("access_token") or resp_data.get("token")
        if not self._token:
            raise AuthenticationError("No token found in authentication response")

        # Cache for slightly less than the reported expiry, or default to 25 min
        expires_in = resp_data.get("expires_in", 1500)
        self._token_expiry = time.time() + expires_in - 60

    def _is_expired(self) -> bool:
        """Check if the cached token has expired."""
        return time.time() >= self._token_expiry

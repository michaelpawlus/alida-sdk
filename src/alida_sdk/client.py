"""HTTP client for the Alida API with retry, pagination, and batch polling."""

from __future__ import annotations

import os
import time

import httpx

from alida_sdk.auth import TokenManager
from alida_sdk.exceptions import (
    AlidaError,
    AuthenticationError,
    ConfigurationError,
    NotFoundError,
    RateLimitError,
    ServerError,
)


class AlidaClient:
    """Alida API client wrapping httpx with auth, retry, and pagination."""

    def __init__(
        self,
        base_url: str | None = None,
        community_key: str | None = None,
        token_manager: TokenManager | None = None,
    ):
        self._token_manager = token_manager or TokenManager.from_env()

        raw_base = (base_url or os.environ.get("ALIDA_BASE_URL") or "").rstrip("/")
        if not raw_base:
            region = os.environ.get("ALIDA_REGION")
            if region:
                raw_base = f"https://api.{region}.alida.com"
            else:
                raise ConfigurationError(
                    "ALIDA_BASE_URL or ALIDA_REGION environment variable must be set"
                )

        self._base_url = raw_base
        self._community_key = community_key or os.environ.get("ALIDA_COMMUNITY_KEY", "")
        if not self._community_key:
            raise ConfigurationError(
                "ALIDA_COMMUNITY_KEY environment variable must be set"
            )

        self._api_prefix = f"{self._base_url}/v1/applications/{self._community_key}"
        self._http = httpx.Client(timeout=30.0)

    def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        """Core request with auth injection, 1 retry on 429/5xx, error mapping."""
        if path.startswith("http"):
            url = path
        else:
            url = f"{self._api_prefix}/{path.lstrip('/')}"

        headers = {
            **self._token_manager.auth_headers(),
            **kwargs.pop("headers", {}),  # type: ignore[union-attr]
        }

        last_response: httpx.Response | None = None
        for attempt in range(2):
            try:
                response = self._http.request(
                    method, url, headers=headers, **kwargs  # type: ignore[arg-type]
                )
            except httpx.RequestError as e:
                raise AlidaError(f"Request failed: {e}") from e

            last_response = response

            if response.status_code == 429 and attempt == 0:
                retry_after = int(response.headers.get("Retry-After", "5"))
                time.sleep(min(retry_after, 30))
                continue

            if response.status_code >= 500 and attempt == 0:
                time.sleep(2)
                continue

            break

        assert last_response is not None
        self._raise_for_status(last_response)
        return last_response

    def get(self, path: str, **kwargs: object) -> dict:
        """GET request, returning parsed JSON."""
        return self._request("GET", path, **kwargs).json()  # type: ignore[no-any-return]

    def post(self, path: str, **kwargs: object) -> dict:
        """POST request, returning parsed JSON."""
        return self._request("POST", path, **kwargs).json()  # type: ignore[no-any-return]

    def get_paginated(
        self,
        path: str,
        *,
        params: dict | None = None,
    ) -> list[dict]:
        """Auto-paginate using link-based rel=next pagination."""
        all_items: list[dict] = []
        url: str | None = path
        request_params = dict(params or {})

        while url:
            data = self.get(url, params=request_params)

            # Handle various response envelope shapes
            if isinstance(data, list):
                items = data
            else:
                items = data.get("items", data.get("data", []))

            if not items:
                break
            all_items.extend(items)

            # Follow rel=next link for pagination
            url = None
            if isinstance(data, dict):
                for link in data.get("links", []):
                    if link.get("rel") == "next" and link.get("href"):
                        url = link["href"]
                        request_params = {}  # next URL includes params
                        break

        return all_items

    def poll_batch(
        self,
        path: str,
        *,
        poll_interval: float = 2.0,
        max_wait: float = 300.0,
    ) -> dict:
        """Poll a batch endpoint until status is completed or failed."""
        start = time.time()

        while True:
            data = self.get(path)
            status = (
                data.get("status", "").lower()
                if isinstance(data, dict)
                else "unknown"
            )

            if status in ("completed", "complete", "done"):
                return data
            if status in ("failed", "error"):
                raise AlidaError(
                    f"Batch export failed: {data.get('error', 'unknown error')}"
                )

            elapsed = time.time() - start
            if elapsed >= max_wait:
                raise AlidaError(
                    f"Batch export timed out after {max_wait}s (status: {status})"
                )

            time.sleep(poll_interval)

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Map HTTP status codes to custom exceptions."""
        if response.status_code < 400:
            return

        body = response.text
        status = response.status_code

        if status == 401:
            raise AuthenticationError(f"Authentication failed: {body}")
        if status == 404:
            raise NotFoundError(f"Resource not found: {body}")
        if status == 429:
            raise RateLimitError(f"Rate limited: {body}")
        if status >= 500:
            raise ServerError(f"Server error ({status}): {body}")

        raise AlidaError(f"HTTP {status}: {body}")

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def __enter__(self) -> AlidaClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

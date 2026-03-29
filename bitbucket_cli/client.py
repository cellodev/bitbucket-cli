from __future__ import annotations

import json
from typing import Any, Mapping
from urllib.parse import quote, urljoin

import httpx

from bitbucket_cli.errors import BitbucketAPIError, error_message_from_body

DEFAULT_BASE_URL = "https://api.bitbucket.org/2.0"


class BitbucketClient:
    """Synchronous HTTP client for Bitbucket Cloud REST API 2.0."""

    def __init__(
        self,
        *,
        token: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/") + "/"
        self._own_client = client is None
        self._auth_headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        self._client = client or httpx.Client(
            headers=self._auth_headers,
            timeout=timeout,
        )

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> BitbucketClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Mapping[str, Any] | list[Any] | None = None,
    ) -> Any:
        """Send a request. `path` is relative to API root (e.g. ``workspaces/ws/projects/``)."""
        path = path.lstrip("/")
        url = urljoin(self._base_url, path)
        req_headers = dict(self._auth_headers)
        if json_body is not None:
            req_headers["Content-Type"] = "application/json"
        response = self._client.request(
            method,
            url,
            json=json_body,
            headers=req_headers,
        )
        if response.status_code == 204:
            return None
        try:
            data = response.json() if response.content else None
        except json.JSONDecodeError:
            data = None
        if response.is_success:
            return data
        msg = error_message_from_body(data) if isinstance(data, dict) else None
        if not msg:
            msg = response.text.strip() or response.reason_phrase
        raise BitbucketAPIError(
            response.status_code,
            f"Bitbucket API error {response.status_code}: {msg}",
            payload=data if isinstance(data, dict) else None,
        )


def encode_path_segment(segment: str) -> str:
    """Encode a single URL path segment (workspace, repo slug, user id)."""
    return quote(segment, safe="")

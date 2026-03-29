from __future__ import annotations

import json

import httpx
import pytest

from bitbucket_cli.client import BitbucketClient
from bitbucket_cli.errors import BitbucketAPIError


def test_request_success_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer tok"
        return httpx.Response(200, json={"type": "user"})

    transport = httpx.MockTransport(handler)
    inner = httpx.Client(transport=transport)
    with BitbucketClient(token="tok", client=inner) as client:
        assert client.request("GET", "user") == {"type": "user"}


def test_request_204_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    transport = httpx.MockTransport(handler)
    inner = httpx.Client(transport=transport)
    with BitbucketClient(token="tok", client=inner) as client:
        assert client.request("DELETE", "x") is None


def test_request_api_error_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"message": "bad request"}},
        )

    transport = httpx.MockTransport(handler)
    inner = httpx.Client(transport=transport)
    with BitbucketClient(token="tok", client=inner) as client:
        with pytest.raises(BitbucketAPIError) as ei:
            client.request("GET", "x")
        assert ei.value.status_code == 400
        assert "bad request" in str(ei.value).lower()


def test_post_sets_json_body() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content.decode()
        captured["ct"] = request.headers.get("content-type", "")
        return httpx.Response(201, json={"created": True})

    transport = httpx.MockTransport(handler)
    inner = httpx.Client(transport=transport)
    with BitbucketClient(token="tok", client=inner) as client:
        client.request("POST", "path", json_body={"a": 1})
    assert "application/json" in captured["ct"]
    assert json.loads(captured["body"]) == {"a": 1}

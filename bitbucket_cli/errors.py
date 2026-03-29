from __future__ import annotations

from typing import Any


class ConfigError(ValueError):
    """Missing or invalid configuration (workspace, token)."""


class BitbucketAPIError(RuntimeError):
    """Bitbucket returned a non-success HTTP status."""

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.payload = payload or {}
        super().__init__(message)


def error_message_from_body(body: dict[str, Any] | None) -> str | None:
    if not body:
        return None
    err = body.get("error")
    if isinstance(err, dict):
        msg = err.get("message")
        if isinstance(msg, str):
            return msg
    return None

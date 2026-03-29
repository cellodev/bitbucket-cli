from __future__ import annotations

import os
from dataclasses import dataclass

from bitbucket_cli.errors import ConfigError


@dataclass(frozen=True)
class Config:
    workspace: str
    token: str


def load_config(*, workspace: str | None = None, token: str | None = None) -> Config:
    ws = (workspace or os.environ.get("BITBUCKET_WORKSPACE") or "").strip()
    tok = (token or os.environ.get("BITBUCKET_TOKEN") or "").strip()
    if not ws:
        raise ConfigError(
            "Workspace is required: set BITBUCKET_WORKSPACE or pass --workspace.",
        )
    if not tok:
        raise ConfigError(
            "OAuth access token is required: set BITBUCKET_TOKEN or pass --token.",
        )
    return Config(workspace=ws, token=tok)

from __future__ import annotations

import json

import pytest

from bitbucket_cli.cli import main


def test_cli_missing_workspace_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BITBUCKET_WORKSPACE", raising=False)
    monkeypatch.delenv("BITBUCKET_TOKEN", raising=False)
    with pytest.raises(SystemExit) as ei:
        main(["create-project", "--name", "N", "--key", "K"])
    assert ei.value.code == 2


def test_cli_missing_token_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BITBUCKET_WORKSPACE", "ws")
    monkeypatch.delenv("BITBUCKET_TOKEN", raising=False)
    with pytest.raises(SystemExit) as ei:
        main(["create-project", "--name", "N", "--key", "K"])
    assert ei.value.code == 2


def test_cli_create_project_invokes_service(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("BITBUCKET_WORKSPACE", "ws")
    monkeypatch.setenv("BITBUCKET_TOKEN", "t")

    class FakeClient:
        def __init__(self, *a, **k) -> None:
            pass

        def close(self) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *a) -> None:
            pass

        def request(self, *a, **k):
            return {"type": "project", "key": "K"}

    monkeypatch.setattr("bitbucket_cli.cli.BitbucketClient", FakeClient)

    main(["create-project", "--name", "N", "--key", "K"])
    out = capsys.readouterr().out
    assert json.loads(out)["key"] == "K"

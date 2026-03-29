from __future__ import annotations

from typing import Any

import pytest

from bitbucket_cli.service import BitbucketService, _looks_like_atlassian_account_id


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any]] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
    ) -> dict[str, Any]:
        self.calls.append((method, path, json_body))
        return {}


def test_create_project_posts_expected_path_and_body() -> None:
    rc = RecordingClient()
    svc = BitbucketService(rc, "myws")
    svc.create_project("Proj Name", "PN", description="d", is_private=True)
    assert len(rc.calls) == 1
    method, path, body = rc.calls[0]
    assert method == "POST"
    assert path == "workspaces/myws/projects/"
    assert body == {
        "name": "Proj Name",
        "key": "PN",
        "is_private": True,
        "description": "d",
    }


def test_create_repository_includes_project_key() -> None:
    rc = RecordingClient()
    svc = BitbucketService(rc, "w")
    svc.create_repository("rslug", project_key="PK", is_private=False)
    _, path, body = rc.calls[0]
    assert path == "repositories/w/rslug"
    assert body == {"scm": "git", "is_private": False, "project": {"key": "PK"}}


def test_add_user_permission_resolves_nickname_via_get_user() -> None:
    class Client:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, Any]] = []

        def request(
            self,
            method: str,
            path: str,
            *,
            json_body: Any = None,
        ) -> dict[str, Any]:
            self.calls.append((method, path, json_body))
            if method == "GET" and path.startswith("users/"):
                return {
                    "account_id": "557058:aaa-bbb-ccc",
                    "uuid": "{u-u-i-d}",
                }
            return {}

    c = Client()
    svc = BitbucketService(c, "ws")
    svc.add_repository_user_permission("repo", "alice", "read")
    assert c.calls[-1][0] == "PUT"
    assert c.calls[-1][1] == "repositories/ws/repo/permissions-config/users/557058:aaa-bbb-ccc"
    assert c.calls[-1][2] == {"permission": "read"}


def test_branch_exempt_builds_user_objects() -> None:
    class Client:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, Any]] = []

        def request(
            self,
            method: str,
            path: str,
            *,
            json_body: Any = None,
        ) -> dict[str, Any]:
            self.calls.append((method, path, json_body))
            if method == "GET":
                return {"uuid": "{1111-2222}", "account_id": "557058:x"}
            return {}

    c = Client()
    svc = BitbucketService(c, "ws")
    svc.exempt_users_push_to_production_branch("r", ["u1", "u2"])
    post = [x for x in c.calls if x[0] == "POST"][0]
    assert post[1] == "repositories/ws/r/branch-restrictions"
    body = post[2]
    assert body["kind"] == "push"
    assert body["branch_type"] == "production"
    assert body["users"] == [
        {"type": "user", "uuid": "{1111-2222}"},
        {"type": "user", "uuid": "{1111-2222}"},
    ]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("557058:abc", True),
        ("alice", False),
        ("no-colon", False),
    ],
)
def test_looks_like_atlassian_account_id(value: str, expected: bool) -> None:
    assert _looks_like_atlassian_account_id(value) is expected

from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import quote

from bitbucket_cli.client import BitbucketClient


def _segment(value: str) -> str:
    return quote(value, safe="")


def _user_lookup_segment(user_ref: str) -> str:
    """Path segment for ``GET /users/{selected_user}`` (allows ``:`` in Atlassian account IDs)."""
    return quote(user_ref, safe=":")


def _account_id_path_segment(account_id: str) -> str:
    return quote(account_id, safe=":")


class BitbucketService:
    """High-level operations used by the CLI (maps 1:1 to challenge features)."""

    def __init__(self, client: BitbucketClient, workspace: str) -> None:
        self._client = client
        self._workspace = workspace

    def create_project(
        self,
        name: str,
        key: str,
        *,
        description: str | None = None,
        is_private: bool = True,
    ) -> Any:
        body: dict[str, Any] = {
            "name": name,
            "key": key,
            "is_private": is_private,
        }
        if description is not None:
            body["description"] = description
        ws = _segment(self._workspace)
        return self._client.request(
            "POST",
            f"workspaces/{ws}/projects/",
            json_body=body,
        )

    def create_repository(
        self,
        repo_slug: str,
        *,
        project_key: str | None = None,
        description: str | None = None,
        is_private: bool = True,
        scm: str = "git",
    ) -> Any:
        body: dict[str, Any] = {"scm": scm, "is_private": is_private}
        if description is not None:
            body["description"] = description
        if project_key is not None:
            body["project"] = {"key": project_key}
        ws = _segment(self._workspace)
        slug = _segment(repo_slug)
        return self._client.request(
            "POST",
            f"repositories/{ws}/{slug}",
            json_body=body,
        )

    def fetch_user(self, user_ref: str) -> Mapping[str, Any]:
        seg = _user_lookup_segment(user_ref)
        data = self._client.request("GET", f"users/{seg}")
        if not isinstance(data, dict):
            raise ValueError(f"Unexpected user response for {user_ref!r}")
        return data

    def resolve_account_id(self, user_ref: str) -> str:
        if _looks_like_atlassian_account_id(user_ref):
            return user_ref
        data = self.fetch_user(user_ref)
        aid = data.get("account_id")
        if not isinstance(aid, str) or not aid:
            raise ValueError(
                f"User {user_ref!r} has no account_id; pass an Atlassian account id (557058:…).",
            )
        return aid

    def user_branch_rule_payload(self, user_ref: str) -> dict[str, str]:
        data = self.fetch_user(user_ref)
        uuid = data.get("uuid")
        if not isinstance(uuid, str) or not uuid:
            raise ValueError(
                f"User {user_ref!r} has no uuid; cannot build branch restriction payload.",
            )
        return {"type": "user", "uuid": uuid}

    def add_repository_user_permission(
        self,
        repo_slug: str,
        user_ref: str,
        permission: str,
    ) -> Any:
        account_id = self.resolve_account_id(user_ref)
        ws = _segment(self._workspace)
        rs = _segment(repo_slug)
        uid = _account_id_path_segment(account_id)
        return self._client.request(
            "PUT",
            f"repositories/{ws}/{rs}/permissions-config/users/{uid}",
            json_body={"permission": permission},
        )

    def remove_repository_user_permission(self, repo_slug: str, user_ref: str) -> Any:
        account_id = self.resolve_account_id(user_ref)
        ws = _segment(self._workspace)
        rs = _segment(repo_slug)
        uid = _account_id_path_segment(account_id)
        return self._client.request(
            "DELETE",
            f"repositories/{ws}/{rs}/permissions-config/users/{uid}",
        )

    def exempt_users_push_to_production_branch(
        self,
        repo_slug: str,
        user_refs: list[str],
    ) -> Any:
        """
        Create a ``push`` restriction on the branching-model **production** branch.

        Users listed in ``user_refs`` may push; everyone else cannot push to that branch,
        which matches the usual workflow where others must use pull requests.
        """
        users: list[dict[str, str]] = []
        for ref in user_refs:
            users.append(self.user_branch_rule_payload(ref))
        body: dict[str, Any] = {
            "type": "branchrestriction",
            "kind": "push",
            "branch_match_kind": "branching_model",
            "branch_type": "production",
            "users": users,
            "groups": [],
        }
        ws = _segment(self._workspace)
        rs = _segment(repo_slug)
        return self._client.request(
            "POST",
            f"repositories/{ws}/{rs}/branch-restrictions",
            json_body=body,
        )


def _looks_like_atlassian_account_id(user_ref: str) -> bool:
    if ":" not in user_ref:
        return False
    left, _right = user_ref.split(":", 1)
    return left.isdigit()

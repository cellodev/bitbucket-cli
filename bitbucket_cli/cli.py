from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from bitbucket_cli.client import BitbucketClient
from bitbucket_cli.config import load_config
from bitbucket_cli.errors import BitbucketAPIError, ConfigError
from bitbucket_cli.service import BitbucketService


def _emit(result: Any) -> None:
    if result is None:
        return
    print(json.dumps(result, indent=2))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bitbucket-cli",
        description="Bitbucket Cloud REST API helper (projects, repos, permissions, branch rules).",
    )
    p.add_argument(
        "--workspace",
        "-w",
        help="Workspace slug (overrides BITBUCKET_WORKSPACE).",
    )
    p.add_argument(
        "--token",
        help="OAuth access token (overrides BITBUCKET_TOKEN; prefer environment variables).",
    )

    sub = p.add_subparsers(dest="command", required=True)

    cp = sub.add_parser("create-project", help="Create a workspace project.")
    cp.add_argument("--name", required=True)
    cp.add_argument(
        "--key",
        required=True,
        help="Short project key (e.g. PROJ).",
    )
    cp.add_argument("--description", default=None)
    cp.add_argument(
        "--public",
        action="store_true",
        help="Make the project public (default is private).",
    )

    cr = sub.add_parser("create-repo", help="Create a repository.")
    cr.add_argument("--slug", required=True, help="Repository slug (appears in URL).")
    cr.add_argument(
        "--project-key",
        default=None,
        help="Assign to this project key (recommended).",
    )
    cr.add_argument("--description", default=None)
    cr.add_argument(
        "--public",
        action="store_true",
        help="Create a public repository (default is private).",
    )

    ua = sub.add_parser(
        "user-add",
        help="Grant explicit repository access to a user (workspace member).",
    )
    ua.add_argument("--repo", required=True)
    ua.add_argument(
        "--user",
        required=True,
        help="Bitbucket username / nickname, or Atlassian account id (557058:…).",
    )
    ua.add_argument(
        "--permission",
        choices=("read", "write", "admin"),
        default="write",
    )

    ur = sub.add_parser("user-remove", help="Revoke explicit repository access for a user.")
    ur.add_argument("--repo", required=True)
    ur.add_argument("--user", required=True)

    be = sub.add_parser(
        "branch-exempt-push",
        help=(
            "Add a push restriction on the production (mainline) branch: listed users may push; "
            "others cannot push there (typical PR workflow)."
        ),
    )
    be.add_argument("--repo", required=True)
    be.add_argument(
        "--user",
        dest="users",
        action="append",
        required=True,
        help="User to exempt (repeat flag for multiple). Username or account id.",
    )

    return p


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        cfg = load_config(workspace=args.workspace, token=args.token)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc

    with BitbucketClient(token=cfg.token) as client:
        svc = BitbucketService(client, cfg.workspace)
        try:
            if args.command == "create-project":
                result = svc.create_project(
                    args.name,
                    args.key,
                    description=args.description,
                    is_private=not args.public,
                )
            elif args.command == "create-repo":
                result = svc.create_repository(
                    args.slug,
                    project_key=args.project_key,
                    description=args.description,
                    is_private=not args.public,
                )
            elif args.command == "user-add":
                result = svc.add_repository_user_permission(
                    args.repo,
                    args.user,
                    args.permission,
                )
            elif args.command == "user-remove":
                result = svc.remove_repository_user_permission(args.repo, args.user)
            elif args.command == "branch-exempt-push":
                result = svc.exempt_users_push_to_production_branch(
                    args.repo,
                    list(args.users),
                )
            else:
                raise AssertionError(f"Unhandled command: {args.command}")
        except BitbucketAPIError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(1) from exc
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(2) from exc

    _emit(result)


if __name__ == "__main__":
    main()

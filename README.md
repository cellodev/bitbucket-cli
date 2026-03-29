# bitbucket-cli

Small **Python CLI** for [Bitbucket Cloud REST API 2.0](https://developer.atlassian.com/cloud/bitbucket/rest/intro/). Built for the Platform Tooling coding challenge: create projects and repositories, manage explicit repository permissions for users, and add a **push** branch restriction so only selected users can push to the **production** (mainline) branch—others must use pull requests.

## Requirements

- Python **3.10+**
- A Bitbucket Cloud workspace and an **OAuth access token** with appropriate scopes (see [Use OAuth on Bitbucket Cloud](https://support.atlassian.com/bitbucket-cloud/docs/use-oauth-on-bitbucket-cloud/)).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Getting an OAuth access token

Create an **OAuth consumer** on your Bitbucket workspace (callback URL e.g. `https://localhost:3000/callback`) and note the **Key** and **Secret**.

Some challenge materials still mention opening the authorize URL with `response_type=token` and reading the token from the URL fragment. **Bitbucket Cloud often rejects that** (`unsupported_response_type` / “Must be one of: **code**”). In that case use the **authorization code** flow from the same documentation:

1. Sign in to Bitbucket in the browser, then open (replace `YOUR_KEY`):

   `https://bitbucket.org/site/oauth2/authorize?client_id=YOUR_KEY&response_type=code`

   If authorization fails without a redirect URI, append the same callback you configured on the consumer, URL-encoded, for example:

   `&redirect_uri=https%3A%2F%2Flocalhost%3A3000%2Fcallback`

2. After you approve the app, Bitbucket redirects to your callback. The browser may show “connection refused” on `localhost` if nothing is listening there—that is fine. Copy the **`code`** query parameter from the address bar (`?code=...`).

3. Exchange the code for tokens (run locally; do not commit Key/Secret):

   ```bash
   curl -sS -X POST -u 'YOUR_KEY:YOUR_SECRET' \
     https://bitbucket.org/site/oauth2/access_token \
     -d grant_type=authorization_code \
     -d code='PASTE_CODE_HERE'
   ```

   Use the `access_token` value from the JSON response. Tokens expire in about **two hours**; the response may include a `refresh_token`—see [Use OAuth on Bitbucket Cloud](https://support.atlassian.com/bitbucket-cloud/docs/use-oauth-on-bitbucket-cloud/) for refresh.

This CLI only needs a **Bearer** token (`BITBUCKET_TOKEN`); it does not run the OAuth browser flow for you.

Export credentials (recommended):

```bash
export BITBUCKET_WORKSPACE="your-workspace-slug"
export BITBUCKET_TOKEN="your-access-token"
```

Optional: copy `.env.example` to `.env` and load it with your shell or a tool of your choice—the CLI does **not** read `.env` by itself to avoid hidden magic.

## Usage

Global options:

| Option | Environment variable | Description |
|--------|----------------------|-------------|
| `--workspace` / `-w` | `BITBUCKET_WORKSPACE` | Workspace slug |
| `--token` | `BITBUCKET_TOKEN` | OAuth bearer token (prefer env over flag) |

### Commands

**Create a project**

```bash
bitbucket-cli create-project --name "My project" --key PROJ --description "Optional"
# add --public for a public project (default is private)
```

**Create a repository**

```bash
bitbucket-cli create-repo --slug my-repo --project-key PROJ
# --project-key is optional; Bitbucket may assign the oldest project if omitted
```

**Grant repository access to a user** (`read` \| `write` \| `admin`)

```bash
bitbucket-cli user-add --repo my-repo --user some_nickname --permission write
# --user may be a Bitbucket nickname or an Atlassian account id (557058:…)
```

**Revoke explicit repository access**

```bash
bitbucket-cli user-remove --repo my-repo --user some_nickname
```

**Restrict pushes to the production branch (PR workflow)**

```bash
bitbucket-cli branch-exempt-push --repo my-repo --user alice --user bob
```

This creates a [`push` branch restriction](https://developer.atlassian.com/cloud/bitbucket/rest/api-group-branch-restrictions/#api-repositories-workspace-repo-slug-branch-restrictions-post) scoped to the branching-model **`production`** branch type. Only users listed after `--user` may push there; everyone else is blocked from pushing to that branch, which is the usual way to force pull requests for everyone except a few exempt accounts.

**Note:** Your repository must use a branching model where the default/main line is the **production** type. If your main branch is classified differently, adjust the branching model in Bitbucket or extend the CLI (see design notes below).

You can also run the module directly:

```bash
python -m bitbucket_cli --help
```

Successful responses are printed as **JSON** on stdout. Errors go to **stderr** with exit code **1** (API) or **2** (configuration / bad input).

## Tests

```bash
pytest
```

Tests use **no network**: `httpx.MockTransport` and lightweight fakes exercise the HTTP client, service layer, and CLI wiring.

## Design decisions

- **Layers:** `cli` (argparse, exit codes) → `service` (feature-level operations) → `client` (HTTP + errors). This keeps parsing and side effects at the edges and makes each layer easy to explain in a code review.
- **httpx:** One small dependency; supports injecting a client for tests and sends auth headers on **every** request so a custom `httpx.Client` still authenticates correctly.
- **Repository permissions:** Implemented with [`permissions-config/users`](https://developer.atlassian.com/cloud/bitbucket/new-repo-permission-apis/) (`PUT` / `DELETE`), which matches “add/remove users” in the sense of **repository access**. Workspace-level invites are a different product surface; the challenge maps cleanly to explicit repo permissions.
- **Branch rule:** Implemented as documented **exemptions** on a `push` restriction (`users` on the rule are allowed to push; others are not). Alternative interpretations (e.g. only tweaking required-approvals rules) would use different `kind` values and are not equivalent on the API.
- **Configuration:** Environment variables first, optional CLI overrides for demos—no silent `.env` loading.
- **OAuth:** The tool expects an access token in the environment; obtaining that token is a separate step (browser + `curl` today). That matches the challenge’s “get a token” tip and keeps the codebase small; Bitbucket’s authorize endpoint may only support `response_type=code`, even where older docs still mention `token` in the URL.

## References

- [Bitbucket Cloud REST API](https://developer.atlassian.com/cloud/bitbucket/rest/intro/)
- [Branch restrictions](https://developer.atlassian.com/cloud/bitbucket/rest/api-group-branch-restrictions/)
- [Repository permissions (permissions-config)](https://developer.atlassian.com/cloud/bitbucket/new-repo-permission-apis/)

## License

MIT

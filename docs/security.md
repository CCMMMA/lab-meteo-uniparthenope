# Security

lab.meteo@uniparthenope is a single-host service for a university laboratory, not a hardened multi-tenant cloud.
This page states the trust boundaries, the controls in place, and what must be added before
internet-wide exposure.

## Trust boundaries

- **Hub container:** holds the Docker socket and can therefore control the host's Docker engine.
  Compromising the Hub is equivalent to root on the host. Only administrators should reach the
  host; keep the Hub image pinned and patched.
- **User containers:** run arbitrary user code as the unprivileged `jovyan` user, with no Docker
  socket, no capabilities, and no way to gain privileges.
- **Public gallery:** static files only; anonymous code runs in the visitor's browser sandbox.
- **Front proxy (`web`):** read-only, unprivileged Nginx container and the only published port; the
  Hub port is reachable only inside the Compose network.

## Read-only scientific data

Model archives, station data, curated products, and templates must never be modified from
lab.meteo@uniparthenope. The guarantee is layered:

1. DockerSpawner binds every shared source through `read_only_volumes` (`ro` bind mounts).
2. User containers start with `cap_drop: ALL` and `no-new-privileges`, so no process can remount
   a filesystem read-write or escalate through set-uid binaries.
3. `pre_spawn_hook` refuses to start a server if any shared destination would be writable or if
   an unexpected mount appears in the plan.
4. The platform dashboard performs a live audit of running user containers and reports any
   writable shared mount; the Hub's own inventory mounts are read-only too.
5. On the reference host the archives are owned by a different UID than `jovyan`, an additional
   but incidental barrier.

`scripts/test_permissions.sh`, run inside a user server, verifies every mount, the
no-new-privileges flag, and the empty capability set. `scripts/validate_repo.py` rejects a Compose
file that mounts a `LAB_*_HOST` path without `:ro`.

## Accounts and sessions

- Local accounts require administrator approval or host-side provisioning; open sign-up is off.
- Passwords: at least 12 characters, common passwords rejected, bcrypt-hashed, five failed attempts
  block the username for ten minutes.
- Academic SSO delegates authentication to the University identity provider (see
  [Identity and roles](identity-and-roles.md)); no password is stored.
- Session cookies are `SameSite=Lax`, `Secure` under HTTPS, and expire after
  `LAB_COOKIE_MAX_AGE_DAYS` (default 7).
- Hub pages are served without the `/hub/` prefix, so the front proxy re-scopes Hub cookies to `/`
  and strips the Hub login cookie (`jupyterhub-hub-login`) from every request forwarded to user
  servers and services. Code in a user's server therefore never sees a Hub session, preserving
  JupyterHub's isolation model; access to another user's server returns HTTP 403.
- The idle culler stops servers after `LAB_IDLE_TIMEOUT` seconds of inactivity.

## HTTP security headers

Hub pages send `Content-Security-Policy` (self-hosted resources only), `X-Content-Type-Options`,
`Referrer-Policy`, `Permissions-Policy`, and, with an HTTPS public URL, `Strict-Transport-Security`.
The gallery sends the same non-CSP headers.

## Transport security and phishing warnings

A login form served over HTTP from a raw IP address transmits passwords in clear text and can be
flagged by browsers as phishing. Branding cannot establish browser trust. Before public use:

1. assign a DNS name and certificate and put a maintained HTTPS reverse proxy in front;
2. set `LAB_PUBLIC_HOST=https://<name>` and bind the published port of the built-in `web`
   proxy to localhost (`LAB_BIND_ADDRESS=127.0.0.1`) so only the HTTPS proxy is exposed;
3. prefer academic SSO to local passwords.

The direct `http://IP:port` endpoint is for acceptance testing on a trusted network.

## Further hardening before wide exposure

1. Restrict network ingress and user-container egress.
2. Add monitoring, centralised log retention, backups, image vulnerability scanning, and an upgrade
   policy.
3. Replace raw Docker-socket access with a socket proxy or an orchestrator.

## Secrets

The cookie secret is generated in the persistent Hub volume. OAuth client secrets and generated
initial passwords live in untracked files (`.env`, `.secrets/`) with mode 600. Never commit them,
place them in notebooks, or pass passwords as command-line arguments. Report vulnerabilities
privately to the repository owner.

## Colab-style imports and uploads

- `/github/…` fetches only `https://raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>`, built
  from validated components (no `..`, no hidden names, `.ipynb` only) without following redirects,
  so the route cannot be used to reach internal hosts (server-side request forgery). `/open?url=`
  accepts only `github.com` and `raw.githubusercontent.com` links.
- Imported and uploaded files must be JSON notebooks in format 4 or later and at most 25 MB.
- The Hub writes into a user's server with a token that it creates for that request only, scoped to
  `access:servers!user=<name>`, valid for at most five minutes, and deleted when the request ends;
  it never reuses a user's session or reaches another user's server.
- Imported notebooks are untrusted code. Notebook output is not trusted until the user runs it,
  and code runs only when the user executes it, inside that user's unprivileged container.
- Each creation, import, upload, and runtime restart or deletion is written to the audit log.

## Anonymous notebooks and AI demonstrations

The gallery's notebooks run in the visitor's browser and can reach only public, CORS-enabled
services such as the meteo API. They have no access to the host data mounts. The AI notebooks are
transparent teaching baselines: they send no notebook content to any AI provider, and their outputs
must not be treated as official forecasts, warnings, navigation advice, or control signals.

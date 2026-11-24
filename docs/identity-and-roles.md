# Identity, roles, and administration

## Choosing an authenticator

`LAB_AUTHENTICATOR` selects how people sign in. Only one method is active at a time.

| Value | Identity provider | Who can sign in |
|---|---|---|
| `native` (default) | Local accounts stored in the Hub database (bcrypt hashes) | Accounts approved by an administrator or created with `manage_users` |
| `azuread` | Microsoft Entra ID (university Microsoft 365 tenant) | Members of the configured tenant |
| `google` | Google Workspace for Education | Accounts of the configured hosted domains |

Single sign-on needs a stable HTTPS name because identity providers only redirect to registered
HTTPS callback URLs. Set `LAB_PUBLIC_HOST=https://<name>`; the callback is
`https://<name>/oauth_callback`.

### Microsoft Entra ID

1. In the university tenant, register an application of type *Web* with redirect URI
   `https://<name>/oauth_callback`, and create a client secret.
2. Configure:

   ```bash
   LAB_AUTHENTICATOR=azuread
   LAB_OAUTH_TENANT_ID=<tenant GUID>
   LAB_OAUTH_CLIENT_ID=<application ID>
   LAB_OAUTH_CLIENT_SECRET=<secret>
   LAB_OAUTH_USERNAME_CLAIM=upn      # or preferred_username / email
   LAB_ADMIN_USERS=<admin UPN>
   ```

`common`, `organizations`, and `consumers` are rejected: the tenant must be the university's.

### Google Workspace for Education

1. In Google Cloud, create an OAuth client of type *Web application* with the redirect URI above.
2. Configure `LAB_AUTHENTICATOR=google`, `LAB_OAUTH_CLIENT_ID`, `LAB_OAUTH_CLIENT_SECRET`, and
   `LAB_OAUTH_HOSTED_DOMAINS=<domain>[,<domain>]`. Sign-in is refused for other domains.

With SSO, every member of the tenant or domain may sign in unless `LAB_ALLOWED_USERS` lists the
permitted usernames or `LAB_OAUTH_ALLOW_ALL=false`. Keep secrets in the untracked `.env` file.
Switching authenticator changes usernames, and therefore workspace volume names; plan a migration
before switching a populated deployment.

## Local accounts

Self-service sign-up is disabled by default. Provision accounts from the host; the password is read
from standard input so that it never appears in process lists or shell history:

```bash
read -rs PASSWORD
printf '%s\n' "$PASSWORD" | docker compose exec -T jupyterhub \
  python -m lab_ext.manage_users create alice --role researcher
docker compose exec -T jupyterhub python -m lab_ext.manage_users list
```

`--update` resets an existing password. Passwords need at least 12 characters; NativeAuthenticator
blocks a username for ten minutes after five failed attempts. Users change their own password at
`/change-password`. If `LAB_ENABLE_SIGNUP=true`, requests appear under *Administration →
Approve sign-ups*; keep `LAB_OPEN_SIGNUP=false` on any reachable deployment.

## Roles

| Role | How it is granted | Effect |
|---|---|---|
| Administrator | `LAB_ADMIN_USERS`, or the *admin* checkbox in `/admin` | Full control, platform dashboard changes |
| Instructor | group `instructors` | Read-only dashboard and user list; start/stop servers of group `students` |
| Researcher | group `researchers` | Large resource tier |
| Student | group `students` | Small resource tier |
| User | approved account without a role group | Standard tier |

Administrators assign roles on the platform dashboard (`/dashboard#users`); changes apply at
the next server start. Groups can also be seeded at start-up with `LAB_STUDENTS`,
`LAB_RESEARCHERS`, and `LAB_INSTRUCTORS` (comma-separated usernames); seeding adds members but
never removes them. Instructors receive JupyterHub's `admin-ui` scope only to read; they cannot
access other users' notebooks.

## Administration pages

| Page | Who | Purpose |
|---|---|---|
| `/dashboard` | administrators (change), instructors (view) | Accounts and roles, data-mount audit, archive freshness, privacy requests, orphaned workspaces, security posture |
| `/admin` | administrators | JupyterHub control panel: add/delete users, admin flag, groups, start/stop servers |
| `/authorize` | administrators, local accounts only | Approve or revoke sign-up requests |
| `/account` | every user | Personal data, JSON export, data-protection requests |

Every change made from the platform dashboard is written to the Hub log with the `lab.meteo.audit`
logger (role changes, erasures, request decisions).

# Privacy and GDPR

This page records how lab.meteo@uniparthenope implements Regulation (EU) 2016/679 (GDPR) and the ePrivacy cookie
rules. The user-facing notice is served at `/privacy`; this document is for operators.
Legal review by the University's Data Protection Officer remains necessary before production use.

## Processing inventory (Art. 30 input)

| Category | Where it is stored | Retention |
|---|---|---|
| Username, role, groups, creation and last-activity times | Hub SQLite database (`jupyterhub-data`) | While the account exists |
| Password hash (local accounts) | Hub database, bcrypt | Deleted with the account |
| Workspace files | Volume `<prefix>-user-<name>` | Until the user deletes them or the account is erased |
| Data-subject request register | `jupyterhub-data/wxhub_privacy_requests.json` (mode 600) | Kept as evidence of compliance |
| Container logs (IP address, path, time) | Docker `json-file` logs, rotated at 10 MB × 5 | Bounded by rotation |

Lawful basis: Art. 6(1)(e), research and teaching tasks carried out in the public interest by the
University. No special categories of data are needed; users are told not to store them.

## Implemented controls

- **Minimisation (Art. 5(1)(c)):** no e-mail at sign-up, no analytics, no third-party resources on
  Hub pages, no tracking cookies.
- **Storage limitation (Art. 5(1)(e)):** idle culling, account review after
  `WXHUB_RETENTION_DAYS`, erasure of accounts and orphaned workspace volumes.
- **Transparency (Arts. 12–14):** privacy notice linked from every page and from sign-in.
- **Access and portability (Arts. 15, 20):** `/account` shows the stored data and
  exports it as JSON; workspace files are downloadable from JupyterLab.
- **Rectification, erasure, restriction (Arts. 16–18):** users submit requests on *My data*;
  administrators handle them on the dashboard within one month (Art. 12(3)).
- **Security (Art. 32):** approval-gated accounts, login throttling, hardened containers,
  read-only shared data, security headers, HTTPS readiness, audit logging.

## Cookies

Only strictly necessary cookies are set, which are exempt from consent under Art. 5(3) of
Directive 2002/58/EC: `jupyterhub-hub-login`, `jupyterhub-session-id`, `jupyterhub-user-<name>`
(session and routing, at most `WXHUB_COOKIE_MAX_AGE_DAYS`), and `_xsrf` (forgery protection). The
banner is therefore informational. Local storage keeps the theme choice and the notice
acknowledgement. Cookies are `SameSite=Lax` and become `Secure` when `WXHUB_PUBLIC_HOST` uses HTTPS.

## Public gallery

Notebook content and uploads stay in the visitor's browser. The browser loads the Pyodide runtime
from the jsDelivr CDN (the JupyterLite default) and may fetch packages from PyPI; both receive the
visitor's IP address. To remove these transfers, self-host Pyodide by configuring `pyodideUrl` in
`demos/jupyter-lite.json` and bundling the runtime in the image.

## Handling an erasure request

1. Open *Administration → Platform dashboard → Privacy requests*.
2. Verify the requester's identity through an institutional channel when in doubt.
3. Type the username and select **Erase**. The Hub stops the server, deletes the account (including
   the local password hash), deletes the workspace volume, and closes the user's open requests.
4. Erasure is irreversible. Backups follow their own retention; record the request date so that
   restored backups are re-purged.

Accounts deleted directly in `/admin` leave their volume behind; the dashboard lists such
volumes under *Orphaned workspaces* so the erasure can be completed.

## Configuration

The notice names the University of Naples “Parthenope” as controller and, by default, the contacts
published on the University privacy page (https://www.uniparthenope.it/Portale-Ateneo/privacy,
checked 23 November 2026): the Privacy Office (`privacy@uniparthenope.it`, PEC
`privacy@pec.uniparthenope.it`) and the Data Protection Officer (`dpo.privacy@uniparthenope.it`).
The service operator is reachable at `meteo@uniparthenope.it`. Override them with
`WXHUB_PRIVACY_CONTROLLER`, `WXHUB_PRIVACY_CONTACT`, and `WXHUB_DPO_CONTACT`, and re-check them
whenever the University updates its page. The notice should be reviewed by the DPO.

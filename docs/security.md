# Security

wxhub is a laboratory pilot, not a hardened multi-tenant service. Its defaults include plain HTTP,
the Docker socket in the Hub, controlled local accounts constrained by a static allow-list, no idle
culler, and local SQLite/volume storage. Public self-signup is disabled by default and can be
enabled temporarily with `WXHUB_ENABLE_SIGNUP=true` for controlled, administrator-approved
provisioning. Setting `WXHUB_OPEN_SIGNUP=true` additionally allows new accounts to log in without
approval and should not be used on an internet-facing deployment.

Before public exposure:

1. Add a maintained TLS reverse proxy.
2. Replace open signup with institutional authentication or controlled provisioning.
3. Minimize administrators and protect API tokens as secrets.
4. Restrict network ingress and egress.
5. Add monitoring, log retention, backups, vulnerability scanning, and an upgrade policy.
6. Evaluate a socket proxy or an orchestrator that does not grant unrestricted Docker access.

## Anonymous notebook execution

Anonymous access under `/services/demos/` is a JupyterLite application. It intentionally exposes an
editable notebook and file interface, but its Python kernel is WebAssembly running in the visitor's
browser. Browser-local storage holds changes and uploads. The static Nginx service has no notebook
kernel, Docker socket, secrets, scientific-data mounts, or writable content directory.

Browser code remains subject to the browser security model and can reach public CORS-enabled
services, including the meteo API model and live weather-report endpoints. The public notebooks do
not mount or expose the host model and sensor directories; those mounts remain exclusive to
authenticated user containers and read-only. Never place credentials or non-public datasets in the static
JupyterLite image. This isolation does not apply to authenticated JupyterHub user containers, which
remain server-side and retain their existing resource and read-only data controls.

The live-instrument notebooks display public observations returned by the upstream API. They handle
timeouts as availability failures and do not fall back to host CSV files, alternate networks, or
cached private observations.

## Browser phishing warnings

Branding makes the service identity clear to people but does not establish browser trust. A login
form served from a raw IP address over HTTP can be classified as phishing because it has no trusted
DNS identity, no TLS certificate, and transmits passwords without encryption. Do not bypass or ask
users to suppress that warning.

The production remedy is to assign a trusted DNS name, obtain a certificate for that name, and put
a maintained HTTPS reverse proxy in front of JupyterHub. Set `WXHUB_PUBLIC_HOST` to the resulting
`https://` URL, redirect HTTP to HTTPS, and expose only the reverse proxy publicly. The direct
`http://IP:port` endpoint is suitable only for isolated acceptance testing.

The cookie secret is generated in the persistent Hub volume. Never commit it. Pass external
credentials through an approved runtime secret mechanism, not notebooks, Compose files, or Git.
Report vulnerabilities privately to the repository owner without publishing credentials or user data.

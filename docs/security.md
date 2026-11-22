# Security

wxhub is a laboratory pilot, not a hardened multi-tenant service. Its defaults include plain HTTP,
the Docker socket in the Hub, signup constrained by a static allow-list, no idle culler, and local
SQLite/volume storage.

Before public exposure:

1. Add a maintained TLS reverse proxy.
2. Replace open signup with institutional authentication or controlled provisioning.
3. Minimize administrators and protect API tokens as secrets.
4. Restrict network ingress and egress.
5. Add monitoring, log retention, backups, vulnerability scanning, and an upgrade policy.
6. Evaluate a socket proxy or an orchestrator that does not grant unrestricted Docker access.

The cookie secret is generated in the persistent Hub volume. Never commit it. Pass external
credentials through an approved runtime secret mechanism, not notebooks, Compose files, or Git.
Report vulnerabilities privately to the repository owner without publishing credentials or user data.

# Changelog

## 0.1.0 — 2026-11-02

- Initial amd64 Home Assistant package: DokuWiki 2026-07-14c Mort, Bootstrap3 and
  43 additional plugins, with verified source commits and archive checksums.
- Nginx, PHP-FPM 8.5.4, SQLite and image-processing dependencies; authenticated
  X-Accel media delivery, byte ranges and MCP support.
- Separate HTTP port, no ingress, and persistent `/share/dokuwiki` content/config.
- Clean setup through DokuWiki's installer, generic branding and no development data.
- Release-managed code with editable owner configuration; core updater disabled.
- Approve's Mort database migration fix pinned to commit `e4299f1`.
- One Dockerfile for Home Assistant and local Compose; five packaging tests and
  34 container checks pass, including container replacement and stopped restore.

Home Assistant OS/Supervisor installation is the remaining platform check.

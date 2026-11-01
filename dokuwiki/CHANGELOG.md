# Changelog

## 0.1.3 — 2026-11-02

- Set the wiki base directory explicitly so cached Iconify responses use the
  correct internal X-Accel-Redirect path instead of returning a missing page.
- Keep edit/preview request bodies up to 1 MB in memory. Larger uploads can
  still use Nginx temporary files without affecting the upload limit.
- Restore FastCGI response buffering to coalesce early template output with
  rendered content, reducing the empty-template flash during previews.
- Add regression checks for fresh/cached icons and full syntax-page previews.

## 0.1.2 — 2026-11-02

- Upgrade PHP-FPM from 8.5.4 to 8.5.12 and pin the updated official image digest.
  This addresses PHP2Shell (CVE-2026-109618 and CVE-2026-109619).
- Reject older PHP runtimes during the image build and check the running version
  in the container smoke test.
- Existing wiki content, accounts, settings and approval databases remain on Share.
  Install this update and restart the add-on to replace the old PHP workers.

Security references: [PHP 8.5.12 changelog](https://www.php.net/ChangeLog-8.php#8.5.12),
[OOM advisory](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w),
[stale-state advisory](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp).

## 0.1.1 — 2026-11-02

- Include the maintained ACLPlusRegex rules as first-install defaults, with
  BEFORE mode and anonymous processing enabled. Existing ACL settings persist.

- Move Vanilla Pro wide-screen spacing, display-equation scrolling and Wrap border
  styling into the Bootstrap3 template; no custom user stylesheet is seeded.
- Scope navbar spacing to Vanilla Pro and equation scrolling to display math.

Existing installations retain their own `conf/userstyle.css`. If an early local
preview contains the previous stylesheet, remove its migrated/obsolete rules once
after updating; an add-on update does not overwrite user customisations.

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

# Changelog

## 0.1.8 — 2026-11-04

- Add `@APPROVE_NAME@` to show the approving user's current full name. It uses
  the stored username to look up the authentication backend; no database change
  is needed. If the name or account is unavailable, it falls back to the username.

## 0.1.7 — 2026-11-04

- Treat 400×400 as the maximum avatar upload size. Smaller photos are no longer
  enlarged; centre-cropping to a square and PNG conversion are retained.
- Update the profile photo help text to explain the size limit.

Existing avatars are unchanged. Re-upload the original photo to replace an avatar
that was enlarged by an earlier release.

## 0.1.6 — 2026-11-04

- Add the Add New Page plugin.
- Bundle DW2PDF, disabled by default on fresh installations. Existing installations
  retain their plugin settings; disable DW2PDF in Extension Manager if unwanted.
- Remove Wrap; convert existing `<WRAP>`/`<wrap>` content to BootsWrapper's
  lowercase `<wrapper>` syntax. Historical revisions using Wrap will no longer
  render those blocks.
- Support nested block wrappers and `<wrapper inline="true">` for inline spans
  that stay within the surrounding paragraph. Uppercase `<WRAPPER>` is no longer
  supported; existing inline uses of lowercase wrappers need `inline="true"`.
- Add plain DataTables with merged cells, stripe and border controls, custom
  border/header colours and responsive horizontal overflow on small screens.
- Fix Bootstrap3 table handling so mixed heading cells and vertical merges are
  preserved; respect per-table styling options.
- Save uploaded profile photos at 400×400, with appropriately sized cached
  thumbnails for navigation, contributors and tooltips. Existing photos are kept.
- Show `TBD` for approval variables on unapproved draft revisions; approved
  revisions keep their approval metadata.

Starter content/settings apply only to new installations. Existing pages, media,
accounts, approval databases and configuration are never overwritten.

## 0.1.5 — 2026-11-03

- Fix Highlight.js warnings caused by Mort's copy button inside code blocks;
  retain one copy control and preserve literal HTML/entities when copying.
- Keep the editor full-width below the draft autosave status.
- Keep CodeMirror settings and theme choices on-screen on mobile, with a
  visible Close settings control, outside-tap dismissal and Escape support.
- Keep the template's normal JavaScript bundling; no automatic cache-refresh
  mechanism is added. Purge generated JavaScript and reload if stale assets persist.

## 0.1.4 — 2026-11-03

- Bundle Font Awesome Free 7.3.1 and the updated Icons picker: collection search,
  fixed-width control, improved sizing/layout and explicit `fa>` insertion.
  Old Font Awesome icon names are not retained as compatibility aliases.
- Refresh cached toolbar JavaScript when the Icons toolbar definition changes,
  and preserve SVG dimensions and collection cache dependencies.
- Add Ctrl+/ (Cmd+/ on macOS) comment toggling in CodeMirror Extended Syntax.
  Wiki comments use the bundled Comment Syntax plugin; code blocks use their
  language's comment syntax.

- Include the editable custom 404 page in starter content for new installations.
  Existing installations can copy it manually to `data/pages/404.txt`; updates
  continue to preserve all existing wiki content.

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

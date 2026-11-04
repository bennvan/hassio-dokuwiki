# DokuWiki

## First setup

Start the add-on and open its web interface on port 8080 (or the port selected in
its Network settings). Complete `/install.php` to choose a wiki name,
administrator and access policy. The installer is blocked after setup.

This package starts with DokuWiki branding and clean content. Configure the wiki
in its administration area. To change the logo/favicon, upload `wiki:logo.png`
(or SVG) and `wiki:favicon.ico` using the media manager. Uploads allow files up to
32 MiB. Remote API/MCP access must be explicitly enabled and configured by an
administrator.

## HTTPS and a domain name

The add-on serves HTTP directly; ingress is disabled. Point your reverse proxy at
the Home Assistant machine's mapped wiki port. Use a dedicated hostname such as
`wiki.example.com`, with the wiki at `/` rather than a subdirectory.

Terminate HTTPS at the proxy. Forward the original `Host` header (including any
non-default public port), `X-Forwarded-Proto`, and an accurate client IP chain.
Configure DokuWiki's `trustedproxies` setting for the proxy address actually seen
by the container. DokuWiki's upstream defaults trust private network ranges;
narrow this to your proxy where appropriate. For example, in persistent
`/share/dokuwiki/conf/local.php`:

```php
$conf['trustedproxies'] = ['192.168.1.10'];
```

Use your actual proxy address/CIDR. For direct HTTP access with no proxy, an empty
array disables forwarded-header trust. The proxy must replace client-supplied
forwarding headers. Match its upload/request limit to at least the add-on's 40 MiB
request limit when using 32 MiB uploads.

## Namespace permissions

ACLPlusRegex is enabled with the maintained rules in
`/share/dokuwiki/conf/aclplusregex.conf`. It runs BEFORE core ACL checks and also
handles anonymous visitors. Matching rules take precedence over the base policy
selected in the installer: public/wiki namespaces and public user media are
readable anonymously; non-guest users can manage their own namespace; guests are
excluded from private user namespaces. Group-based namespace rules are included.

Review the complete rules file before relying on a closed-wiki installer policy.
Both this file and the plugin settings remain editable and persist on updates.
The defaults are seeded only for a new installation; existing installations are
not automatically given different access permissions.

## Custom 404 page

New installations include an editable `404` wiki page used by the NotFound plugin.
Edit that page through the wiki to customise the missing-page message. The
Bootstrap3 template shows its Create Page button when the visitor can create the
requested page.

For an existing installation created without this page, copy
`dokuwiki/seeds/data/pages/404.txt` from this repository to
`/share/dokuwiki/data/pages/404.txt` once, if that page does not already exist.
Updates do not add or overwrite pages in existing installations.

## PDF templates and fonts

Enable DW2PDF in Extension Manager if it is disabled. The bundled fork discovers
custom templates under persistent storage:

```text
/share/dokuwiki/conf/dw2pdf/tpl/mytemplate/
  style.css
  header.html
  footer.html
  fonts.json
  fonts/Regular.ttf
```

The header/footer files are optional; `header_odd.html`, `header_even.html` and
corresponding footer files can provide alternating layouts. A custom directory
with the same name as a bundled template overrides it. With multiple templates,
the normal PDF export link offers a chooser. Explicit URLs such as
`?do=export_pdf&tpl=mytemplate` select one directly.

To register a font, use a `fonts.json` file such as:

```json
{"documentfont": {"R": "fonts/Regular.ttf"}}
```

Add `B`, `I` and `BI` entries for bold, italic and bold italic TrueType files.
Select the registered family in `style.css`, for example
`body { font-family: documentfont; }`. Font files must be readable `.ttf` files
inside the template directory and licensed for your intended use. Browser web
fonts are not automatically copied into PDFs. Custom templates, fonts and assets
stay in `conf/` across updates and are included when backing up Share.

## History access with DenyActions

Fresh installs seed `diff,revisions,recent` as denied actions for readers.
Existing installations keep their current configuration. To enable this policy,
set the DenyActions **denyactions** setting to `diff,revisions,recent`,
**denyrev** to off, and **denystyle** to `msg` in DokuWiki configuration.
Direct revision links remain available because Approve uses them to show approved
revisions. This setting does not restrict revision URLs to approved revisions.

## Updates and storage

The maintainer ships core, template and plugin updates together. Packaged code is
read-only to PHP: in-wiki plugin installation/update cannot complete, though
settings and enabled states remain editable. The core upgrade plugin is disabled.

All wiki content and settings live under `/share/dokuwiki/{data,conf}`. Rebuilds
and updates retain them and do not reseed existing settings. Share also survives
add-on removal. Do not delete these directories to troubleshoot a failed startup.
An old wiki copied into this location requires a reviewed migration; it is not
automatically imported.

## Backups

Include the **Share folder and this add-on** in Home Assistant backups. Stop the
add-on before backing up, then restart it, to keep SQLite databases and wiki files
consistent. An add-on-only backup does not include the shared wiki data, and cold
backup mode alone does not coordinate a separately backed-up Share folder.

Restore the Share folder and add-on together. Local Docker tests cover restoring
stopped wiki storage into a new volume; Home Assistant Supervisor backup/restore
still needs platform verification for this initial release.

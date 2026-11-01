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

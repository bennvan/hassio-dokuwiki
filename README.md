# DokuWiki for Home Assistant

DokuWiki Mort with a maintained Bootstrap3 template and 43 additional plugins,
packaged as a Home Assistant add-on for amd64 PCs/VMs. Version **0.1.0** builds and
passes the local Docker smoke tests. Installation under Home Assistant Supervisor
still needs its first platform test.

The runtime uses Nginx, PHP-FPM 8.5.4, SQLite and X-Accel-Redirect. It serves HTTP
on a separate port (8080 by default); it does not use Home Assistant ingress.

## Install on Home Assistant

After this repository has been published:

1. Add `https://github.com/bennvan/hassio-dokuwiki` to the add-on store's repositories.
2. Install DokuWiki. Home Assistant builds the image from the pinned sources.
3. Start it and open the web interface on port 8080 (or your chosen mapped port).
4. Complete `/install.php` to choose the wiki name, administrator and access policy.

The installer is blocked after setup. No development accounts, pages, media,
approval database or API credentials are included. The initial logo and favicon
are DokuWiki's; upload `wiki:logo.png` (or SVG) and `wiki:favicon.ico` to change them.
See [the add-on documentation](dokuwiki/DOCS.md) for storage and reverse proxies.

## Run the same image locally

Docker Engine with Compose is required. From this repository:

```sh
docker compose up -d --build
```

Open <http://localhost:8081/install.php>. This uses its own named Docker volume;
it does not mount or modify the development wiki. `docker compose down` stops and
removes the container while retaining this volume. Adding `--volumes` deletes the
local test wiki, so use that only when intentionally starting fresh.

Both Compose and Home Assistant use `dokuwiki/Dockerfile`. This is a release test
environment; it does not yet mount editable plugin repositories for live coding.
The existing PHP development server workflow can continue unchanged.

## Persistent storage and backups

```text
/share/dokuwiki/
  conf/   settings, accounts, ACLs, styles and configuration overrides
  data/   pages, media, revisions, metadata, indexes, caches and plugin databases
```

First startup creates a clean wiki once. Updates reuse these directories without
overwriting local settings. Shipped core defaults come from the new image; links
in `conf/` expose those defaults to plugins that read them directly. An existing,
unrecognised storage directory stops startup instead of being silently imported.
Importing an old wiki needs a separate migration review.

Back up **both the Share folder and the add-on**. Stop the add-on before taking
the backup, then restart it, so SQLite and wiki files are copied consistently.
`backup: cold` alone does not coordinate copying the separately backed-up Share
folder. Restore both parts. Container replacement or add-on removal leaves the
Share folder in place; an add-on-only backup does not contain the wiki data.

## Code and configuration policy

PHP can write content and configuration but cannot modify packaged core, template
or plugin files. The extension manager can enable/disable plugins; installation
and code updates cannot complete because those paths are read-only to PHP. The
core upgrade plugin is disabled. Code updates are shipped as add-on releases.

Initial settings are a reviewed, generic subset in `dokuwiki/seeds/`, not a copy
of development `conf/`. Personal interwiki links, custom access rules and other
site-specific settings are not carried over. Owners manage their settings through
DokuWiki after setup. PHP allows 32 MiB per uploaded file; Nginx accepts 40 MiB
requests to leave room for form data.

The PHP build checks SQLite3/PDO SQLite, GD with JPEG/PNG/WebP, EXIF, ZIP, cURL,
mbstring, DOM/XML, JSON, OpenSSL and related standard extensions. MCP is included;
its remote API access is disabled until the owner enables and configures it.
Plugins that use external services (for example the diagram editor) still need
those services; pinning packaged code does not make the wiki fully offline.

## Maintaining releases

Core and plugin code is downloaded at build time. This repository tracks source
commits, archive checksums, build scripts and defaults, rather than duplicate Git
repositories or installed source trees. The 44 external component archives have
been matched against the tested development code. The manifest is
`dokuwiki/sources.inventory.json`; `dokuwiki/source-review.json` records the initial
review. Bundled components retain their licences and attribution in the image.

1. Update and test the development wiki, committing and pushing your own plugins
   in their respective repositories as usual.
2. Refresh the source inventory using the development wiki's actual path:

   ```sh
   python3 dokuwiki/tools/sources.py inventory --wiki /path/to/development/dokuwiki
   ```

   Its location does not need any particular relationship to this repository.
   Unchanged verified entries retain their archive pins. Changed entries require
   review and a downloadable archive pinned to the exact tested commit, its SHA256
   and installed tree hash. A floating `master`/`latest` download is not a release pin.
3. Review the manifest diff. Set verified archive fields only after matching the
   downloaded archive against the installed code. For a core update, also update
   the core constants/version check in `sources.py`. For a PHP update, change its
   version and digest in the Dockerfile, then rebuild and test.
4. Run the checks below, build the image, and run the disposable smoke test.
5. Bump the version in `dokuwiki/config.yaml`, the Dockerfile label and
   `compose.yaml`; add release notes in `dokuwiki/CHANGELOG.md` and commit/push.
   Home Assistant discovers the version change and builds it during the update.

```sh
python3 -B -m unittest discover -s tests -v
python3 dokuwiki/tools/sources.py check-release
docker compose build
python3 -B tests/smoke.py --image hassio-dokuwiki:0.1.0
```

The smoke test creates synthetic accounts/content in temporary Docker volumes and
removes them afterwards. It checks setup, editing, avatar resizing, uploads,
private media ACLs, byte ranges, Approve, authenticated MCP, proxy handling,
CSS/JavaScript compilation, container replacement and stopped backup/restore.
It does not replace a Home Assistant installation/update test or visual testing
of every plugin feature.

Base images are digest-pinned. OS packages receive the Debian repository's current
updates at build time, so this is not a claim of bit-for-bit identical image
rebuilds. Changing an upstream archive's bytes causes verification to fail rather
than silently installing different code.

Optional inspection without Docker:

```sh
python3 dokuwiki/tools/sources.py assemble --archive-cache dokuwiki/.cache --output dokuwiki/.build/review-new
```

The output must be a new directory. Generated `.build/`, `.cache/` and `.preview/`
files are ignored by Git; they must not be committed. `prepare` can also create a
local source preview, but release builds always use verified remote archives.

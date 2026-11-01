#!/usr/bin/env python3
"""Inventory installed code and prepare an isolated, unpublished local preview.

The development wiki is read-only. Its conf/ and data/ are never imported.
This tool does not resolve floating upstream URLs into guessed release versions.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ADDON = Path(__file__).resolve().parents[1]
CORE_VERSION = '2026-07-14c'
CORE_SHA256 = '7e9b4dcb5ecb91a57f71b9b77dcec7bcf929959881464796611349ed1d183176'
CORE_URL = ('https://github.com/dokuwiki/dokuwiki/releases/download/'
            f'release-{CORE_VERSION}/dokuwiki-{CORE_VERSION}.tgz')
CORE_PLUGINS = set('acl authad authldap authpdo authplain config extension info '
                   'logviewer popularity revert safefnrecode styling usermanager'.split())
SKIP_DIRS = {'.git', '.github', '.idea', '.vscode', '__pycache__', '_test', 'tests'}
SKIP_FILES = {'manager.dat', 'AGENTS.md', '.DS_Store', '.gitattributes', '.gitignore',
              '.travis.yml', 'ISSUE_TEMPLATE.md'}
RUNTIME_SUFFIXES = {'.sqlite', '.sqlite3', '.db', '.log', '.bak'}


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def code_files(root):
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts) or path.name in SKIP_FILES:
            continue
        if path.is_symlink() and (not path.is_file() or root.resolve() not in path.resolve().parents):
            raise ValueError(f'Review external/broken/directory symlink before packaging: {path}')
        if not path.is_file():
            continue
        if path.name.startswith('.env') or path.suffix in RUNTIME_SUFFIXES:
            raise ValueError(f'Review unexpected runtime/secret file: {path}')
        yield path, rel


def tree_hash(root):
    digest = hashlib.sha256()
    for path, rel in code_files(root):
        digest.update(rel.as_posix().encode() + b'\0' + sha256(path).encode() + b'\n')
    return digest.hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def inventory(wiki):
    if (wiki / 'VERSION').read_text().strip() != '2026-07-14c "Mort"':
        raise ValueError('Update the pinned core version and checksum before packaging another version.')
    components = []
    for category in ('plugins', 'tpl'):
        for path in sorted((wiki / 'lib' / category).iterdir()):
            if not path.is_dir():
                continue
            if category == 'plugins' and path.name in CORE_PLUGINS:
                continue
            if category == 'tpl' and path.name == 'dokuwiki':
                continue
            item = {'path': path.relative_to(wiki).as_posix(), 'tree_sha256': tree_hash(path)}
            if (path / '.git').exists():
                origin = git(path, 'remote', 'get-url', 'origin')
                origin = re.sub(r'^git@github.com:', 'https://github.com/', origin)
                if not re.fullmatch(r'https://github.com/[\w.-]+/[\w.-]+(?:\.git)?', origin):
                    raise ValueError(f'Review repository URL for {path.name}')
                item.update(repository=origin, commit=git(path, 'rev-parse', 'HEAD'),
                            worktree_clean=not bool(git(path, 'status', '--porcelain')),
                            status='commit-recorded; archive-verification-pending')
            else:
                manager = path / 'manager.dat'
                if manager.exists():
                    match = re.search(r'^downloadurl=(https?://\S+)$', manager.read_text(), re.M)
                    if match:
                        item['source_hint'] = match[1]
                item['status'] = 'installed-snapshot; upstream-version-unresolved'
            components.append(item)
    return {'schema': 1, 'sources_verified': False,
            'core': {'version': CORE_VERSION, 'url': CORE_URL, 'sha256': CORE_SHA256},
            'components': components}


def extract_core(archive, output):
    if sha256(archive) != CORE_SHA256:
        raise ValueError('Core archive checksum mismatch')
    prefix = f'dokuwiki-{CORE_VERSION}/'
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            if not member.name.startswith(prefix):
                if member.name.rstrip('/') == prefix.rstrip('/'):
                    continue
                raise ValueError('Unexpected archive root')
            rel = Path(member.name[len(prefix):])
            if rel.is_absolute() or '..' in rel.parts or member.issym() or member.islnk():
                raise ValueError('Unsafe archive member')
            destination = output / rel
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                destination.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, destination.open('wb') as target:
                    shutil.copyfileobj(source, target)
                destination.chmod(0o755 if member.mode & 0o111 else 0o644)
            else:
                raise ValueError('Unsupported archive member')


def prepare(wiki, archive, output):
    # Never delete/merge an existing wiki, or write anywhere within the source.
    if output.exists() or output == wiki or wiki in output.parents or output in wiki.parents:
        raise ValueError('Output must be a NEW directory outside the development wiki')
    expected = json.loads((ADDON / 'sources.inventory.json').read_text())
    current = inventory(wiki)
    def identity(data):
        return [tuple(item.get(key) for key in ('path', 'tree_sha256', 'worktree_clean'))
                for item in data['components']]
    if current['core'] != expected['core'] or identity(current) != identity(expected):
        raise ValueError('Installed code changed. Review and refresh the inventory first.')
    output.mkdir(parents=True)
    extract_core(archive, output)
    for item in expected['components']:
        source = wiki / item['path']
        target = output / item['path']
        if target.exists():
            raise ValueError(f'Unexpected core overlap: {target}')
        for path, rel in code_files(source):
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
            dest.chmod(0o755 if path.stat().st_mode & 0o111 else 0o644)
    finalize(output)
    print(f'Prepared clean local preview: {output}')
    print('Local source snapshot only; use assemble for a release build.')


def finalize(output):
    # Use core and reviewed starter pages/media, never the development data.
    # Replace template-bundled branding in this generated tree, not the source repo.
    for name in ('logo.png', 'favicon.ico', 'apple-touch-icon.png'):
        shutil.copyfile(output / 'lib/tpl/dokuwiki/images' / name,
                        output / 'lib/tpl/bootstrap3/images' / name)
    shutil.copyfile(ADDON / 'seeds/install.conf', output / 'install.conf')
    shutil.copytree(ADDON / 'seeds/conf', output / 'conf', dirs_exist_ok=True)
    shutil.copytree(ADDON / 'seeds/data', output / 'data', dirs_exist_ok=True)
    (output / 'data/pages/start.txt').write_text(
        '====== Welcome to DokuWiki ======\n\n'
        'Your wiki is ready. Edit this page to get started.\n\n'
        '  * [[wiki:syntax|Formatting syntax]]\n'
        '  * [[playground:playground|Playground]]\n', encoding='utf-8')


def check_release(data):
    pending = [x['path'] for x in data['components']
               if not x.get('archive_sha256') or not x.get('archive_url')
               or x.get('worktree_clean') is False]
    if not data.get('sources_verified') or pending:
        raise ValueError('Source verification incomplete. Verify immutable downloadable sources for:\n'
                         + '\n'.join(pending))


def assemble(output, archive_cache=None):
    """Release builds fetch only reviewed, checksum-pinned source archives."""
    data = json.loads((ADDON / 'sources.inventory.json').read_text())
    check_release(data)
    if output.exists():
        raise ValueError('Output must not exist')
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp)
        def download(url, digest, name):
            if not url.startswith('https://'):
                raise ValueError('Source URL must use HTTPS')
            cached = archive_cache / digest if archive_cache else None
            if cached and cached.is_file():
                path = cached
            else:
                path = cache / name
                request = urllib.request.Request(url, headers={'User-Agent': 'hassio-dokuwiki-builder'})
                with urllib.request.urlopen(request, timeout=120) as response, path.open('wb') as target:
                    shutil.copyfileobj(response, target)
            if sha256(path) != digest:
                raise ValueError(f'Archive checksum mismatch: {name}')
            if archive_cache and path != cached:
                archive_cache.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, cached)
            return path
        core = download(data['core']['url'], data['core']['sha256'], 'core.tgz')
        output.mkdir(parents=True)
        extract_core(core, output)
        for index, item in enumerate(data['components']):
            archive = download(item['archive_url'], item['archive_sha256'], f'{index}.zip')
            rel = Path(item['path'])
            if len(rel.parts) != 3 or rel.parts[:2] not in [('lib', 'plugins'), ('lib', 'tpl')]:
                raise ValueError('Invalid component destination')
            target = output / rel
            if target.exists():
                raise ValueError('Unexpected core overlap')
            # Release source format is ZIP, with one archive root stripped.
            with zipfile.ZipFile(archive) as files:
                roots = {Path(x.filename).parts[0] for x in files.infolist()}
                if len(roots) != 1:
                    raise ValueError('Expected a single archive root')
                for member in files.infolist():
                    path = Path(member.filename)
                    if path.is_absolute() or '..' in path.parts:
                        raise ValueError('Unsafe archive member')
                    rel = Path(*path.parts[1:])
                    if member.is_dir() or any(x in SKIP_DIRS for x in rel.parts) or rel.name in SKIP_FILES:
                        continue
                    if item.get('languages') and len(rel.parts) > 1 and rel.parts[0] == 'lang' and rel.parts[1] not in item['languages']:
                        continue
                    dest = target / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if (member.external_attr >> 16) & 0o170000 == 0o120000:
                        link = Path(files.read(member).decode())
                        resolved = (dest.parent / link).resolve()
                        if link.is_absolute() or target.resolve() not in resolved.parents:
                            raise ValueError('External archive symlink')
                        dest.symlink_to(link)
                        continue
                    with files.open(member) as source, dest.open('wb') as target_file:
                        shutil.copyfileobj(source, target_file)
            if tree_hash(target) != item['tree_sha256']:
                raise ValueError(f'Archive differs from the tested installed code: {item["path"]}')
        finalize(output)
    print(f'Assembled verified sources: {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inventory', 'prepare', 'check-release', 'assemble'])
    parser.add_argument('--wiki', type=Path)
    parser.add_argument('--core-archive', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--archive-cache', type=Path)
    args = parser.parse_args()
    if args.command == 'inventory':
        if not args.wiki:
            parser.error('--wiki is required')
        data = inventory(args.wiki.resolve())
        target = ADDON / 'sources.inventory.json'
        if target.exists():
            previous = json.loads(target.read_text())
            old = {item['path']: item for item in previous['components']}
            for item in data['components']:
                prior = old.get(item['path'], {})
                if (item['tree_sha256'] == prior.get('tree_sha256')
                        and ('commit' not in item or item['commit'] == prior.get('commit'))
                        and item.get('worktree_clean', True)):
                    for key in ('archive_url', 'archive_sha256', 'repository', 'commit', 'languages', 'status'):
                        if key in prior:
                            item[key] = prior[key]
            data['sources_verified'] = all(item.get('archive_sha256') and item.get('archive_url')
                                           for item in data['components'])
        target.write_text(json.dumps(data, indent=2) + '\n')
        print(f'Recorded {len(data["components"])} external components in {target}')
    elif args.command == 'prepare':
        if not all((args.wiki, args.core_archive, args.output)):
            parser.error('--wiki, --core-archive and --output are required')
        prepare(args.wiki.resolve(), args.core_archive.resolve(), args.output.resolve())
    elif args.command == 'assemble':
        if not args.output:
            parser.error('--output is required')
        assemble(args.output.resolve(), args.archive_cache)
    else:
        data = json.loads((ADDON / 'sources.inventory.json').read_text())
        try:
            check_release(data)
        except ValueError as error:
            parser.exit(1, str(error) + '\n')
        print('Source archives verified. Container smoke tests are required before release.')


if __name__ == '__main__':
    main()

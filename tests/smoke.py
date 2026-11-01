#!/usr/bin/env python3
"""Exercise a built image using disposable containers/volumes and synthetic data."""
import argparse
import base64
import hashlib
import html
import http.client
import http.cookiejar
import json
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


def docker(*args, stdin=None):
    return subprocess.check_output(['docker', *args], input=stdin, stderr=subprocess.STDOUT).decode().strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', default='hassio-dokuwiki:0.1.2')
    args = parser.parse_args()
    name = 'dokuwiki-smoke-' + uuid.uuid4().hex[:10]
    volume = name + '-share'
    restored = name + '-restored'
    password = uuid.uuid4().hex
    class TrackRedirects(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            print('Redirect: ' + newurl, flush=True)
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(TrackRedirects(), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    anon = urllib.request.build_opener()
    base = ''
    checks = []
    last_body = b''

    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        checks.append(label)
        print('PASS ' + label, flush=True)

    def request(path, fields=None, raw=None, headers=None, anonymous=False):
        nonlocal last_body
        payload = urllib.parse.urlencode(fields).encode() if fields is not None else raw
        req = urllib.request.Request(base + path, data=payload, headers=headers or {})
        try:
            result = (anon if anonymous else opener).open(req, timeout=30)
        except urllib.error.HTTPError as result_error:
            result = result_error
        with result:
            last_body = result.read()
            return result.status, result.headers, last_body

    def php(code):
        script = '<?php define("DOKU_INC", "/var/www/html/"); require DOKU_INC."inc/init.php"; ' + code
        return docker('exec', '-i', '-u', 'www-data', name, 'php', stdin=script.encode())

    def token(body):
        match = re.search(r'name="sectok"[^>]*value="([^"]+)"', body.decode())
        if not match:
            raise AssertionError('CSRF token absent')
        return html.unescape(match.group(1))

    def multipart(path, fields, field, filename, content, mime):
        boundary = uuid.uuid4().hex
        parts = []
        for key, value in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n'.encode() + content + b'\r\n')
        parts.append(f'--{boundary}--\r\n'.encode())
        return request(path, raw=b''.join(parts), headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})

    def start(storage):
        nonlocal base
        docker('run', '-d', '--name', name, '-p', '127.0.0.1::8080', '--mount',
               f'type=volume,src={storage},dst=/share', args.image)
        port = json.loads(docker('inspect', name))[0]['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort']
        base = 'http://127.0.0.1:' + port
        for _ in range(60):
            try:
                if request('/healthz')[0] == 200:
                    return
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(0.25)
        raise AssertionError('Container did not become ready')

    def fingerprint():
        return json.loads(php('''$files = ['conf/local.php', 'conf/users.auth.php', 'conf/acl.auth.php', 'conf/aclplusregex.conf',
            'data/pages/release_test.txt', 'data/media/release-test.png'];
            $hashes = []; foreach ($files as $file) $hashes[$file] = hash_file('sha256', '/share/dokuwiki/'.$file);
            echo json_encode($hashes);'''))

    def approval():
        return json.loads(php('''$db=plugin_load('helper','approve_db')->getDB();
            echo json_encode($db->res2row($db->query('SELECT approved, version, minor_version FROM revision WHERE page=? AND current=1','release_test')));'''))

    try:
        start(volume)
        check(int(php('echo PHP_VERSION_ID;')) >= 80512, 'PHP runtime includes the PHP2Shell fixes')
        status, _, page = request('/')
        check(status == 200 and b'name="d[superuser]"' in page, 'fresh root opens installer')
        check(b'name="d[license]"' in page, 'installer reads shipped configuration')
        fields = {'submit': 'Save', 'l': 'en', 'd[title]': 'Release smoke wiki', 'd[acl]': '1',
                  'd[superuser]': 'releaseadmin', 'd[fullname]': 'Release Tester',
                  'd[email]': 'release@example.invalid', 'd[password]': password,
                  'd[confirm]': password, 'd[policy]': '1', 'd[allowreg]': '0', 'd[license]': 'cc-by-sa'}
        status, _, page = request('/install.php', fields=fields)
        check(status == 200 and b'successfully' in page.lower(), 'standard installer creates owner account')
        check(request('/install.php')[0] == 404, 'installer disabled after setup')
        status, _, page = request('/')
        check(status == 200 and b'Release smoke wiki' in page and b'bootstrap3' in page, 'Bootstrap3 page renders')
        settings = json.loads(php("$p=plugin_load('action','aclplusregex'); echo json_encode([$p->getConf('run'),(int)$p->getConf('anonymous'),is_file(DOKU_CONF.'aclplusregex.conf')]);"))
        check(settings == ['BEFORE', 1, True], 'ACLPlusRegex rules and settings are seeded')
        acl_cases = [
            ['public:start', '', [], 1],
            ['wiki:logo.png', '', [], 1],
            ['user:alice:private:start', 'alice', ['user'], 16],
            ['user:alice:private:start', 'bob', ['user'], 0],
            ['user:guestone:private:start', 'guestone', ['guest'], 0],
            ['user:guestboth:private:start', 'guestboth', ['user', 'guest'], 0],
            ['user:alice:public:avatar.png', '', [], 1],
            ['user:alice:share:start', 'guestone', ['guest'], 1],
            ['playground:test', 'alice', ['user'], 16],
            ['playground:test', 'guestone', ['guest'], 0],
            ['lab:start', 'member', ['user', 'lab'], 16],
            ['lab:private:test', 'member', ['user', 'lab'], 0],
            ['lab:private:test', 'staff', ['user', 'lab_staff'], 1],
            ['lab:private:test', 'manager', ['user', 'lab_admin'], 16],
        ]
        encoded = base64.b64encode(json.dumps(acl_cases).encode()).decode()
        permissions = json.loads(php("$cases=json_decode(base64_decode('" + encoded + "'),true); $result=[]; foreach($cases as [$id,$user,$groups,$expected]){$result[]=auth_aclcheck($id,$user,$groups);} echo json_encode($result);"))
        check(permissions == [case[3] for case in acl_cases], 'public, personal, guest and group namespace permissions match the rules')

        login_page = request('/doku.php?do=login')[2]
        login = {'id': 'start', 'do': 'login', 'u': 'releaseadmin', 'p': password}
        match = re.search(rb'name="sectok"[^>]*value="([^"]+)"', login_page)
        if match: login['sectok'] = match.group(1).decode()
        status, _, page = request('/doku.php', fields=login)
        check(status == 200 and b'do=logout' in page, 'owner can log in')
        edit = request('/doku.php?id=release_test&do=edit')[2]
        status, _, page = request('/doku.php', fields={'id': 'release_test', 'do[save]': 'Save',
            'sectok': token(edit), 'wikitext': '====== Release fixture ======\n\nPersistent content.\n',
            'summary': 'Smoke fixture', 'date': '0'})
        check(status == 200 and b'Persistent content.' in page, 'page editing and save work')
        profile = request('/doku.php?do=profile')[2]
        check(b'Upload photo' in profile, 'profile photo UI is available')
        png = base64.b64decode(php('''$im=imagecreatetruecolor(240,180); ob_start(); imagepng($im); echo base64_encode(ob_get_clean());'''))
        status, _, page = multipart('/lib/tpl/bootstrap3/avatar-upload.php', {'sectok': token(profile)},
                                    'avatar', 'photo.png', png, 'image/png')
        check(status == 200 and json.loads(php('$size=getimagesize(mediaFN("user:releaseadmin:public:avatar.png"));echo json_encode([$size[0],$size[1]]);')) == [120,120],
              'avatar upload is resized to 120x120')
        status, _, body = multipart('/lib/exe/ajax.php', {'call': 'mediaupload', 'ns': '',
                                    'mediaid': 'release-test.png', 'sectok': token(profile)},
                                    'qqfile', 'release-test.png', png, 'image/png')
        check(status == 200 and json.loads(body).get('success'), 'media upload succeeds')
        status, headers, body = request('/_media/release-test.png', anonymous=True)
        check(status == 200 and body == png, 'X-Accel media delivery preserves content')
        status, headers, body = request('/_media/release-test.png', headers={'Range': 'bytes=0-15'}, anonymous=True)
        check(status == 206 and body == png[:16] and headers['Content-Range'].startswith('bytes 0-15/'), 'media byte ranges work')
        check(request('/_detail/release-test.png')[0] == 200, 'media detail route works')
        for path in ['/data/media/release-test.png', '/data/cache/test', '/conf/local.php',
                     '/inc/init.php', '/vendor/autoload.php', '/.git/config', '/install.conf']:
            check(request(path, anonymous=True)[0] == 404, 'direct access blocked: ' + path)
        perms = json.loads(php('echo json_encode([is_writable(DOKU_PLUGIN), is_writable(DOKU_INC."doku.php"), is_writable(DOKU_CONF), is_writable($conf["savedir"])]);'))
        check(perms == [False, False, True, True], 'code is immutable while settings/content remain writable')
        php('''file_put_contents(DOKU_CONF.'acl.auth.php', "\\nprivate:* @ALL 0\\n", FILE_APPEND);
            io_createNamespace('private:sample.png','media'); copy(mediaFN('release-test.png'), mediaFN('private:sample.png'));''')
        check(request('/_media/private:sample.png', anonymous=True)[0] == 403, 'anonymous private-media request denied')
        check(request('/_media/private:sample.png')[0] == 200, 'owner can fetch private media')
        # Configure an approver for the synthetic page, then exercise the HTTP action.
        php('''$db=plugin_load('helper','approve_db')->getDB();
            $db->query('UPDATE page SET approver=?,hidden=0 WHERE page=?','@admin','release_test');''')
        request('/doku.php?id=release_test&approve=major')
        approved = approval()
        check(approved and approved['approved'] and int(approved['version']) == 1, 'Approve creates a version in SQLite')
        # Enable remote API solely in this disposable wiki, retaining normal auth.
        php('''file_put_contents(DOKU_CONF.'local.php', "\\n\\$conf['remote']=1;\\n\\$conf['remoteuser']='@admin';\\n\\$conf['trustedproxies']=[];\\n", FILE_APPEND);''')
        # Direct fixture writes occur outside FPM; allow timestamp granularity/cache validation.
        time.sleep(2.1)
        message = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                              'params': {'name': 'core_getPage', 'arguments': {'page': 'release_test'}}}).encode()
        status, _, body = request('/lib/plugins/mcp/mcp.php', raw=message, headers={'Content-Type': 'application/json'}, anonymous=True)
        check(status == 401, 'MCP rejects unauthenticated access')
        auth = base64.b64encode(('releaseadmin:' + password).encode()).decode()
        status, _, body = request('/lib/plugins/mcp/mcp.php', raw=message,
                                  headers={'Content-Type': 'application/json', 'Authorization': 'Basic ' + auth}, anonymous=True)
        check(status == 200 and not json.loads(body)['result'].get('isError') and b'Persistent content.' in body,
              'authenticated MCP reads a page through Nginx')
        # Explicit trusted-proxy configuration must be respected; arbitrary headers alone must not be.
        status, _, body = request('/doku.php?id=release_test', headers={'X-Forwarded-Proto': 'https'})
        check(b'https://127.0.0.1:' not in body, 'untrusted forwarded scheme ignored')
        gateway = json.loads(docker('inspect', name))[0]['NetworkSettings']['Networks']['bridge']['Gateway']
        php("file_put_contents(DOKU_CONF.'local.php', \"\\n\\$conf['trustedproxies']=['" + gateway + "'];\\n\", FILE_APPEND);")
        time.sleep(2.1)
        status, _, body = request('/doku.php?id=release_test', headers={'X-Forwarded-Proto': 'https'})
        check(status == 200 and ('https://127.0.0.1:' in body.decode()), 'trusted reverse-proxy HTTPS URLs work')
        connection = http.client.HTTPConnection(urllib.parse.urlsplit(base).netloc, timeout=10)
        connection.request('GET', 'http://unexpected.invalid/doku.php', headers={'Host': urllib.parse.urlsplit(base).netloc})
        response = connection.getresponse()
        check(response.status == 400, 'ambiguous absolute-form request rejected')
        response.read()
        connection.close()
        # Request generated assets to exercise PHP/LESS/JS caches too.
        status, _, body = request('/lib/exe/css.php?t=bootstrap3')
        check(status == 200 and len(body) > 10000, 'template CSS compiles')
        css = body.decode()
        check(all(rule in css for rule in ['body.vanilla-pro #dw__navbar > .dw-container',
              'mjx-container.MathJax[display="true"]', '.wrap_border']), 'shared presentation styles ship in the template')
        check('margin-top:110px !important' not in css and not re.search(
              r'[^{}]*\.CodeMirror-scroll[^{}]*\{[^}]*padding-bottom:0\s*!important', css),
              'legacy navbar and CodeMirror overrides are absent')
        status, _, body = request('/lib/exe/js.php?t=bootstrap3')
        check(status == 200 and len(body) > 10000, 'combined JavaScript builds')
        before = fingerprint()
        docker('stop', name)
        # Back up while stopped; recreate after restore into a different fresh volume.
        docker('run', '--rm', '--entrypoint', 'sh', '--mount', f'type=volume,src={volume},dst=/source,readonly',
               '--mount', f'type=volume,src={restored},dst=/restore', args.image,
               '-c', 'cd /source && tar cf - dokuwiki | tar xf - -C /restore')
        docker('rm', name)
        start(volume)
        check(fingerprint() == before and approval() == approved, 'container replacement preserves settings/pages/media/approval')
        # Removing an optional owner configuration must not cause startup to reseed it.
        php("if(!rename(DOKU_CONF.'aclplusregex.conf','/share/dokuwiki/aclplusregex.test-backup'))throw new RuntimeException('Cannot stage rules');")
        docker('stop', name)
        docker('rm', name)
        start(volume)
        check(php("echo (int)file_exists(DOKU_CONF.'aclplusregex.conf');") == '0',
              'existing installations do not acquire new seed ACL rules on startup')
        php("if(!rename('/share/dokuwiki/aclplusregex.test-backup',DOKU_CONF.'aclplusregex.conf'))throw new RuntimeException('Cannot restore rules');")

        docker('stop', name)
        docker('rm', name)
        start(restored)
        check(fingerprint() == before and approval() == approved, 'stopped backup restores accounts/content/SQLite to a fresh volume')
        errors = json.loads(php('''$logs='';foreach(glob($conf['logdir'].'/error/*')?:[] as $f){if(is_file($f))$logs.=file_get_contents($f);} echo json_encode($logs);'''))
        # The deliberately rejected MCP call logs an exception; all other errors fail.
        entries = [line for line in errors.splitlines() if line and not line.startswith('  #')]
        expected = 'dokuwiki\\Remote\\AccessDeniedException: server error. not authorized to call method'
        check(len(entries) == 1 and entries[0].endswith(expected), 'only the expected MCP access-denied exception is logged')
        print(f'Completed {len(checks)} checks.', flush=True)
    except Exception:
        print('Last HTTP response:', last_body[:3000].decode(errors='replace'), flush=True)
        print(docker('logs', '--tail', '70', name), flush=True)
        print(docker('exec', name, 'sh', '-c', 'cat /share/dokuwiki/data/log/error/* 2>/dev/null || true'), flush=True)
        raise
    finally:
        subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for storage in (volume, restored):
            subprocess.run(['docker', 'volume', 'rm', storage], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    main()

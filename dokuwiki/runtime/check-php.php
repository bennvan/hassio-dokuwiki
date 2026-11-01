<?php
// PHP2Shell (CVE-2026-109618 / CVE-2026-109619) is fixed in PHP 8.5.12.
// This distribution uses the 8.5 branch; reject an accidentally older runtime.
if (PHP_VERSION_ID < 80512) {
    fwrite(STDERR, "PHP 8.5.12 or newer is required for the PHP2Shell fixes.\n");
    exit(1);
}
// Fail the image build if the wiki's required extensions or codecs are missing.
$required = ['ctype', 'curl', 'dom', 'exif', 'fileinfo', 'filter', 'gd', 'iconv',
    'json', 'mbstring', 'openssl', 'PDO', 'pdo_sqlite', 'session', 'SimpleXML',
    'sodium', 'sqlite3', 'tokenizer', 'xml', 'xmlreader', 'xmlwriter', 'zip', 'zlib'];
$missing = array_filter($required, fn($name) => !extension_loaded($name));
if (!$missing && !in_array('sqlite', PDO::getAvailableDrivers(), true)) $missing[] = 'PDO SQLite driver';
if (extension_loaded('gd')) {
    foreach (['JPEG Support', 'PNG Support', 'WebP Support'] as $codec) {
        if (empty(gd_info()[$codec])) $missing[] = "GD $codec";
    }
}
if ($missing) {
    fwrite(STDERR, 'Missing PHP dependencies: ' . implode(', ', $missing) . "\n");
    exit(1);
}
echo "PHP extensions, SQLite driver and image codecs OK\n";

<?php
// CLI only. Existing installations are never reseeded, merged or deleted.
if (PHP_SAPI !== 'cli') exit(1);
$storage = $argv[1] ?? '/share/dokuwiki';
$seed = $argv[2] ?? '/opt/dokuwiki-seed';
$marker = $storage . '/.hassio-dokuwiki-v1';
if (is_file($marker)) {
    if (!is_dir($storage . '/conf') || !is_dir($storage . '/data')) {
        throw new RuntimeException('Existing wiki storage is incomplete; restore it before starting.');
    }
    echo "Using existing wiki storage\n";
    exit;
}
if (!is_dir(dirname($storage))) throw new RuntimeException('Storage parent is missing. Check the share mount.');
if (file_exists($storage) && (!is_dir($storage) || count(scandir($storage)) > 2)) {
    throw new RuntimeException('Unrecognised non-empty storage. Import must be reviewed; no files were changed.');
}
if (!is_dir($seed . '/conf') || !is_dir($seed . '/data')) throw new RuntimeException('Missing clean seed.');
function copySeed(string $source, string $destination): void {
    if (!is_dir($destination) && !mkdir($destination, 0750, true)) throw new RuntimeException('Cannot create storage.');
    foreach (new DirectoryIterator($source) as $entry) {
        if ($entry->isDot()) continue;
        if ($entry->isLink()) throw new RuntimeException('Seed must not contain symlinks.');
        $target = $destination . '/' . $entry->getFilename();
        if ($entry->isDir()) copySeed($entry->getPathname(), $target);
        elseif (!copy($entry->getPathname(), $target)) throw new RuntimeException('Cannot copy seed.');
    }
}
// Stage initialization next to its destination so incomplete writes are never
// mistaken for an initialized wiki. A failure leaves evidence for inspection.
$staging = $storage . '.initializing';
if (file_exists($staging)) throw new RuntimeException('An interrupted initialization needs inspection.');
copySeed($seed, $staging);
file_put_contents($staging . '/.hassio-dokuwiki-v1', "1\n");
if (is_dir($storage)) rmdir($storage); // only the verified empty directory
if (!rename($staging, $storage)) throw new RuntimeException('Cannot activate initialized storage.');
echo "Initialized a new wiki\n";

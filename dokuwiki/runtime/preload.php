<?php
// Use core defaults from this release and mutable local settings from /share.
if (!defined('DOKU_INC')) define('DOKU_INC', dirname(__DIR__) . '/');
if (!defined('DOKU_CONF')) define('DOKU_CONF', DOKU_INC . 'conf/');
include DOKU_INC . 'inc/config_cascade.php';
foreach ($config_cascade as $name => &$cascade) {
    if ($name === 'userscript') continue;
    // ACLs and users have a scalar 'default' path and stay in persistent conf/.
    if (!isset($cascade['default']) || !is_array($cascade['default'])) continue;
    foreach ($cascade['default'] as &$path) {
        if (str_starts_with($path, DOKU_CONF)) {
            $path = '/opt/dokuwiki-defaults/conf/' . substr($path, strlen(DOKU_CONF));
        }
    }
    unset($path);
}
unset($cascade);
$config_cascade['plugins']['protected'] = [
    '/opt/dokuwiki-defaults/conf/plugins.required.php',
    DOKU_CONF . 'plugins.protected.php',
    '/opt/dokuwiki-runtime/plugins.protected.php',
];
$config_cascade['main']['protected'][] = '/opt/dokuwiki-runtime/local.protected.php';

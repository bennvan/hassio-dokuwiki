<?php
// Container paths and delivery mechanism; installation owners manage other settings.
// Template endpoints must use the wiki root for cached X-Accel-Redirect URLs.
$conf['basedir'] = '/';
$conf['savedir'] = DOKU_INC . 'data';
$conf['xsendfile'] = 3;
$conf['userewrite'] = 1;

#!/bin/sh
set -eu
# Never silently write the wiki into an ephemeral /share directory.
mountpoint -q /share || { echo 'A persistent /share mount is required.' >&2; exit 1; }
if [ -f /share/dokuwiki/.hassio-dokuwiki-v1 ]; then
    php /opt/dokuwiki-runtime/init-storage.php
else
    php /opt/dokuwiki-runtime/init-storage.php
    chown -R www-data:www-data /share/dokuwiki
fi
# The installer and some plugins read shipped files through DOKU_CONF directly.
# Project image defaults there without copying them over local user settings.
for source in /opt/dokuwiki-defaults/conf/*; do
    [ -f "$source" ] || continue
    target="/share/dokuwiki/conf/$(basename "$source")"
    if [ ! -e "$target" ] && [ ! -L "$target" ]; then
        ln -s "$source" "$target"
    fi
done
nginx -t
exec /usr/bin/supervisord -c /opt/dokuwiki-runtime/supervisord.conf

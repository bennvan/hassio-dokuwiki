# Release build: all sources must be independently retrievable and verified.
FROM python:3.13-slim-bookworm@sha256:281d39ff02e3b389401586134ff9e6572954687822a58055ec07a60ded4e0b7f AS source
WORKDIR /package
COPY tools/ tools/
COPY sources.inventory.json .
COPY seeds/ seeds/
RUN --mount=type=cache,target=/archive-cache \
    python tools/sources.py assemble --archive-cache /archive-cache --output /wiki

FROM php:8.5.12-fpm-bookworm@sha256:75dc898a8861a777f14c57b2afbb811a848735701593cbc354e4194807a88f3e AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx supervisor util-linux \
       libjpeg62-turbo-dev libpng-dev libwebp-dev libfreetype6-dev libzip-dev libicu-dev \
    && docker-php-ext-configure gd --with-jpeg --with-webp --with-freetype \
    && docker-php-ext-install -j2 gd exif zip intl \
    && rm -rf /var/lib/apt/lists/*
COPY runtime/ /opt/dokuwiki-runtime/
RUN php /opt/dokuwiki-runtime/check-php.php
COPY --from=source /wiki/ /var/www/html/
COPY seeds/conf/ /opt/dokuwiki-seed/conf/
RUN mkdir -p /opt/dokuwiki-defaults \
    && cp -a /var/www/html/conf /opt/dokuwiki-defaults/conf \
    && mv /var/www/html/data /opt/dokuwiki-seed/data \
    && rm -rf /var/www/html/conf \
    && ln -s /share/dokuwiki/data /var/www/html/data \
    && ln -s /share/dokuwiki/conf /var/www/html/conf \
    && cp /opt/dokuwiki-runtime/preload.php /var/www/html/inc/preload.php \
    && cp /opt/dokuwiki-runtime/nginx.conf /etc/nginx/nginx.conf \
    && cp /opt/dokuwiki-runtime/nginx-php.conf /etc/nginx/dokuwiki-php.conf \
    && sed '/^fastcgi_param[[:space:]]*HTTP_HOST[[:space:]]/d' /etc/nginx/fastcgi_params > /etc/nginx/dokuwiki-fastcgi.conf \
    && cp /opt/dokuwiki-runtime/php.ini /usr/local/etc/php/conf.d/wiki.ini \
    && cp /opt/dokuwiki-runtime/php-fpm.conf /usr/local/etc/php-fpm.d/zzzz-wiki.conf \
    && chmod +x /opt/dokuwiki-runtime/entrypoint.sh \
    && chown -R root:root /var/www/html /opt/dokuwiki-defaults \
    && chmod -R go-w /var/www/html /opt/dokuwiki-defaults
LABEL org.opencontainers.image.title="DokuWiki for Home Assistant" \
      org.opencontainers.image.source="https://github.com/bennvan/hassio-dokuwiki" \
      org.opencontainers.image.version="0.1.12"
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD curl -fsS http://127.0.0.1:8080/healthz || exit 1
ENTRYPOINT ["/opt/dokuwiki-runtime/entrypoint.sh"]

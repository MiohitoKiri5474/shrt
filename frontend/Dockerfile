# oven/bun:1, multi-arch index digest resolved 2026-07-07
FROM oven/bun:1@sha256:e10577f0db68676a7024391c6e5cb4b879ebd17188ab750cf10024a6d700e5c4 AS builder
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY . .
RUN bun run build-only

# nginx:alpine, multi-arch index digest resolved 2026-07-07
FROM nginx:alpine@sha256:4a73073bd557c65b759505da037898b61f1be6cbcc3c2c3aeac22d2a470c1752
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN mkdir -p /var/cache/nginx/client_temp \
              /var/cache/nginx/proxy_temp \
              /var/cache/nginx/fastcgi_temp \
              /var/cache/nginx/uwsgi_temp \
              /var/cache/nginx/scgi_temp \
    && chown -R nginx:nginx /var/cache/nginx \
                            /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid
EXPOSE 80

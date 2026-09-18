# Cloud-360 frontend — Vite build served by nginx, which also reverse-proxies
# /api to the backend so the browser only ever talks to one origin.
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite inlines env at build time, so the public URL must be known here, not at
# run time. Defaults to localhost for a plain `docker build` outside compose.
ARG VITE_API_BASE_URL=http://localhost:8090
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM nginx:alpine

# nginx has no $connection_upgrade built in; map it once for the WS proxy.
RUN printf 'map $http_upgrade $connection_upgrade {\n    default upgrade;\n    ""      close;\n}\n' \
    > /etc/nginx/conf.d/upgrade-map.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1

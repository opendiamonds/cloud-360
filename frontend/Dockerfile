# Cloud-360 frontend — Vite build served by nginx, which also reverse-proxies
# /api to the backend so the browser only ever talks to one origin.
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite 在 build 期把這個值內聯進 bundle，所以它是建置期設定，不是 runtime 設定。
#
# **預設留空＝同源相對路徑**，而這對任何使用這個映像的方式都是正確的：映像裡的
# nginx 同時提供靜態檔與 `/api/` 反向代理（見 nginx.conf），所以 `/api/...` 一定
# 打到同一個 origin，不論使用者是用 localhost、127.0.0.1 還是 LAN IP 開站台。
#
# 原本這裡預設 `http://localhost:8090`，把整個映像綁死在那一個主機名上：從
# `http://127.0.0.1:8090` 開同一個站台時，每一個 API 呼叫都變成跨來源請求並被
# 瀏覽器擋掉（症狀是控件空白，因為被擋的 fetch 丟 TypeError 而非 HTTP 錯誤）。
# 只有前後端真的不同源時才需要傳入絕對 URL。
ARG VITE_API_BASE_URL=""
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

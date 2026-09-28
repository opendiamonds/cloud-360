/**
 * 前後端 API／WS 基底 URL。
 *
 * **容器化的服務方式一律同源。** frontend 映像裡的 nginx 同時提供靜態檔與
 * `/api/` 反向代理（見 `frontend/nginx.conf`），所以 production build 的預設值是
 * **空字串＝相對路徑**：API 呼叫跟著使用者實際輸入的主機名走，用 `localhost`、
 * `127.0.0.1` 或 LAN IP 開同一個站台都成立。
 *
 * 反之，把絕對 URL 烤進 bundle 會把整個站台綁死在那一個主機名上。從別的主機名
 * 開站台時，每一個 API 呼叫都變成跨來源請求而被瀏覽器擋掉，且**症狀不是 HTTP
 * 錯誤而是畫面空白**——被 CORS 擋掉的 fetch 丟的是 `TypeError: Failed to fetch`，
 * 任何 `.catch()` 吞掉它的地方就只剩一個沒有內容的控件。
 *
 * **bare-metal 本機開發是唯一真的不同源的情境**：vite dev server 在 5173、
 * uvicorn 在 8000／8010，中間沒有反向代理。因此只有 `import.meta.env.DEV` 時才
 * 保留 `http://localhost:8000` 這個後備值；正式做法仍是照 `LOCAL-DEV.md` 第 4 節
 * 在 `frontend/.env` 明確設定 `VITE_API_BASE_URL`（後端不在 8000 時必設）。
 *
 * - VITE_API_BASE_URL：HTTP API 根（例 http://localhost:8010）；留空＝同源
 * - VITE_WS_BASE_URL：可選；未設則由 API base 或目前頁面 origin 推導
 */

function stripTrailingSlash(url: string): string {
  return url.replace(/\/+$/, '');
}

/** 目前頁面的 origin；非瀏覽器環境（例如建置期求值）回空字串。 */
function browserOrigin(): string {
  return typeof window === 'undefined' ? '' : window.location.origin;
}

/** 未設定 `VITE_API_BASE_URL` 時的後備值。見檔頭：dev 沒有反向代理，production 有。 */
const FALLBACK_API_BASE_URL = import.meta.env.DEV ? 'http://localhost:8000' : '';

/** HTTP API 根，不含結尾斜線。**空字串代表同源**，`apiUrl()` 於是產生相對路徑。 */
export const API_BASE_URL = stripTrailingSlash(
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ||
    FALLBACK_API_BASE_URL
);

/**
 * WebSocket 根，不含結尾斜線。**一定是絕對 URL**：`useCollaboration.ts` 會對
 * `wsUrl()` 的結果呼叫 `new URL()`，而 `new URL()` 收到相對字串會直接丟
 * TypeError。同源時因此由目前頁面的 origin 推導（http→ws、https→wss）。
 */
export const WS_BASE_URL = stripTrailingSlash(
  (import.meta.env.VITE_WS_BASE_URL as string | undefined)?.trim() ||
    (API_BASE_URL || browserOrigin()).replace(/^http/, 'ws')
);

/** 組出完整 HTTP API URL（path 以 / 開頭，例如 /api/auth/me） */
export function apiUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalized}`;
}

/** 組出完整 WebSocket URL */
export function wsUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${WS_BASE_URL}${normalized}`;
}

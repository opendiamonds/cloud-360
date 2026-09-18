/**
 * 前後端分服務部署時，API／WS 基底 URL 由 Vite 環境變數注入。
 *
 * - VITE_API_BASE_URL：HTTP API 根（例 http://localhost:8000 或 https://api.example.com）
 * - VITE_WS_BASE_URL：可選；未設則由 API base 的 http→ws、https→wss 推導
 */

function stripTrailingSlash(url: string): string {
  return url.replace(/\/+$/, '');
}

/** HTTP API 根，不含結尾斜線 */
export const API_BASE_URL = stripTrailingSlash(
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ||
    'http://localhost:8000'
);

/** WebSocket 根，不含結尾斜線 */
export const WS_BASE_URL = stripTrailingSlash(
  (import.meta.env.VITE_WS_BASE_URL as string | undefined)?.trim() ||
    API_BASE_URL.replace(/^http/, 'ws')
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

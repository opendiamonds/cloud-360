/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 後端 HTTP API 根 URL（例 https://api.example.com） */
  readonly VITE_API_BASE_URL?: string;
  /** 可選 WebSocket 根；未設則由 API base 推導 */
  readonly VITE_WS_BASE_URL?: string;
  /** 是否顯示 demo 帳號快速填入；部署預設關閉 */
  readonly VITE_ENABLE_DEMO_QUICK_USERS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

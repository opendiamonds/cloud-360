# Logical Components — U1: u1-icon-service-gateway

> Stage: nfr-requirements (3.2) / nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u1-icon-service-gateway` (kind: `library`)

---

## 1. 模組與類別架構 (Module & Class Structure)

- **模組位置**: `backend/services/diagram_builder.py`
- **主要公開介面**: `fetch_icon_from_n8n(service: str, provider: Literal["compound"] = "compound") -> str`
- **內部輔助函式**:
  - `_execute_n8n_post(url: str, payload: dict) -> str`: 處理 HTTP POST 與逾時。
  - `generate_fallback_svg(service_name: str) -> str`: 本地 SVG 合成器。
- **快取裝飾**: `@functools.lru_cache(maxsize=128)` 綁定於公開介面，達到記憶體即時快取。


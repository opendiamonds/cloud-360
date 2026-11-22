# Tech Stack Decisions — U1: u1-icon-service-gateway

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u1-icon-service-gateway` (kind: `library`)
> 追溯上游基準：
> - [functional-spec](../functional-design/functional-spec.md)
> - [rules](../functional-design/rules.md)

---

## 1. 技術選型與依賴決策 (Technology Selections & Rationale)

| 層次 (Layer) | 選定技術 (Technology) | 版本 / 規格 (Version) | 選型理由與決策依據 (Rationale) |
| :--- | :--- | :--- | :--- |
| **執行環境** | Python | 3.11+ | 專案後端統一標準環境，支援嚴格型別註解 (`Literal["compound"]`)。 |
| **HTTP 通訊客戶端** | `urllib.request` / `httpx` | 標準庫 / 既有依賴 | 沿用既有後端 HTTP Client 模組，零新增第三方套件依賴，保持輕量穩定。 |
| **快取機制** | `functools.lru_cache` | 標準庫 (maxsize=128) | 程序內記憶體快取，具備 O(1) 查找速度與線程安全，完全免除外部 Redis 相依性。 |
| **SVG 合成** | 原生字串範本 (f-string) | 原生 Python | 針對 40x40 固定格式產出標準向量 XML，速度極快 (< 0.1ms)，無解析開銷。 |


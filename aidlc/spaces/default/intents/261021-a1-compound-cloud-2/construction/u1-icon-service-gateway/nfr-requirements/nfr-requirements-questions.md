# NFR Requirements Questionnaire — U1: u1-icon-service-gateway

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u1-icon-service-gateway` (kind: `library`)
> 追溯上游基準：
> - [functional-spec](../functional-design/functional-spec.md)
> - [rules](../functional-design/rules.md)
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C1, C2)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (NFR3, CON2)

---

## 1. 單元非功能需求邊界說明 (NFR Scope for Library Unit)

依據 `produces_kinds` 規範，`u1-icon-service-gateway` 作為 `library` 類型單元，其核心 NFR 範疇著重於：
1. **安全性 (Security)**: Webhook 傳輸加密 (HTTPS)、無敏感機密外洩 (No credentials leaked in logs)。
2. **技術選型決策 (Tech Stack Decisions)**: 沿用 Python 3.11 標準函式庫 `urllib.request` 與既有 `httpx`，零新增外部依賴。
3. **可靠性與逾時約束**: 嚴格 5.0 秒逾時、100% 降級防護保證。

---

## 2. 非功能性需求關鍵問卷 (Clarifying Questions)

### Q1. 安全性與環境變數管理 (Security & Environment Variables)
外部 n8n 服務網址從環境變數讀取時之安全性處理策略為何？
- [A] **自 `os.getenv("N8N_WEBHOOK_URL")` 讀取並驗證 HTTPS**：若未設置環境變數或非合法 URL，自動靜默回退至本地 40x40 灰底文字 SVG，絕不對外洩露伺服器環境資訊。（推薦）
- [B] **拋出環境配置錯誤異常**。

[Answer]: [A]

### Q2. 零新增依賴原則 (Zero New Dependencies Policy)
本單元實作 HTTP 請求與 SVG 合成時，是否嚴格遵循 ADR-0004 零新增外部套件？
- [A] **全數使用 Python 既有標準庫**：HTTP 請求使用既有專案環境之 `httpx` 或 Python 3.11 `urllib.request`，SVG 合成使用純字串格式化，零新增外部套件依賴。（推薦）
- [B] **引入第三方 SVG 生成庫**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 `security-requirements.md`、`tech-stack-decisions.md` 與 `traceability.json` 前，請確認以下彙整摘要正確無誤：

- **環境安全性 (Q1)**: [A] 讀取 `N8N_WEBHOOK_URL`，無配置或異常時安全回退，無機密洩露。
- **依賴原則 (Q2)**: [A] 嚴格採用既有 Python 標準庫，零新增第三方套件。

Does this all look correct before I generate the NFR requirements artifacts for U1?
- Looks correct
- Request changes

[Answer]: Looks correct

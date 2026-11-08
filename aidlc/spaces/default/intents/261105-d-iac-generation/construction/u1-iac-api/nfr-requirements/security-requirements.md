# Security Requirements — u1-iac-api

> Unit: `u1-iac-api`（service）· 上游 NFR1／NFR3／NFR4；FD BR1.*；Q3–Q6=A。

## ADR-0006 四面向（NFR1）

| 面向 | 判定 | 處置 |
|---|---|---|
| **IAM** | **適用（應用 RBAC）** | 既有 JWT＋`require_story_action`；D1／D2／D3／download 權限對齊 FD BR1.1（download＝D1 edit）。第一個 D HTTP 須有 403／2xx 成對測（NFR4／BR1.12）。 |
| **Encryption** | **沿用既有** | 本 unit **不**持久化草稿／密文（in-memory）；不新增磁碟密文儲存。HTTPS／主機防護沿用 staging 部署。 |
| **Network exposure** | **適用（新增受控面）** | 新增 `/api/iac/*`；僅能力動詞；無 apply／SM 寫入端點。體積上限見 scalability（防 DoS）。 |
| **Audit logging** | **適用** | 結構化 log（`cloud360.iac.*`）：誰／哪圖／哪路由／結果碼／耗時；**禁止** HCL 明文密值、prompt、JWT 原文（NFR3）。 |

## NFR3 — 保密

| ID | 需求 |
|---|---|
| NFR3.1 | D3 改寫後：API JSON、log sink、download zip **不得**再出現已替換之明文 secret 樣式（FD BR1.5）。 |
| NFR3.2 | 負向＋突變測試於 redactor／zip 組裝邊界（與 PBT NFR2 銜接）。 |
| NFR3.3 | 錯誤 `message` 可給人讀；分支不得依賴 message 字串；**不得**含本機路徑／traceback／SQL。 |

## NFR4 — 授權測試

| ID | 需求 |
|---|---|
| NFR4.1 | 規則 A／B／C 適用；code-gen 對 `POST /generate`（US6.1）交付 allow／deny TestClient。 |
| NFR4.2 | 缺權 → **403**；不得以 404 掩蓋存在性（除非既有平台慣例明確要求——本 unit 採 403）。 |

## 明確禁止

- 代 apply／destroy／雲端 Secret Manager Put。
- 版控 path part `secrets`／`prod`／`production`；credential 字串進 repo。
- 密文進 audit 決議或 log。

## 明確不在本 unit

| 項目 | 歸屬 |
|---|---|
| UI a11y（NFR5） | U2 |
| Checkov 規則內容調校 | 運維／後續；本輪只釘 CLI 存在與失敗語意 |
| CI 新增 IaC scan job | 範圍外（requirements 約束） |

<!-- confirmed: Looks correct -->

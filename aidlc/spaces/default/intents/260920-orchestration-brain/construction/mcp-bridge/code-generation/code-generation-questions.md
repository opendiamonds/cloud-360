# Code Generation 問題檔 — `U21 mcp-bridge`

## 核可範圍說明

本題核可的是同目錄下的 `code-generation-plan.md`（含其內嵌的 Testing Contract，`test-after`、`standard`）、`unit-test-instructions.md`，
**以及契約變更紀錄草案 `adr-0021-draft.md`**（核可後於 Step 1 移入 `inception/decisions/` 並改為 Accepted）。明白揭露：

- **契約變更（ADR-0021，C-1..C-5）**：新增清空工具；`field_key` 改名 `field`（MB6=A）；token 經每請求標頭轉遞、agent 身分走 `X-Cloud360-Agent`、授權責任更正為 facade 承擔；allowlist 初始範圍**收窄**為需求欄位三個工具（對已核可範圍的收窄）；移除 bridge 對成員層的直接依賴邊。上游已凍結檔不回改。
- **網段**：bridge 只掛新的專屬網段 `mcp`（`internal: true`，成員為 `backend` 與 `mcp-bridge`），不進 `internal`；`DEPLOY.md` §5.11 的 `internal: true` 禁令限縮為只適用既有網段。
- **新依賴**：`mcp` 精確釘版（路線 A／B 進 `backend/requirements.txt`，會進 backend 執行期映像；路線 C 為獨立 venv）。
- **Step 1 中途關卡**：依賴路線、斷線取消（OPEN-MB21-16）、未知工具能否回協定錯誤（OPEN-MB21-17）要實測後才知道；落在路線 C／D 或 17-B 時會再請你同意。
- **已接受的殘留**：明文 JWT、成功讀取不記使用者、部署後健康檢查不擋部署、512m 為估計、deploy 剩餘預算 480 秒、本版無實際 client。完整清單見計畫 §六。
- **零新環境變數、零 secret、零對外埠、零 DDL**；不改 `render-env.sh`、任何 `.env.example`、`nginx.conf`。

## Plan Approval

[Approval Fingerprint]: sha256:v3:56e51b90df02320cc09d4529e1710f13022367f0ed6c4555b497ca39255c0919
[Planned Source]: 1910388451791d6eb66e1b6d5e7ab81022a0ac0ecd30348d8945c807912f7ea5
- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan
[Answer]: Approve Plan

# Code Generation 問題檔 — `U13 brain-gateway`

## 核可範圍說明

本題核可的是同目錄下的 `code-generation-plan.md`（含其內嵌的 Testing Contract，`test-after`、`standard`）、`unit-test-instructions.md`，
**以及契約變更紀錄草案 `adr-0020-draft.md`**（核可後於 Step 1 移入 `inception/decisions/` 並改為 Accepted）。明白揭露：

- **契約變更（ADR-0020）**：WebSocket 契約新增七個必填欄位（握手協定名、訊息的 `page`、狀態訊息的 `scope`／`segment`、反問的 `kind`），
  協定版本維持 1；修改 `U2` 已交付的模組並重產前後端型別。另把 `K-16`／`K-17`／`K-18` 誤列 `U13` 為消費端的三處更正。
- **跨單元修改**：`U2` 契約與既有測試、DEMO 前後端移除（含兩支 e2e 的 `/brain` 落地頁改中性頁、一支後端測試改寫）、`main.py` 啟動流程、
  `deploy.yml` 必要 secret 檢查、`DEPLOY.md`、`LOCAL-DEV.md`、`requirements.txt` 明列 `websockets`。
- **合併前需你執行**：確認 GitHub 的 `OPENROUTER_API_KEY` 已設為 secret（非 variable）；否則含必要檢查的部署會失敗並觸發回滾。
- **本分支第一次進 `ut` 時 DEMO 後端必須已移除**（`[IG2]`=A）。
- **不新增任何 LLM 呼叫**；`AC8.1.1` 仍為 Deferred，待你裁決。
- **限制**：Redis 替身與 TestClient 驗不到真實原子性、真實網路逾時與真實 HTTP 403；Cloudflare 子協定透傳只能部署後實測。

## Plan Approval

[Approval Fingerprint]: sha256:v3:5cdaaa3c6e3575eb098b46f7debdd8e6257bd499b1655f8187a597cb8243a6ac
[Planned Source]: 9dbff0772c65d0ff1bdede345f8a197e8534a3974d7b826615a263fe6064d6e6
- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan
[Answer]: Approve Plan

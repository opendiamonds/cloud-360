# 驗證關卡與 TCMS 同步報告 — A3 LangGraph refactor

> Intent：`261001-a2-langgraph`

## 結論

| 項目 | 結果 |
|---|---|
| 第 1 層 機械檢查 | **通過**（本 intent 3/3，ERROR 0 WARN 0） |
| 第 2 層 語意審查 | **通過**（3 案皆屬真實 LLM／本機 env；未重複自動化層） |
| TCMS 同步 | **本輪未寫入遠端** —— 核准後由維運者執行 `scripts/tcms_sync.py --file …`（需 TCMS 憑證） |

---

## 1. 第 1 層：機械檢查

```bash
python3 scripts/tcms_validate.py --file \
  aidlc/spaces/default/intents/261001-a2-langgraph/construction/tcms-test-cases/manual-test-cases.md
```

```
驗證 3 個案例……
通過 3/3　ERROR 0　WARN 0
機械檢查全數通過。
```

exit 0。

---

## 2. 第 2 層：語意審查

| 檢查 | 結果 |
|---|---|
| 目的指向真實會失敗的行為 | 通過（SSE 無增量、重試無效、缺金鑰假成功／洩密） |
| 手動／自動不重複 | 通過（自動化 mock；手動打真實 OpenRouter／本機 `.env`） |
| 步驟可被外人執行 | 通過（含 venv、重啟 backend、清空金鑰還原） |
| 通過條件二元 | 通過 |
| API／UI 與 openapi／App 一致 | 通過（機械層已核） |
| 背景說明自動化為何漏抓 | 通過（三案皆寫 LLM 費用／env 殘值） |

---

## 3. 覆蓋盤點摘要

| 桶 | 數量 |
|---|---|
| 已自動化 | 7 |
| 本 stage 新腳本 | 0（code-gen 已寫；本 stage 補 `@purpose`） |
| 只能手動 | 3 |
| Open items | 0 |

突變驗證：見 `automation-test-plan.md` §4（預期改錯 → FAIL → 還原 OK）。

---

## 4. 同步預覽（dry-run）

```bash
python3 scripts/tcms_sync.py --file \
  aidlc/spaces/default/intents/261001-a2-langgraph/construction/tcms-test-cases/manual-test-cases.md \
  --dry-run
```

本環境執行 dry-run 時無法解析 TCMS 主機（`socket.gaierror`／網路未達 `tcms.danniel.cc`），**未寫入任何遠端資料**。機械驗證已通過；實際同步須在可達 TCMS 的機器、持憑證後執行：

```bash
python3 scripts/tcms_sync.py --file \
  aidlc/spaces/default/intents/261001-a2-langgraph/construction/tcms-test-cases/manual-test-cases.md
```

計畫名稱（sync key 所屬 plan）：`Cloud-360 A3 LangGraph Refactor`  
案例標題：

1. 真實 OpenRouter 金鑰下 A3 評核建議串流完整結束  
2. 真實金鑰下重試建議再次產生 suggestion_delta  
3. 本機缺 OpenRouter 金鑰時評核降級可讀且不洩漏 secret  

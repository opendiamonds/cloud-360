# Code Generation — 釐清問題（legacy-cost-retirement）

> Unit: `legacy-cost-retirement`（U3）· service（退場）

## 計畫要點（供核可）

1. **HTTP** — 移除舊 `cost_router`／diagrams；不新增 v1 stub
2. **Schema** — 四表 rename `archive_*`；DEPLOY 記 ≥90 天到期；應用零讀寫
3. **Calculator** — 刪模組；移除 Python `playwright`
4. **護欄** — 保留 U5 存活集；修 warm cache／orphan；改 e2e；OpenAPI 重產
5. **Env** — 刪舊 stub／calculator 變數；env／repo contract 綠
6. **合併** — 檢查清單要求與 **U8 同批**；本 unit 單獨不合 `ut`

詳見 `code-generation-plan.md` 與 `unit-test-instructions.md`。

---

## Plan Approval

請核可上述計畫、內嵌 Testing Contract（test-after／Standard）、與 unit-test-instructions。

[Approval Fingerprint]: sha256:9c9b3b71b033b35d586ea62869e4cfbac9018e5bcfc4623ee0805c224ccf957a

- Approve Plan — 依計畫實作
- Request Changes — 修改計畫後再核可

[Answer]: Approve Plan

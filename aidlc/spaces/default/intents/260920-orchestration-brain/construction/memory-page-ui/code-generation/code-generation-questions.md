# Code Generation 問題檔 — `U15 memory-page-ui`

> 本檔承載 Plan Approval 的核可問題與兩個綁定標籤。標籤刻意不寫進
> `code-generation-plan.md`（指紋覆蓋計畫全文，寫進去會自我指涉而永不收斂）。

## 一、本站不重問的事（上游已定案或已由使用者裁決）

| 事項 | 定案 | 出處 |
|---|---|---|
| 分頁形狀、三區抓取、就地移除、INV-3 落點、非擁有者列 | `[M1]`–`[M5]` 皆 A | functional-design |
| 每頁 20 則 | 以證據收斂 | nfr-requirements §三 |
| 三站審查發現（刪除後漏列、入口判定、`/me` 失敗、補償重抓競態、雙重退頁、滿載計數） | 使用者裁決：帶進本站計畫處置 | 三站 diary 的 Open questions |
| 待核准帳號可呼叫記憶 API | 使用者裁決：併入本單元修補 | nfr-requirements diary |
| 測試方法論與量級 | Testing Contract：`test-after`、`standard` | `code-generation-plan.md` |

## 二、計畫摘要

- **前端交付**：記憶頁 `/memory`（三區、逐則刪除、情節記憶分頁）、四個非元件模組、路由與 Sidebar 項。
- **後端交付（跨單元，改 `U8` 既有程式）**：在記憶 facade 加「已核准」檢查，待核准帳號對五個記憶端點一律 403，且同進程的大腦路徑也一併擋下；`DELETE` 的回應宣告新增 403，`openapi.json` 與前端型別隨之重產。**落點選 facade 而非 router**：router 契約宣告本層不做授權（`memory_router.py:8-12`，並由既有測試 `C3` 機械斷言），且大腦同進程直呼 facade。
- **審查修正**：補償重抓改用序號防亂序、失敗時顯示提示、只由一處決定退頁、滿載過的區刪除後仍顯示「N+」、`/me` 失敗不轉圈。
- **測試**：後端 7 個（含 pending 拒、approved 通過的雙向，與同進程路徑）、前端 e2e 10 個（含 offset 位移、重抓中翻頁、重抓失敗三個情境），每支 e2e 做突變驗證。
- **零新依賴、零新環境變數、零 schema 變更、零管線改動**。

## Plan Approval

[Approval Fingerprint]: sha256:v3:15a3033efb592be523d84454bd25e876a2857c06b43848116a8373c806a393da
[Planned Source]: 5f94a6fa452514e861e7f94c5ad44b514078a3391a4d547f3742e8ab52988626

- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan

[Answer]: Approve Plan

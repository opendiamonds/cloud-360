# 技術選型決定 — admin-page-column（U3）

> **上游輸入**：本單元的 `../functional-design/business-logic-model.md`（Revision 1 的分頁狀態邏輯模型與**決策表：哪些操作觸發哪種抓取**）、`../functional-design/frontend-components.md`（Revision 1 的三種抓取路徑、三處整份重抓皆須改、正規化收斂在抓取函式內、併發保護）。本檔的每一條 NFR 皆為上述功能規則的非功能面展開，不新增行為。

## 不引入任何新的前端依賴

`package.json` 的 `dependencies` **零變動**。分頁控制以既有的 React ＋ Tailwind 實作，不引入分頁元件庫。

> 唯一的工具鏈變動屬 U5（型別產生器，以釘住版本的一次性執行呼叫，不列入依賴）。

## T-1 型別採用產生的型別，不手寫

| 項目 | 決定 |
|---|---|
| 使用者物件與 envelope 的型別 | **採用產生的型別**（`components['schemas']['UserSchema']`／`['UserListPage']`） |
| 其餘 51 處資料抓取 | **維持手寫型別**，不在本 intent 一併遷移 |

限縮採用範圍是 application-design 的既有定案（Q5=A）。本單元只遷移自己碰到的兩個型別。

## T-2 三種抓取路徑對應三種畫面行為，互不共用旗標

既有程式碼只有一個 `isLoading`；本單元需要三種不同行為，故新增一個 `isBusy`，並讓第三種**不設任何旗標**：

| 路徑 | 旗標 | 畫面 |
|---|---|---|
| 初次載入 | 既有 `isLoading` | 整個容器替換為「載入中…」 |
| 切換頁次 | **新增** `isBusy` | 容器內「載入中…」，分頁控制留在畫面上 |
| 刪除後的背景重抓 | **無** | 完全不進載入態 |

**為何不共用**：`isLoading` 會把**整個容器**（含分頁控制）替換掉。沿用它做切頁，控制項會在游標下消失、鍵盤焦點退回頁面主體；沿用它做背景重抓，每刪一列整張表閃一次載入。這不是偏好問題 —— 前者讓 AC-5.10 必然失敗。

## T-3 分頁控制渲染在容器之外

結構前提，不是樣式選擇。既有的 `isLoading ? … : error ? … : (…)` 三元式替換的是**整個容器內容**；控制項留在容器內就會被一起替換掉。

## T-4 併發保護用遞增請求序號，不用 AbortController

application-design 允許兩者擇一。選序號的理由：

| 方案 | 判斷 |
|---|---|
| 遞增序號（採用） | 與既有的 `cancelled` flag 形狀同類（都是「回應抵達時檢查自己是否仍然有效」），一個 `useRef` 即可，不引入新概念 |
| `AbortController` | 會真的中止請求（省一點頻寬），但需要在三個抓取路徑各自持有並清理 controller，且與既有的 `.then/.catch/.finally` 形狀不如序號貼合 |

兩者對「只有最後發出的回應能寫入 state」這個不變量的保證相同。

## T-5 時間在地化用 `Intl.DateTimeFormat` 的 `sv-SE`

後端一律回 UTC，顯示端負責在地化（requirements C-5）。**直接截斷 ISO 字串是錯的** —— 那會讓顯示時間整體偏移一個時區位移量，AC-1.6 直接失敗而畫面看起來完全正常。

選 `sv-SE` locale 的理由：它的日期時間格式**恰為** `YYYY-MM-DD HH:MM`（AC-1.4 要求的格式），不需手動組字串。`Intl` 是平台內建，零依賴。

## T-6 44x44 觸控目標以 `md:` 前綴分岔

小螢幕 `min-w-11 min-h-11`（Tailwind 的 `--spacing: 0.25rem` × 11 = **44px**，已以專案自身的 Tailwind 實際編譯驗證），桌面回到既有小按鈕的密度。用既有 spacing scale 的既有值，不新增代幣。

> **查證依據更正**：本專案為 **Tailwind v4**，實際生效的設定是 `frontend/src/index.css` 的 `@theme`；`frontend/tailwind.config.js` **未被任何 `@config` 載入、是死碼**。早期的相關查證引用了那支不生效的檔案（數字碰巧正確），已更正。

## Review（三單元合併審查）

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-11T02:54:59Z
**Iteration:** 1

> 審查範圍：`user-object-serialization`（U2）、`api-type-contract`（U5）、`admin-page-column`（U3）三單元的 `nfr-requirements` 全部產出（含本檔）。`backend-activity-policy`（U1）、`security-reviewer-permission`（U4）不在範圍內，未讀取其目錄。

### 事實查證

| # | 查證項目 | 實際執行的指令／方法 | 結果 |
|---|---|---|---|
| 1 | U5 宣稱的規格統計（36 path／29 schema／68,951 bytes） | `python3 -c "json.load(open('openapi.json'))"` 數 `paths`／`components.schemas`；`wc -c openapi.json` | **相符**：36 paths、29 schemas、68951 bytes，逐位元與文件宣稱一致 |
| 2 | U2／U3「不引入新依賴」 | `git diff $(git merge-base HEAD ut) -- backend/requirements.txt frontend/package.json` | **相符**：`requirements.txt` 僅 `fastapi`／`pydantic` 由未版本約束改為 `==` 精確釘選（同一組既有依賴，非新增）；`package.json` 僅新增兩個 npm script（`gen:types`／`check:types`），`dependencies`／`devDependencies` 皆零異動 |
| 3 | U3 的 44px 主張（`min-w-11 min-h-11`） | 以專案既有 `@tailwindcss/cli` 對 `src/index.css` 實際編譯 `min-w-11`／`min-h-11` 的 probe class | **相符**：輸出 `calc(var(--spacing) * 11)`，`--spacing: 0.25rem`，11 × 0.25rem = 2.75rem = 44px |
| 4 | U5 T-4「型別檔進入 lint 作用域後維持 0 errors」 | `npm run lint`（含已 commit 的 `src/types/api.d.ts`） | **相符**：`0 errors, 3 warnings`，與 `team.md` 記載的既有 3 個 `exhaustive-deps` warning 完全相同，`api.d.ts` 未新增任何違規 |
| 5 | U5 S-2「產生器只輸出純 `.d.ts`」 | `wc -l src/types/api.d.ts`；grep 排除 `declare` 後的 `const`／`let`／`class` | **相符**：2385 行純 `interface`／型別宣告，零可執行陳述式 |
| 6 | U5 T-3「兩道漂移 gate 乾淨時 exit 0、刻意漂移時 exit 1」 | 直接跑 `backend/scripts/dump_openapi.py --check` 與 `npm run check:types`；各自先製造一次刻意漂移（改 `openapi.json` 一個 schema title／在 `api.d.ts` 尾端加一行）再還原，兩態都跑 | **相符**：乾淨態兩者皆 exit 0；刻意漂移態兩者皆 exit 1 且訊息指出應跑哪個指令；還原後複測回到 exit 0，工作樹已確認乾淨無殘留 |
| 7 | U5 S-3「該產生器目前沒有任何已發佈版本支援 TS 6，`npx` 為必要偏離」 | `npm view openapi-typescript@<7.7.0/7.9.0/7.10.0/7.12.0/7.13.0> peerDependencies`（7.13.0 為當時最新版）；`npm install --no-save --dry-run openapi-typescript@7.13.0`（專案 `typescript` 為 `~6.0.2`／已安裝 `6.0.3`） | **相符**：全部已發佈版本的 peerDependencies 皆為 `typescript: ^5.x`；`npm install` 確實重現 `ERESOLVE`，錯誤訊息與文件描述逐字相符 |
| 8 | U3 T-5「`sv-SE` 恰為 `YYYY-MM-DD HH:MM`」 | Node `Intl.DateTimeFormat('sv-SE', {...}).format(...)` 直接計算；核對 `LastActivityCell.tsx` 實作 | **相符**：輸出 `2026-08-11 22:05` 形狀，與 AC-1.4 要求格式一致，程式碼呼叫參數與文件描述相符 |
| 9 | U2 NFR-8 的測試「存在且非恆真」 | `cd backend && python -m unittest discover -s tests -v` | **相符**：140 個測試全數 `OK`，含 `test_illegal_parameters_are_rejected_without_leaking_data`、`test_negative_values_never_reach_the_query_layer`、`test_total_is_a_separate_count_not_len_items`、`test_same_page_twice_returns_same_order` 等文件引用的具名測試，皆確實存在且通過 |
| 10 | AD-11 引用的「SQLite `LIMIT -1`／負 `OFFSET` 行為」 | 直接對記憶體 SQLite 探針執行 `LIMIT -1 OFFSET 3`／`LIMIT 5 OFFSET -5` | **相符**：20 列表中，`LIMIT -1 OFFSET 3` 回 17 列（整表剩餘）、`LIMIT 5 OFFSET -5` 回 5 列，與 AD-11 原文數字逐一相符 |
| 11 | U2 T-1「`minimum`／`maximum` 確實出現在 OpenAPI 規格中」 | `python3` 讀 `openapi.json` 的 `/api/auth/list` GET `parameters` | **相符**：`page.schema.minimum=1`；`page_size.schema.minimum=1,maximum=100` |
| 12 | U5「只產出 2／5 份文件」是否為 `produces_kinds` 允許的判斷，而非湊巧漏產 | 讀 `.claude/aidlc-common/stages/construction/nfr-requirements.md` frontmatter 的 `produces_kinds`；核對 `unit-of-work.md` 的 U2=service／U3=ui／U5=packaging | **相符**：`performance-requirements`∈[service,ui]、`scalability-requirements`／`reliability-requirements`∈[service]，`security-requirements`／`tech-stack-decisions` 未受 kind 限制（全 kind 皆須產出）。三單元實際產出的檔案集合與此逐項吻合，U5 僅產 2 份是規則允許的判斷，不是缺工 |
| 13 | `upstream-coverage` sensor（本站 `consumes: business-logic-model, business-rules, requirements`，皆 `required: true`） | 直接執行 `bun .claude/tools/aidlc-sensor-upstream-coverage.ts`，對三單元的 `tech-stack-decisions.md`（含同目錄全部 deliverables）分別以裸 slug 與 `slug:producer`（`functional-design`）兩種形式跑；另以 `grep -rn "BR-P"` 複驗是否真的完全零引用 | **三單元皆 FAIL**：`business-logic-model`／`business-rules` 在任何形式（裸詞、wikilink、backtick 檔名、producer 目錄片段）下皆未被引用；`grep BR-P` 全域零命中。`requirements` 一項三單元皆通過 |
| 14 | U2 T-2／U5 T-2 對 `fastapi`／`pydantic` 精確釘選的交叉引用是否對得上 | 讀 `requirements.txt` 實際內容；核對兩份文件互相引用的段落文字 | **相符**：兩份文件對同一組版本號（`0.141.1`／`2.13.4`）與釘選理由描述一致，無矛盾 |
| 15 | U2／U5／U3 對 AD-9／AD-10／AD-11／AD-12 的技術主張轉述 | 讀 `inception/application-design/decisions.md` 對應章節逐句核對 | **相符**：三單元對 offset 分頁、框架原生範圍約束、刪除後就地移除＋背景重抓、三種抓取旗標等主張的轉述與來源決策一致，無失真 |

### Findings

| # | Severity | Unit | Location | Finding | Recommendation |
|---|---|---|---|---|---|
| 1 | Major | U2／U5／U3（三單元一致） | 各單元 `nfr-requirements/` 全部產出 | `upstream-coverage` sensor 對三單元皆回報 FAIL（見事實查證 #13）：本站 frontmatter 明列 `business-logic-model`／`business-rules` 為 `required: true` 的上游輸入，且 Step 2 明文要求讀取 `functional-design/` 產出，但三單元的 NFR 文件全篇零引用這兩份上游 artifact（無論以檔名、wikilink 或 `BR-P` 規則 ID 形式）。內容本身站得住腳（`requirements`／`application-design` 的追溯鏈完整、實測扎實），但與同一 intent 其他 stage（`requirements-analysis`、`functional-design`）已建立的高強度可追溯慣例不一致，且是三單元共同的系統性缺口，非單一單元疏漏 | 下一輪小步修訂時，在每單元至少一份文件（建議 `security-requirements.md` 或本檔）補上對應的 `functional-design/business-rules.md`／`business-logic-model.md` 具體規則 ID 引用（例如 U2 的 R-3／R-4 可直接掛 `BR-P2`／`BR-P3`，U3 的 T-2／T-4 可掛其對應的 `UserListPage` 前端規則 ID）。此 sensor 本身為 `advisory` 級，不構成本輪 NOT-READY 理由 |
| 2 | Minor | U5 | `security-requirements.md` S-1 | 「規格檔／型別檔不得落在會被靜態服務原樣供出的路徑」有明確威脅模型與契約，但驗證手段誠實記載為「目前沒有自動化執行」，僅靠檔案位置的天然安全形狀防護，人工疏失（如日後誤放進 `frontend/public/`）不會被任何 CI gate 攔下 | 可在 CI 的 frontend job 加一行機械檢查（`grep -r "openapi" dist/ && exit 1` 之類），把「天然安全」升級為「機械保證」；非阻塞，可併入下一次工具鏈調整 |
| 3 | Minor | U5（與上游 AD-9 的交叉一致性） | `inception/application-design/decisions.md` AD-9「Consequences」段 vs. U5 `security-requirements.md` S-3 | AD-9 的「負面」清單仍逐字寫著「新增一個 devDependency（這正是 AD-5 原本要避免的）」，但 U5 S-3 記載的最終實作**沒有**新增 devDependency（改採釘住版本的 `npx`）。依 `project.md ## Corrections` 的既有規則，下游不回改已核可的上游 artifact 是正確處置，S-3 也已如實記載偏離與理由，故不構成違規；但只讀 AD-9 本身的讀者會被那句「新增一個 devDependency」誤導 | 非阻塞。若後續有機會小步觸碰 AD-9，可在該段落補一句指向 U5 S-3 的交叉引用（不改寫 AD-9 原文本身，僅加註記） |

### Summary

三份合併審查涵蓋的所有可查證陳述（規格統計、44px 編譯結果、lint 結果、兩道漂移 gate 的即時紅／綠、`npx` 偏離的技術理由、`sv-SE` 格式、SQLite 邊界行為、OpenAPI 參數約束、NFR-8 測試存在性與可測性）逐一實測後**全數屬實**，無一項虛假或誇大；U5 只產出安全與技術選型兩份文件，經核對 `produces_kinds` 後確認是規則允許的正確判斷而非規避。唯一的系統性缺口是三單元一致缺乏對 `functional-design` 上游（`business-logic-model`／`business-rules`）的明確引用，`upstream-coverage` sensor 三戰三敗，判定 Major 但不足以阻擋 READY（該 sensor 本身為 advisory，且 0 Critical、≤2 Major 不擋 READY）。

- **U2 `user-object-serialization`：READY** —— 五份文件內容扎實、測試真實存在且非恆真、與 AD-9/10/11/12 逐句相符，唯缺上游規則引用（Finding 1）。
- **U5 `api-type-contract`：READY** —— 僅產 2/5 文件為 `produces_kinds` 正確判斷而非湊數；`npx` 偏離的技術理由（TS 6 不相容）獨立查證屬實；兩道漂移 gate 現場複驗皆真的會紅；唯缺上游規則引用（Finding 1）、`dist/` 洩漏檢查尚無自動化（Finding 2，Minor）。
- **U3 `admin-page-column`：READY** —— 44px、`sv-SE`、零新依賴、三旗標狀態機皆與程式碼及 AD-12 一致；唯缺上游規則引用（Finding 1）。

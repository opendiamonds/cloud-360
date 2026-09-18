# Test Case Management Plan — Cloud-360

- Status: Decided（工具已定：Kiwi TCMS 自架；實作進行中）
- Date: 2026-07-13
- Decision: 2026-07-13 選定 **Kiwi TCMS（自架）**，理由見第 3 節；SaaS 方案（Qase）與 TestLink 已否決。
- 關聯：[[ui-regression]] workflow、`frontend/tests/e2e/regression.spec.ts`、user stories（A1/A2/A4/Pillar J）

### 1. 目標與現況

目標：建立一套能同時管理**自動化測案**與**未來手動測案**的測案管理機制，並提供跨時間的**通過率趨勢儀表板**與**需求↔測案的追溯**。

現況（已具備）：
- 自動化測案 = 程式碼：`frontend/tests/e2e/regression.spec.ts`（6 個核心免-LLM 案例）。
- 執行：每個 PR 由 `.github/workflows/ui-regression.md` 起臨時 stack 跑 Playwright，agent 在 PR 留言失敗案例。
- 結果：GitHub Checks（單次 pass/fail）+ `pw-report.json` artifact。

缺口：
- 沒有跨 run 的**歷史通過率趨勢 / 儀表板**。
- 沒有**手動測案**的登錄、執行與紀錄能力（未來需求）。
- 沒有**需求↔測案↔結果**的追溯矩陣。

### 2. 核心原則：每種測案有單一真實來源

| 測案類型 | 真實來源 | 執行 | 結果去向 |
|---|---|---|---|
| 自動化 | Playwright spec（repo code） | GitHub Actions（PR 觸發） | Checks + TCM 儀表板 |
| 手動（未來） | TCM 平台 | TCM 的 test run（人工執行） | TCM 儀表板 |

自動化測案**不搬進** TCM 當主檔（會造成雙份維護）；TCM 只保存自動化案例的**中繼資料與歷史結果**，本體仍是 code。手動測案則以 TCM 為主檔。兩者在同一個儀表板匯總。

### 3. 工具選型（關鍵決策）

需要一個能容納「手動 + 自動 + 儀表板 + 追溯」的 TCM。兩條路：

**方案 A — Kiwi TCMS（自架，建議）**
- 開源、可 Docker 自架，與現有 192.168.10.10 基礎設施一致（可用剛建好的部署管線 + Cloudflare Tunnel 上線）。
- 支援手動測案、測試計畫、test run、需求追溯、API 匯入自動化結果。
- 資料留在自有主機，符合本專案「不外送、避免外部 SaaS 依賴」的範圍紀律（ADR-0001）。
- 代價：需自行維運（多一個服務）；自動化整合走 API，較 Qase 的原生 reporter 費工。

**方案 B — Qase（SaaS 免費方案）**
- 上手最快、`qase-playwright` reporter 自動回寫每次 run、儀表板與趨勢開箱即用。
- 代價：資料進外部 SaaS、免費方案有額度上限、多一個外部帳號與 API token。

**決定（2026-07-13）**：採方案 A（Kiwi TCMS 自架）。

**Repo 邊界（重要）**：Kiwi TCMS 屬**共用基礎設施**，不是 Cloud-360 產品碼，因此**在 `opendiamonds/dc-infra` repo 佈建與維運**（該 repo 是 danniel.cc 所有 staging 服務的 Cloudflare Tunnel IaC）。Cloud-360 這邊**只保留**：
- 本測試策略文件；
- 自動化測試 code（Playwright）；
- 未來在 `ui-regression` workflow 中「把結果回寫到 Kiwi API」的整合步驟與 API token secret。

TCMS 服務本身的 compose、tunnel（`dc-tcms` → `tcms.danniel.cc`）、DNS、以及「新增此對外服務」的 ADR/決策記錄，**都在 dc-infra**，不在 Cloud-360。

### 4. 整合架構

```text
自動化：PR → ui-regression → Playwright → pw-report.json
                                   │
                                   └── (reporter/API) ──► TCM test run（自動）
手動：  release 前 → TCM 手動 test run（人工執行）
                                   │
              兩者匯入同一 TCM 專案 ──► 儀表板（通過率趨勢、flaky）
                                   └► 追溯：TCM case ⇄ user story（A1/A2/A4/J…）
```

- 追溯：TCM 每個 case 加一個「story_id」欄位，對應 `aidlc-docs/inception/user-stories/stories.md`。
- 自動化回寫：在 Playwright 每個 test 加註 case 對應 id（annotation），run 後把結果推到 TCM。

### 5. 分階段落地

- **Phase 0（現在）**：維持 Playwright + Checks 現狀；定案工具（方案 A/B）。
- **Phase 1**：建 TCM 專案，測試套件結構鏡射 AIDLC pillar（A1/A2/A4/J）；把現有 6 個自動化案例登錄為 TCM case，接上自動回寫（API token 存為 GitHub secret）。
- **Phase 2**：為未自動化的流程撰寫**手動測案**（例如 A1 自然語言生成架構圖 —— 這條在 CI 刻意跳過，因為會呼叫 OpenRouter 產生費用），建立每次 release 的手動 test cycle。
- **Phase 3**：儀表板 + 追溯矩陣（story ⇄ case ⇄ result）；可選加一支 gh-aw agent，在 release 時彙整測試覆蓋摘要。

### 6. GitHub 與 TCM 的分工

- **GitHub**：自動化測試 code、CI 執行、PR gating（自動化在 PR 上的 pass/fail 真實來源）。
- **TCM**：測案目錄（手動 + 自動中繼資料）、測試計畫、手動執行、跨 run 趨勢儀表板、追溯矩陣。

### 7. 待決事項

1. 工具：方案 A（Kiwi 自架）或 B（Qase SaaS）？
2. 是否為此開新 ADR（自架納 scope／SaaS 資料外送）？
3. 追溯粒度：case 對應到 story（A1）即可，或需細到 acceptance criteria？

> 第 1 項已於第 3 節定案為方案 A（2026-07-13），此處為撰寫時的殘留，保留原文不回改。第 2、3 項仍待決。

---

### 附記（2026-08-16）：Phase 2 的承載機制已落地

第 5 節的 Phase 2「為未自動化的流程撰寫手動測案」原本只是規劃，沒有承載它的機制——手動測案要不要寫、寫成什麼樣、由誰在什麼時候寫，都沒有落點。現已補上：

| 元件 | 位置 | 作用 |
|---|---|---|
| `tcms-test-cases` stage | `.claude/aidlc-common/stages/construction/tcms-test-cases.md` | `tcms` plugin 的 construction 階段 stage，`execution: ALWAYS`、涵蓋全部 scope |
| Blocking 規則 | `aidlc/spaces/default/memory/project.md` `## Mandated` | 未完成不得標示該 stage 為完成，亦不得進入部署階段 |
| 撰寫標準 | `aidlc/spaces/default/knowledge/aidlc-quality-agent/test-case-authoring.md` | 分流判準、格式契約、步驟品質標準、自動化落點、突變驗證 |
| 同步工具 | `scripts/tcms_sync.py` | 解析 stage artifact 寫入 TCMS，以標題為鍵、可重跑 |

**第 2 節的「單一真實來源」原則在新機制中是硬約束**：stage 要求先做覆蓋盤點，把每個行為分類為「已自動化／待自動化／只能手動」，並明文禁止為自動化層已斷言的行為另寫手動案例。

第 3 節指出的 repo 邊界不變：TCMS 服務本身仍在 `dc-infra` 維運，本 repo 只有測案內容、自動化 code 與同步整合。

Phase 1 的自動化案例回寫（junit plugin）與 Phase 3 的儀表板／追溯矩陣不受影響，仍依原規劃進行。

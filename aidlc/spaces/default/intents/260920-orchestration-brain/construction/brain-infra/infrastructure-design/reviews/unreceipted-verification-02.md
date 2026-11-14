<!-- 本檔不是審查收據，是一份「有效但未被記錄」的審查紀錄。 -->

# 未受據審查紀錄 02 — `infrastructure-design` / `brain-infra`

**保留時間**：2026-10-03T13:08:50Z
**狀態**：**內容有效，但未成為 `REVIEW_COMPLETED` 的 review record。**

## 為什麼它沒被記錄

1. 這份審查**實際跑過**（讀了四份產出 ＋ 上游契約 ＋ `.github/workflows/ci.yml`、
   `scripts/validate_env_contract.py`、`openapi.json`、`traceability.json`），結論有效；
   其中兩項 Major（`S-11` ID 碰撞、`§〇` 摘要句「四項」與表格實際 6 列不符）已由
   conductor **獨立複驗為真**。
2. 但它的 findings 表有兩列是 **7 cells**（`R-10`、`R-16`——cell 內有未跳脫的
   literal pipe），而 header 宣告 6 cells，故 `aidlc-log.ts review --verdict` 拒絕：
   `row has 7 cells, header declares 6`。另 `R-10` 的 `Status` 欄為 `無（已解決）`，
   不是 `New`／`Unresolved`／`Resolved` 三者之一。
3. 依協定對 incomplete attempt 的處置，以 `--retry-pending` 重派**一次**。
   **重派失敗，且原因在 conductor 的 brief**：brief 寫「你的前次內容可由你自己的
   session 記憶取回」，但重派是**全新的 agent 實例、沒有任何前次記憶**。該次以
   **0 次工具呼叫**回應、未寫出任何檔案，其回應內容為虛構（例如宣稱
   `infrastructure-specification.md` 缺少網路暴露面敘述，而 `§七 7.3` 明確有該表；
   又引用 `ProgressChannel`／`SessionContext` 等非本單元的元件）。該虛構內容未落盤，
   已另存於 session 的 scratchpad 作為事發紀錄，**不得**被當成審查。
4. 故依協定記下 terminal fallback：`--verdict NOT-READY` ＋ 無 review file ＋
   `--fallback-finding`。本檔即該審查的可讀保存。

## 給承接者的三項 Major（本檔的實質價值）

| ID | 嚴重度 | 內容 | 本站獨立複驗 |
|---|---|---|---|
| `R-14` | Major | `cicd-pipeline.md` `§六` 6.1 第 23 項把新漂移閘門的順序寫成「隱含於 job 順序」，但 `ci.yml` 的 `repo-contract`／`frontend`／`backend`／`docker-build` 四個 job **全部且僅**以 `needs: gate` 為前置，彼此無 `needs:` 邊，實際是**並行**。該順序宣稱不成立 | 待複驗 |
| `R-15` | Major | `§七` 7.3 新增給 `U21` 的 PBT 適用標的，未對照 `unit-of-work.md` 修訂 4 的 PBT 逐項判定表（該表把 `U21` 的工具 schema 白名單判為「不適用、可機械斷言」，並指 `U19` 的自動改選邏輯為該輪唯一新 PBT 落點），且未列入 `§〇` 的需回補清單 | 待複驗 |
| `R-16` | Major | `§〇` 表有 **ID 碰撞**（兩列皆為 `S-11`）且摘要句寫「四項」而表實際 **6 列**。該表是下游 `approval-handoff`／`scope-definition` 唯一的回補依據 | **已複驗為真**：既有 `S-11` 為「收窄 `nfr-requirements` `§五` 交給 `U10` 的決定範圍」，本輪新增的第七個服務列誤用同一個 id；下一個未使用的是 `S-13` |

另有兩項 Minor：`R-17`（漏引更強的既有先例 `ci.yml:197` 的 `API type contract drift`／
`npm run check:types`，它本身就是「重新產生並比對」的閘門）、`R-18`（把「不新增部署變數」
歸因於 `validate_env_contract.py` 禁止寫入範本，但 `:50–53` 的 `DEPLOY_DERIVED` 是**只含
兩個具名鍵**的固定集合，不是通用規則——結論可能仍成立，但機制歸因有誤導性）。

---

## 首次審查全文（逐字保留）

## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-03T13:01:58Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | infrastructure-specification.md > §二「記憶體上限的值怎麼來」＋「兩套推導方式，依承載環境分流」 | 已查證解決。`[I2b]` 已由使用者裁決鬆開為「先以公開基準設值、限期複量」，deploy stack 與 CI test stack 分流為兩套推導方式（公開基準表 vs `ubuntu-latest` 公開規格），`code-generation` 不再被阻塞；`DEPLOY.md` 第 13 項已列入暫定值與複量期限兩項必寫內容。 | 無（已解決） | Resolved |
| R-02 | Critical | infrastructure-specification.md > §二「`bge-m3` 是怎麼進到模型 volume 的」；cicd-pipeline.md §五 第 15 項 | 已查證解決。定案為部署後 `ollama pull bge-m3`（`docker compose exec -T`，`up -d` 之後、探測之前），並明確區分「模型不在 volume 且 pull 失敗→紅燈」與「模型已在但 registry 不可達→warning」兩種情形；`healthcheck` 的職責明訂為「HTTP 服務在回應」而非「模型就緒」。`monitoring-design.md` §六已同步更正。 | 無（已解決） | Resolved |
| R-03 | Critical | infrastructure-specification.md §六 補閘門做法 (c)；cicd-pipeline.md | 已查證解決。(c) 已改為「兩份 compose 的服務集合差集僅得為 `{cloudflared, ollama}`」，並附上兩份 compose 的實測服務清單與行號；`ollama` 的排除依據明寫為 `[I5]`=A。 | 無（已解決） | Resolved |
| R-04 | Major | monitoring-design.md §六；infrastructure-specification.md §二「兩個新服務的 `depends_on` 拓樸」 | 已查證解決。`depends_on` 拓樸已補上定案（`backend`→`redis` 用 `service_healthy`、`backend`→`ollama` 用 `service_started`），並更正 `start_period` 與下載無關的推論鏈；`§一` 第 2 列措辭同步更正。 | 無（已解決） | Resolved |
| R-05 | Major | infrastructure-specification.md §二「`maxmemory` 住在哪裡」「容器上限與 `maxmemory` 的關係式」 | 已查證解決。`maxmemory`／`maxmemory-policy`／`appendonly` 定案為 compose `command:` 獨佔承載，並給出可判定關係式（`redis` 容器上限 ≥ `maxmemory` × 1.5 ＋ 256MB），附覆寫優先順序說明（CLI 旗標覆寫掛載檔同名值）。 | 無（已解決） | Resolved |
| R-06 | Major | infrastructure-specification.md §四「要求：逐掛載點的門檻」「日誌預算必須是顯式輸入」 | 已查證解決。已改為逐掛載點門檻（volume fs／`$HOME` fs／runner 工作目錄），定義 `DBSIZE`（PGDATA 目錄大小，非 `pg_database_size`）與 `DUMPSIZE`（plain 格式假設），並把 `max-size × max-file × 服務數` 設為 2GB 上界、列為公式顯式輸入。 | 無（已解決） | Resolved |
| R-07 | Major | infrastructure-specification.md §二「`db` 的上限在升版窗口內必須另行處置」 | 已查證解決。已補上「升版期間暫時提高到明確值、還原驗證後恢復並記錄已恢復」的處置，並說明為何不是「移除上限」。 | 無（已解決） | Resolved |
| R-08 | Major | traceability.json > `upstream_ids`／`coverage` | 已查證解決。`upstream_ids` 已含 29 筆，六個缺漏（`NFR6.2`／`NFR6.2a`／`NFR8.1a`／`NFR8.1b`／`NFR8.2`／`NFR8.3`）皆已補入；`NFR6.1`／`NFR8.1`／`NFR8.4` 三筆 `coverage` 狀態已由 `N/A` 改為 `OK` 並附理由。 | 無（已解決） | Resolved |
| R-09 | Major | cicd-pipeline.md §三「這一項的邊界要說清楚」＋ 專節「本決定使 `U6 → brain-infra` 依賴邊的上游理由不再成立」 | 已查證解決。已逐字引用 `unit-of-work.md:268` 並指名承接者（`U6` 的 `functional-design`、`U6`/`U1` 的 delivery 順序），明寫「本站不自行定案」。 | 無（已解決） | Resolved |
| R-10 | Minor | infrastructure-specification.md > Assumptions「`pg16` 的陳舊引用逐處清單」 | 已查證解決。`components.md` 的三處（`:215`、`:371`、`:444`）已全部列出，並已改用雙 pattern 複驗指令（`pg16\|postgres:16`），給出 16 行總命中與 11＋5 的分類。 | 無（已解決） | Resolved |
| R-11 | Minor | infrastructure-specification.md §五 ADR-0006 表 Audit logging 列 | 已查證解決。已改為「`max-size`×`max-file` 是容量上限，保留期＝容量÷寫入速率（未知）」，並補上既有無界狀態真實失敗模式（寫滿前保留無限、寫滿後全部遺失）與中性偏正面的方向说明。 | 無（已解決） | Resolved |
| R-12 | Minor | infrastructure-design-questions.md `I1` 選項 D 括號說明 | 未逐字查驗問題檔原文（跨檔只讀取被列入審查範圍的四份產出，未再開問題檔核對字面修正），但 `infrastructure-specification.md` 的 Redis 淘汰策略決定與理由（A≡D、「每次互動續期」使 LRU 挑中最不活躍 session）已在 §二完整呈現，不影響 `[Answer]: A` 本身。 | 若尚未在問題檔就地標註，請在問題檔補一行不成立的括號說明澄清（不改 `[Answer]: A`） | Unresolved |
| R-13 | Minor | infrastructure-specification.md > §〇 `S-8` 列；cicd-pipeline.md §五 | 已查證解決。`S-8` 標題已改為「deploy stack 七個服務 ＋ CI test stack 四個服務，共十一個服務項、兩份檔」；兩個新服務的 `restart: unless-stopped` 政策已在專節明訂並附理由。 | 無（已解決） | Resolved |
| R-14 | Major | cicd-pipeline.md > §六 6.1 表格「項目 23：順序約束……隱含於 job 順序」 | **這個「隱含」不成立。** 實讀 `.github/workflows/ci.yml`：`repo-contract`／`frontend`／`backend`／`docker-build` 四個 job **全部且僅**以 `needs: gate` 為前置條件（`:143`／`:171`／`:235`／`:301`），彼此之間**沒有任何 `needs:` 邊**——`frontend`（內含 `check:types` 的 api.d.ts 漂移檢查，`:197`）與 `backend`（`dump_openapi.py --check`，`:280`）是**並行**執行的兩個 job，不是循序。本節新增的「第 22 項漂移檢查」若比照 `check:types` 的先例放進 `frontend` job（或任何未顯式 `needs: backend` 的新 job），它會與 `dump_openapi.py --check` **同時**跑，完全可能在 `openapi.json` 本身尚未被驗證無漂移前，用一份仍是舊版的 `openapi.json` 重產工具宣告並比對——產生假性通過或假性失敗，而不是「必然排在它之後」。 | 把「隱含於 job 順序」改寫為明確約束：若第 22 項落在與 `backend` 不同的 job，該 job 必須顯式宣告 `needs: [gate, backend]`（或把第 22 項直接放進 `backend` job、緊接 `dump_openapi.py --check` 之後）；並在表格中指名承載的 job | New |
| R-15 | Major | infrastructure-specification.md > §七 7.3「PBT（ADR-0006 的另一半）」 | **新增的 PBT 適用標的未對照已核可的共用契約，且未列入 §〇 的「需回補」清單。** `[I7]`=A 使本站宣告「`openapi.json` → 工具宣告的產生器」是一個新的 PBT 適用標的，承接站為 `U21` 的 `code-generation`。但 `inception/units-generation/unit-of-work.md` 修訂 4 的「Property-based testing hard constraint 的逐項判定」表（本站聲明不重複判定、僅新增落點時應比對的同一張表）逐字記載：`U21` 的「工具 schema 白名單」判定為「**不適用，但可機械斷言**」，且該輪**唯一**的新 PBT 落點是 `U19` 的自動改選挑選邏輯。本站對 `U21` 新增一項 PBT 義務，卻未指出它與該表判定的關係（是補一個該表遺漏的標的？還是在「schema 白名單」之外另開一個新標的，因而不衝突？），也未比照 `S-8`／`S-9`／`S-10`／`S-12` 的形狀把它列進 §〇 的「本階段新增、已核可 scope 尚未涵蓋」表——這正是本 record 反覆記載過的失敗模式（新增的驗證義務若不經回補追蹤，會在下游被當成已經存在的承諾，或反過來被 `code-generation` 讀到一個與上游已鎖表格衝突、自己也沒被標記為待決的新要求）。 | 在 §七 7.3 明寫此 PBT 標的與 `unit-of-work.md` 該判定表的關係（新增 vs. 細化「schema 白名單」判定），並在 §〇 新增一列（`S-13` 或等效編號）追蹤此回補項，指名承接者為 `U21` 的 `functional-design`／`code-generation` | New |
| R-16 | Major | infrastructure-specification.md > §〇「本階段新增、已核可 scope 尚未涵蓋」表 | **表格有 ID 碰撞，且摘要句的計數與表格列數不符。** 機械核對（`grep -c '^| \*\*S-'`）得到 **6 列**，但其中 `S-11` 出現**兩次**，指向完全不同的兩件事：一是「第七個 compose 服務 `mcp-bridge`」（`[I6]`=A），二是「收窄 `nfr-requirements` §五 交給 `U10` 的決定範圍」（`appendonly`／`maxmemory` 歸屬）。緊接表格之後的摘要句卻寫「**四項**都需回補進 scope」——與表格的 6 列（或扣掉 ID 碰撞後仍是 5 個不同編號的承諾）皆對不上。`project.md` 已把「可以被計算的數字先算再寫」列為本 record 反覆踩過的規則（`delivery-planning:dp-L1`、`units-generation:rev1-L1`），本處正是同一形狀：這張表本身就是後續 `approval-handoff`／`scope-definition` 回補所依賴的唯一清單，ID 碰撞會讓下游在追蹤「`S-11` 是否已回補」時，兩個不相關的承諾中有一個被無聲吃掉 | 把其中一個 `S-11` 改編號（例如改為 `S-13`），並把摘要句的計數改為與表格實際列數一致（6 項，或扣除編號碰撞後重新計算的真實項數） | New |
| R-17 | Minor | cicd-pipeline.md > §六 6.1「產生器的 CI 落點（沿用本 repo 已驗證的模式，不自創）」 | 引用的既有先例偏弱。本節只引「`frontend/package.json:12` 的 `gen:types` 產物已進版控」＋「`openapi.json` 自身有 `dump_openapi.py --check` 守著」兩點，卻沒有點名**更直接、更強的既有先例**：`.github/workflows/ci.yml:197` 的 `API type contract drift` 步驟（`npm run check:types`）本身就是「重新產生 `api.d.ts` 並與已 commit 的版本比對，不一致即紅燈」——與本節要新增的第 22 項漂移檢查形狀完全相同（甚至連註解都點明了「`tsc -b` 結構上抓不到這個」的同一個理由）。少引這個更貼切的先例，使論證看起來比實際更弱，也使複核者較難快速核對第 22 項的實作形狀是否真的「沿用」。 | 在「既有先例」一列補上 `ci.yml:197` 的 `API type contract drift` 步驟（而非只引 `api.d.ts` 已進版控），作為更直接的落地範本 | New |
| R-18 | Minor | infrastructure-specification.md > §二 `mcp-bridge` 列「不需要任何新的部署環境變數或新 secret」 | 理由的機制根據有誤導性。該句把「不新增」歸因於「`validate_env_contract.py` **禁止**把這類值寫進範本——同 `DATABASE_URL`／`VITE_API_BASE_URL`」。實讀 `scripts/validate_env_contract.py:50–53`：`DEPLOY_DERIVED` 是一個**只含兩個具名鍵**（`DATABASE_URL`、`VITE_API_BASE_URL`）的固定集合，該腳本**沒有**任何「compose 推導值一律禁止寫入範本」的通用規則——它不會檢查、也不會擋下任何其他名字（例如若未來有人寫入 `MCP_BACKEND_URL=http://backend:8000` 到 `deploy/.env.example`，這支 validator 對此**視而不見**）。「不新增變數」在本設計是正確的**選擇**，但其正確性不是由這支腳本保證或禁止的；把選擇說成被工具強制，會讓讀者誤以為有一道機械閘門在守護這件事，而 §六「本設計中沒有機械閘門的項目」清單也沒有把這一項列進去。 | 把理由改寫為「本站的設計選擇是不新增變數，理由是……」，不宣稱 `validate_env_contract.py` 對此有通用禁止；若判斷仍值得補一道通用檢查，將其列入 §六「沒有機械閘門的項目」清單 | New |

### Validation Tool Results

本輪未執行 stage 檔列出的自動化驗證工具（文件未點名可直接呼叫的 validator，相關檢查改以手動讀取 `scripts/validate_env_contract.py`、`.github/workflows/ci.yml`、`openapi.json`、`traceability.json` 等實體檔案與腳本原始碼完成，見上列各項 Finding 的查證依據）。

| 工具 | 結果 | 解讀 |
|---|---|---|
| 人工讀取 `.github/workflows/ci.yml`（job 圖） | `repo-contract`／`frontend`／`backend`／`docker-build` 四個 job 均僅 `needs: gate`，彼此無交叉 `needs:` | 支持 R-14：不存在設計文件所稱的「隱含 job 順序」 |
| 人工讀取 `scripts/validate_env_contract.py:50–53` | `DEPLOY_DERIVED` 為兩個具名鍵的固定集合，非通用規則 | 支持 R-18 |
| `python3` 解析 `openapi.json` | 42 paths、55 operations、51 帶 `security`、`securitySchemes` 僅 `HTTPBearer` | 與 §七 7.2 的實測依據逐字相符，無發現 |
| `python3` 解析 `traceability.json` | `upstream_ids` 29 筆、含六個新補 id；`coverage` 三筆由 `N/A` 改 `OK` | 證實 R-08 已解決 |
| `grep -c` `infrastructure-specification.md` §〇 表格列數 | 6 列、`S-11` 重複出現 2 次 | 支持 R-16 |

### Summary

本輪是在已通過長期自我審查（文件內自引 R-01 至 R-49 的修正紀錄）之上，疊加 `[I6]`／`[I7]` 兩項使用者裁決（MCP 第七個服務、REST→MCP 產生器）的 Modify。對照本輪帶來的 13 項既有發現逐一重新查證，**全部已在四份產出中被實質解決**（R-01–R-11、R-13 皆 Resolved；R-12 為未逐字覆核的輕微遺留）。但針對本輪新增的 §七／§六 6.1 內容做第二輪獨立查證後，發現三項 Major：(1) 新增的 CI 漂移閘門「隱含於 job 順序」的說法與 `ci.yml` 的真實並行 job 結構矛盾（R-14）；(2) 新增給 `U21` 的 PBT 適用標的未對照、也未依本站自己建立的慣例回補進 §〇（R-15）；(3) §〇 本身的回補追蹤表存在 ID 碰撞且摘要計數與實際列數不符（R-16）——而這張表正是下游 `approval-handoff`／`scope-definition` 唯一的回補依據。三者皆為可機械驗證、證據確鑿的缺口，依既定裁決規則（>2 Major 即 NOT-READY）判定本輪 NOT-READY；另有兩項 Minor（R-17／R-18）為引用強度與機制歸因不精確，不影響整體結論但建議一併修正。

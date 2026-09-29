<!-- 這份副本是手動複製的，不是 `aidlc-log.ts review --verdict` 產生的正式副本。
     原因：conductor 在記錄議決之前就先改了產出檔，導致議決無法綁定到審查當時的位元，
     補記被引擎正確拒絕。審查確實跑過（NOT-READY，5 Major／3 Minor），八項 findings 全部已處置，
     但這一站在稽核紀錄上沒有 REVIEW_COMPLETED 收據。此事已向使用者揭露並由其裁決
     （選擇降低審查要求而非花 redo 的代價重置整個 Construction 的收據）。
     檔名帶 -unrecorded 是刻意的，避免它被誤讀成正式收據的副本。 -->

## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-28T11:24:56Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-data/nfr-design/security-design.md > §〇 最後一行，以及 traceability.json > coverage `U4-R4` 的 target | `OQ-3` 被宣告「已在此結案」，但 `OQ-3` 自身的主題不是本單元。`requirements.md:597` 逐字：「OQ-3 \| episodic memory 的加密手段（靜態與傳輸）—— NFR7」，`requirements.md:385` 的 `NFR7` 逐字只談 episodic memory；本單元自己的 `nfr-requirements/security-requirements.md:57` 也逐字寫「**`OQ-3` 自身文字只涵蓋 episodic memory**，故此擴充已具名為 `S-4`」。本站真正結案的是 `S-4`（`requirement_summary`／`requirement_label` 兩欄），不是 `OQ-3`。同一份檔的 §四 `S-10` 又寫「`OQ-3` 的 `U5` 那一半不受本站答案約束」——**「已結案」與「一半未綁定」在同一份產出裡直接對撞**。後果不是措辭問題：`requirements.md:597` 指定的落點是 stage `nfr-design`，而 `U5` 的 `nfr-design` 是 `CONDITIONAL`；一旦它被 skip，紀錄上 `OQ-3` 已結案，就沒有人會再去找承接站 | 把 §〇 與 `U4-R4` 的 target 改寫為「本站結案的是 `S-4`（本單元兩欄）；`OQ-3` 本體（episodic memory）未結案，其落點仍為 `U5` 的 `nfr-design`」，並在 §四 的 `S-10` 明寫「若 `U5` 的 `nfr-design` 被 skip，`OQ-3` 即無承接站，判定 skip 的人須重新提交給使用者」 | New |
| R-02 | Major | .../hierarchy-data/nfr-design/security-design.md > §一 Audit logging 列「`Q3=A` 的強化」與 §二；traceability.json > coverage `SEC-4` status `OK` | 宣稱 `Q3=A` 把 `SEC-4` 由有條件變成成立的保證（「要麼有可信的行動者，要麼這次異動根本沒發生」）。逐字核對上游的條件：`nfr-requirements/security-requirements.md:70-72` 要求「**存進去的值必須指向真正造成這次異動的人，不得預設填工作階段的擁有者**」，並在 `:202` 的殘餘表逐字記「`SEC-4` 的稽核保證在 `OQ-H3` 定案前不成立」。`Q3=A` 只處理「解不出行動者」這一支；「U12 解出了一個值、但那個值是預設的工作階段擁有者」這一支完全沒被碰到——而那正是上游點名要避免的情形。本站也沒有定義「可信」的判準，判準就是 `OQ-H3`，而 `OQ-H3` 未定案。故條件性沒有消失，只是換了位置 | 把該格改寫為「`Q3=A` 補上了失敗分支，但 `SEC-4` 第 (4) 項仍以 `OQ-H3` 為條件：本站未定義何謂『解出』，『解出但指錯人』仍不可偵測」，並把 `SEC-4` 的 status 由 `OK` 改為 `Deferred`（或保留 `OK` 但在 target 內明列尚未涵蓋的分支）；同時把「不得預設填工作階段擁有者」作為對 `U12` 的約束併入 `S-11` | New |
| R-03 | Major | .../hierarchy-data/nfr-design/security-design.md > §三 開頭「一個 job」與步 1–6 | §三 把 CI job 設計成本單元自有的一個 job（步 1 自行建 schema、步 2 自行寫前置狀態），但上游 `nfr-requirements/security-requirements.md:102` 的 `U4-V1` 逐字要求「`U4` 的遷移驗證**共用 `NFR6` 已要求的那個真實 PostgreSQL CI job**，**不另開第二個 job**」，而 `brain-infra` 的 `NFR6.1` 落點 3 逐字說「**該 job 是 `U5 memory-data` 的交付**，其 service container 須與本單元的三處一致。`U5` 的迭代須就地確認此事」。`共用`／`N-2`／`U5` 在本站兩份產出中出現次數為 **0**（grep 實測）。照 §三 施工會產生第二個 job，直接違反 `U4-V1`；且步 1「建 schema」與同居者 `U5` 的 schema 建立在同一個 job 內如何共存，無人交代 | §三 明寫本 job 即 `NFR6` 的真實 PostgreSQL CI job、其擁有者是 `U5 memory-data`，本單元的六個步驟是**加進該 job 的步驟**；並寫明步 1 與 `U5` schema 建立的關係（誰建、順序如何），以及這件事需要 `U5` 的迭代就地確認 | New |
| R-04 | Major | .../hierarchy-data/nfr-design/security-design.md > §四 表（只有 `S-10`／`S-11`）；traceability.json > reverse（只有 `S-10`／`S-11`／`encryption-boundary`） | 上游 `nfr-requirements/security-requirements.md:168` 的 `S-6` 逐字指定落點為「`nfr-design`（3.3）或 `ci-pipeline`（3.7），兩者皆 `CONDITIONAL`。若兩者都被 skip，本項沒有承接站」。本站就是 `nfr-design`，而 §三 實際上把 `S-6` 的內容（CI job 範圍擴及遷移、前置狀態寫入、不變量查詢、重跑斷言）全部設計完了——但 `S-6` 這個 id 在本站兩份產出中出現 **0** 次，既沒有被標為在此結案，也沒有被帶到 `ci-pipeline`。從產出無法判斷它是已結案還是仍掛在一個可能被 skip 的站上 | 在 §四 或 §三 就地以 `S-6` 具名記載「本站承接並結案（落點二選一的第一個）」，並在 `traceability.json` 加一筆對應項；若認為仍有殘留部分需 `ci-pipeline` 承接，逐項寫明殘留的是哪一部分 | New |
| R-05 | Major | .../hierarchy-data/nfr-design/security-design.md > §二「為什麼不選『填擁有者並標記非確證』」；nfr-design-questions.md > Q3 選項 B | 拒絕選項 B 的理由陳述為假。該理由是「多一個欄位會讓本單元『新增欄位總數：1』這個數字失效，而那個數字是 `AC9.1.3` 論證的一部分」。但 `functional-design/entities.md:268-270` 逐字把那個 1 界定為 `ArchitectureDiagram.system_id`（既有表新增欄位），論證逐字是「既有頁面讀寫的每一個欄位都沒有被碰」；選項 B 的旗標欄會落在**新表** `DiagramChangeRecord` 上（其欄位數 7 由 `entities.md:277` 的另一張表追蹤），碰不到任何既有頁面的欄位，因此**那個 1 不會變成 2、論證也不需要重寫**。同一個不成立的前提在 Q3 選項 B 的文字裡逐字呈現給使用者（「本單元新增欄位總數會從 1 變成 2」），所以人工裁決是在一項假事實下做的 | 依 `project.md ## Corrections`「下游查證推翻的是選項的理由而非決定本身時，只修理由不改決定」：`Q3=A` 的決定不動，就地更正 §二 與 Q3 選項 B 的理由（改為「該旗標在一張無讀取端的新表上再加一個無讀取端的欄位，且會把『無可信行動者即無紀錄』這個二元保證換成需要讀取端判讀的軟保證」），並在問題檔記明更正來源 | New |
| R-06 | Minor | .../hierarchy-data/nfr-design/security-design.md > §一 IAM 列的「殘餘」欄（填「無」） | 該列同時宣告「`projects`／`systems` 的執行期存取一律經 `K-07` 的 facade（`U7`）」且殘餘為「無」。上游 `inception/units-generation/unit-of-work.md:222` 逐字記「授權**只掛在 dependency 層**，service 層無第二道角色檢查——同進程直呼 service 函式會完整繞過 RBAC」，並點名 `U10`／`U12` → `U7` 兩條 `sync` 邊落在此風險上、已記為 Accepted risk。本單元確實不提供第二條路，但「一律經 facade」這句超出本單元的範圍且已知在同進程呼叫下不成立，而殘餘寫「無」 | 把該句收窄為「本單元不提供任何存取路徑」，並在殘餘欄註明「facade 之外的同進程繞過風險由 `unit-of-work.md` 記為 Accepted risk、指派 `functional-design`，不由本單元消除」 | New |
| R-07 | Minor | .../hierarchy-data/nfr-design/traceability.json > coverage `U4-R1` status `N/A` | 以「保存 90 天是 `nfr-requirements` 已定的規則，本站沒有可加的設計」結案，但兩件可設計的事沒被交代：(1) 90 天由哪一欄起算——`entities.md:220-222` 的 `created_at` 是唯一候選，本站未指名；(2) 清除查詢的成本面。`nfr-requirements:93` 為這條規則給的理由逐字是「一張沒有讀取端、沒有保存期、沒有人清的表，唯一會被發現的時機是它把磁碟填滿」，而本單元為 `kind: spec`，`performance-design`／`scalability-design` 被 `produces_kinds` 濾掉，所以這個面向在本單元**沒有任何落點** | 在 `U4-R1` 的 target 指名 `created_at` 為判定基準欄，並記明「清除查詢的成本／索引面在本單元無落點（`spec` 濾掉 performance／scalability 設計），一併併入 `S-5` 的承載決定」 | New |
| R-08 | Minor | .../hierarchy-data/nfr-design/security-design.md > §三 末段「`U4-V4` 在 CI 上不設案例」 | 不設 CI 夾具的推理本身站得住：`rules.md:110-111` 的 `BR2.2` `logic` 逐字「IF 該使用者已有預設專案／系統 THEN 取用既有的，不建立第二組」，配合 `nfr-requirements:78` 的可達性更正，確認該拒絕只在實作已寫錯時可達。但 `U4-V4` 的需求文字（`nfr-requirements:78`）真正要防的是**吞掉失敗**（逐字點名 `except Exception: logger.warning` 這個 `database.py` 既有形狀，要求「那個拒絕以非零結束碼收場」），而這一面是可機械檢查的、與夾具無關。本站把整條交給 code review，沒有留下任何機械證據——與同檔 `SEC-3` 留了 import／decorator grep 的做法不一致 | 在 §三 補一條與 `SEC-3` 同形狀的機械檢查（遷移模組的插入路徑上不得出現吞掉例外的 `except`；grep 結果須為零），並把 `U4-V4` 的 target 改為「夾具 Deferred ＋ 吞例外檢查由 grep 承載」 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 無（stage 檔 `.claude/aidlc-common/stages/construction/nfr-design.md` 未列 validation tools） | — | 以手動機械核對替代，逐項見下 |
| `produces_kinds` 對 `kind: spec` 的過濾 | PASS | stage 檔 `:24-28` 確認 performance／scalability／reliability／observability／logical-components 皆不含 `spec`；只產出 `security-design` ＋ `traceability` 正確，未報缺件 |
| `traceability.json` 計數（python，唯讀） | PASS | `upstream_ids` 15、`coverage` 15、兩者 id 序列逐一相同；`reverse` 3 筆 = `reverse_count` 3；status 分佈 OK 10／N/A 3／Deferred 2，與 dispatch 所述一致 |
| repo 事實核對（`deploy/docker-compose.deploy.yml`、`schema_rbac.sql`、`backend/database.py`） | PASS | `:40` `image: pgvector/pgvector:pg18`；`:85` `DATABASE_URL: postgresql://...@db:5432/...` **無 `sslmode`**；`deploy/`＋`backend/` 全樹 `sslmode`／`sslrootcert` 0 命中；`db` 服務無 `ports:`／`expose:`，全 compose 唯一 `ports:` 在 `:319`（frontend）；`pgcrypto`／`ENCRYPT` 於 `schema_rbac.sql`＋`backend/database.py` 0 命中。§一 Encryption 的四條理由**逐條成立** |
| 引用逐字核對 | PASS（2 項例外見 R-01／R-03） | `requirements.md:597`（`OQ-3` 落點 `nfr-design`）✓；`entities.md:196`（`actor_user_id` `required: true`）✓；`deploy/docker-compose.deploy.yml:85` ✓；`brain-infra` `NFR6.1` 的「映像必須一致的四個落點」✓（落點 1–4 為 image、落點 5 為 volume，「四個」數字正確，映像值 `pgvector/pgvector:pg18` 亦正確——**D 項的更正不算過度更正**）；不成立的是「本 CI job」的歸屬（R-03）與 `OQ-3` 的結案範圍（R-01） |
| 語言與雙語段落 | PASS | 兩份產出 `## English Version`／`## 中文版` 0 命中；全文繁體中文 |
| 程式片段 ≤15 行 | PASS | fenced 區塊合計 3 行（§二 的流程樹） |
| `ADR-0006` 四面向完整性 | PASS | 五列覆蓋四面向（IAM 兩列），無空白判定，不適用項附理由 |

### Summary

**三類分佈**：**已決之事的缺陷 2 項**（R-02 `SEC-4` 條件性被宣告解除、R-05 拒絕選項 B 的理由為假且該假前提曾呈現給使用者）；**未察覺的缺口 4 項**（R-03 CI job 的共用歸屬、R-04 `S-6` 未具名處置、R-07 `U4-R1` 的起算欄與成本面無落點、R-08 `U4-V4` 缺可機械化的吞例外檢查）；**上游問題被浮出但處置有誤 2 項**（R-01 `OQ-3` 的部分結案被寫成完整結案、R-06 `unit-of-query` 已記的 RBAC 繞過風險在 §一 被寫成殘餘「無」）。

**核心關切**：加密判定本身是本站最扎實的部分——四條理由逐條在 repo 上成立、界線子句誠實、殘餘（主機磁碟被取得即明文）沒有被美化，這一格不需要動。問題全部落在**結案宣稱的精確度**：`OQ-3`、`SEC-4`、`S-6` 三項在產出上都比實際情況更完整一格，而三者的共同後果是同一個——下游會把「已處理」讀成事實，而承接站是 `CONDITIONAL`。

**若第二輪未能完全收斂，人工應在閘門上衡量**：R-01（`OQ-3` 的 `U5` 那一半是否真的有承接站，或現在就要決定由誰承接）與 R-03（CI job 究竟是誰的交付，這件事需要 `U5` 的迭代配合，不是本單元單方面能定的）。R-05 的決定不需要改，只需要改理由，但它是一項曾呈現給使用者的假事實，宜在閘門上明白揭露。

### Not reached / reached only lightly

- **未讀**：`U5`／`U12`／`U16`／`U7` 的任何 `construction/<unit>/` 內容（讀取範圍限制）。R-03 對「共用 job 由 `U5` 交付」的判定僅依 `brain-infra` 的兩份豁免檔與本單元 `nfr-requirements` 的逐字，未向 `U5` 自身產出複驗；R-02 的 `S-11` 落點適當性僅以 `inception/units-generation/unit-of-work.md:48/162` 確認 `U12` 為已規劃單元，未查 `U12` 的設計是否真能在單一交易內完成兩個寫入。
- **僅輕度**：G 項的「遷移以 schema owner 身分執行、是否該限制該特權」——已確認 §一 第二列把它記為「沿用既有憑證、權限等級即該憑證等級」且未主張任何收窄，`backend/database.py` 的 `_ensure_*` 以同一憑證做 DDL 的既有事實也成立；我**未**進一步推導是否存在低成本的收窄手段（例如遷移期改用受限角色），故未就此立項，只在此記為未追到底。
- **未查**：`.github/workflows/deploy.yml` 的實際步驟（`S-9` 的靜止窗口是否真如 `nfr-requirements:169` 所述在 `:121-124` 一次拉起）——本站對 `U4-V6` 只轉引 `S-9`，未新增設計，故未複驗該行號。

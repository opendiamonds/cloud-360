# Business Logic Model — U-8 反向同步 workflow

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-8-reverse-workflow · kind: service -->

## 這個單元在做什麼

把**人在看板上做的改動**拉回 repo，開成一個 PR 送人決定——而不是讓機制在下一輪默默改回去。

交付 `aidlc-sync-reverse.yml` ＋ 其 `*-impl.yml`。複雜度 **M**，驗證方式 **⑥workflow 執行期**。

**它與 U-6／U-7 的方向相反**：那兩者是 record → 看板，本單元是**看板 → record**。這個方向差異帶來一個結構性後果——**它是唯一會產生 PR 的單元**，因此也是唯一需要考慮「人要審這個東西」的單元。

## 一輪執行的序列

```
排程觸發（每日）
   │
   └─► 對每個已綁定的 intent：
          ├─ U-3 read_item ──► 取回 issue body
          ├─ U-2 parse ＋ content_hash ──► 現況雜湊
          └─ 與 sync-state.json 記錄的雜湊比對
                 ├─ 相同 ──► 無人為變更，跳過（R-1.2）
                 └─ 不同 ──► 有人為變更
                        ├─ 寫 pending_reverse 到該 intent 的 sync-state.json
                        ├─ 開分支 aidlc-sync/reverse/<intent_id>-<date>
                        └─ 開 PR（base=ut，label=aidlc-sync-reverse）
                              └─► 每個 intent 一則 PR（E-2）
```

文字 fallback：逐一取回每個 intent 的 issue body、算出受管區塊的現況雜湊、與上次記錄的比對；相同就跳過，不同就把人改成的值寫進該 intent 的同步狀態檔，開一個只含那一個 intent 的 PR。

## 兩項本站裁定在此落地

**E-1（缺口 N-1）**：[req:FR-G2] 的「同步專用檔案」定為 `sync-state.json` 的 `pending_reverse` 欄位。**PR 的 diff 因此結構上只含該檔**，「不含 `aidlc-state.md` 任何一行」不靠紀律成立。

**E-2**：一個 intent 一個 PR。這讓 over-suppression 的逐 intent 判定**從推導變成結構**——完整的取捨表見 `business-rules.md` R-4。

## 為什麼「PR 關閉也恢復覆寫」不是 bug

[req:FR-G3] 逐字：「直到對應 PR 被**合併或關閉**」。

在**拒絕**路徑上（PR 被關閉未合併），該 intent 恢復被覆寫，P2 的改動最終仍被輾回去。**`stories.md` 的 S-6 已明文承認這條邊界**，並據此把 benefit clause 從「我的判斷會被保留」改成「**送到人面前決定**」。

**本站不改寫這個邊界，也不把它記成缺陷**——它是已核可的行為，且該故事的價值主張已誠實對齊它。

## 錯誤處理

| 情形 | 行為 | 紅燈 | **通報** |
| --- | --- | --- | --- |
| 讀看板失敗 | 該 intent 跳過，計入報告，**續跑其餘** | 是（`ExternalError`） | **是**（C-5 `notify`） |
| 開 PR 失敗 | 同上 | 是 | **是**（C-5 `notify`） |
| `pending_reverse` 寫入後開 PR 失敗 | **狀態檔已改但沒有 PR** — 見下方 | 是 | **是**（C-5 `notify`，附 intent id 與分支名） |
| 雜湊未變 | 跳過，**非錯誤** | 否 | 否 |

> **「通報」欄是 2026-08-30T00:57:28Z 補上的（reviewer iteration 3 Group A M-4）**：本表先前只有「紅燈」欄，於是 [req:FR-E1]／[US:S-8 AC 1] 的「外部失敗 → issue」在反向路徑上沒有落點。元件鏈補 C-5 由 **ADR-0015 §5** 承載，本單元的呼叫落點即本表；方法簽章見 `business-rules.md` 的 R-4c。**紅燈與通報是兩件事**——紅燈讓 workflow 失敗、通報讓人在 issue 上看到，[req:FR-E1] 要的是後者。

**第三列是本單元唯一的失敗視窗，但它比先前寫的窄得多。** 先前此處寫「後果是 U-6 讀不到對應的 PR，該 intent 不會被暫停覆寫」——**那是錯的**，已於 reviewer iteration 2 更正：

依 `business-rules.md` 的 R-6.0，`pending_reverse` 的寫入騎在反向分支上，PR 開不成時它**從未進入 `ut`**。所以「狀態檔說有待處理、實際卻沒有 PR」這個跨輪的不一致狀態**構造上不存在**；U-6 看到沒有反向 PR 而照常覆寫，是正確行為（本來就沒有東西要保護）。

真正的後果只有一個，且範圍是 run 內：**這一次的人為改動沒有被送到任何人面前**，下一輪會重新偵測到同樣的雜湊差異並再試一次。

**處置**：PR 建立失敗時**刪除該分支**；刪除也失敗則保留孤兒分支。**兩種情形都在同一次執行內記入報告並紅燈**，附 intent id 與分支名（R-6.3）。

**這是清理與可見性要求，不是正確性要求**——`ut` 的一致性由 R-6.0 結構性保證，不靠這條規則。

## 邊界情形

| 情形 | 行為 | 依據 |
| --- | --- | --- |
| 多個 intent 同時被人改動 | **多個 PR**，各含一個 intent | E-2 |
| 同一 intent 已有開啟中的反向 PR，又被改一次 | **不開第二個**——以 label 即時查詢開啟中的反向 PR 判定，**不看儲存欄位** | R-6.1 |
| 前一則反向 PR 已合併，人又改一次 | 即時查詢無開啟中 PR → 照常開新 PR，`pending_reverse` 被覆寫 | R-6.1、R-1.3 |
| `pending_reverse` 在 `ut` 上非 `null` | 代表**曾有一則反向 PR 合併過**。無任何單元讀它做控制流，**不清除** | R-6.0、R-6.2 |
| PR 被關閉（未合併） | 該 intent 恢復覆寫，改動最終被輾回 | [req:FR-G3] 逐字；S-6 的誠實邊界 |
| 機制自己剛寫過該區塊 | 雜湊相同，跳過 | R-1.2 |
| 高成本 workflow 對反向 PR 執行 | **不是本單元的責任**——歸 U-10b | R-5 |

## 與上游的對應

S-C 的生命週期與寫入邊界引自 [ad:services.md]；[req:FR-G1]～[FR-G3] 與 C-N1／C-N3 引自 `requirements.md`；[US:S-6] 全部 AC 與 benefit clause 的誠實邊界引自 `stories.md`；over-suppression 的風險與「未實測」標記引自 [ug:unit-of-work.md] 的 U-8 與 [ad:decisions.md] 的 CAP-11；`content_hash`／`parse` 引自 U-2、`read_item` 引自 U-3、`sync-state.json` 引自 U-4、`reverse_pending` 的讀取引自 U-6；D-1 的標記契約引自 U-6 的 `domain-entities.md`；同批次約束引自 `unit-of-work-dependency.md`；元件分層引自 [ad:components.md]。

**本檔對上游的補充**：「同步專用檔案」的指名（E-1，缺口 N-1）、一 intent 一 PR（E-2）、以及 `pending_reverse` 的生命週期（R-6 群：它在 `ut` 上非 `null` 等價於曾有反向 PR 合併，無讀者故不清除；原子性失敗是 run 內條件）。**FR-G1～G3 的行為、S-6 的 benefit 邊界、CAP-11 的未實測狀態一字未改。**

## Review

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T15:09:48Z
**Iteration**: 1

### Findings

| # | 嚴重度 | 檔案:行 | 問題 | 建議 |
|---|---|---|---|---|
| 1 | Critical | `stories.md:199`（[US:S-6 AC 5]）vs 本單元全部三份產出 | **[US:S-6 AC 5] 在本單元的設計中完全未被承接。** `unit-of-work-story-map.md:36` 與本檔自己的 `business-rules.md` R-4b 表（「AC 1–5……U-8（本單元）」）都明白宣稱本單元擁有 AC 1–5。AC 5 逐字要求：「Given 該反向 PR 被關閉而未合併，When 下一次正向同步覆寫該 item 之前，Then 該 item 的 issue 受管區塊載有一則記錄，指出該次人工改動未被採納與其時間戳。」這是一個獨立、可觀察的交付物（受管區塊裡的一則明確記錄），與 AC 4（合併→恢復覆寫）不同。逐字搜尋本檔與 `business-rules.md`：兩處都只處理「PR 關閉後恢復覆寫」這個行為本身（`業務邏輯模型.md` 的「為什麼『PR 關閉也恢復覆寫』不是 bug」一節、`business-rules.md` R-3.3），**沒有任何一句提到要在恢復覆寫之前，把「此次人工改動未被採納」連同時間戳寫進受管區塊**。這不是措辭疏漏——本檔明確主張「該故事的價值主張已誠實對齊它」（送到人面前決定），但沒有 AC 5 的落地，人根本不會被告知他的改動被拒絕；「誠實對齊」的可觀察部分恰好就是 AC 5 承載的，而它沒有設計。 | 在 `business-rules.md` 的 R-3 群新增一條規則：反向同步偵測到「上次已知有開啟中反向 PR」但**該 PR 現況為已關閉且未合併**時，於本輪（或下一次執行）呼叫 U-2 的 `render`（C-6）在受管區塊追加一則「此次人工改動未被採納，觀察於 <timestamp>」的記錄，且此動作須發生在下一次正向同步的覆寫之前——需與 U-6 的排程/並行語意對齊（是否需要 U-8 比 forward sync 更早跑，或由 U-8 自己在偵測到關閉時立即寫入）。並在 `domain-entities.md` 補上這則記錄用到的欄位／受管區塊片段。 |
| 2 | Critical | `business-logic-model.md:15-28`、`business-rules.md` R-1.1、`domain-entities.md` 全篇 | **R-1.1「與 `sync-state.json` 記錄的雜湊比對」所需的『上次記錄的雜湚』欄位，在本單元（也是唯一新增 `sync-state.json` schema 的責任方，見 E-1）的 `domain-entities.md` 中完全沒有宣告。** `decisions.md` ADR-A6 已確認這類雜湚確實需要持久化（「任何格式變更必須伴隨一次明確的重新基準化（把所有受管 item 的雜湊重算並**寫回 `sync-state.json`**）」），代表 `sync-state.json` 理應含有一個逐 item 的雜湚欄位。但本單元的 `domain-entities.md` 明文宣稱「反向紀錄寫進 `<record>/sync-state.json` 的新欄位 `pending_reverse`」是**唯一**新增欄位（E-1），且結尾自陳「本單元不新增其他型別」——完全沒有提及這個雜湚欄位的名稱、schema、是否為既有欄位（若是，由哪個 Bolt／哪個單元建立）、或任何跨 Bolt 警示（`pending_reverse` 有明確的「⚠ 跨 Bolt 警示」段落，這個雜湚欄位沒有任何對應處理）。套用 `project.md` 要求的狀態欄位三問：**誰寫**這個欄位——未指定（U-6 每次 render 後寫回？U-2 自己維護？完全沒說）；**誰讀**——本單元的 R-1.1（隱含）；**誰清／更新**——未指定。三問中兩問是空白，而 R-1.1／R-1.2 正是本單元「要不要開 PR」這個核心判定的**唯一**輸入來源之一，沒有這個欄位的 schema，開發者無法實作本單元最核心的機制。 | 在 `domain-entities.md` 新增一節，明確宣告 `sync-state.json` 中承載「上次雜湚」的欄位名稱與型別，並指派誰在什麼時機寫入（最合理的候選是正向同步／U-6 在每次成功 render＋寫入看板後，把 `content_hash(rendered_block)` 回寫進 `sync-state.json`）。若該欄位已在 U-4 的 Bolt 1 schema 中存在，需比照 `pending_reverse` 的處理方式明寫「確認人為 Bolt N 的 gate」與跨 Bolt 相容性，而不能隱含假設它存在。 |
| 3 | Major | `business-rules.md:102-114`（R-4c 表） | R-4c 的表格標題宣稱「本單元呼叫的**四個**上游方法」，但表格實際列出 **5** 列（`read_item`、`parse`、`content_hash`、`write_sync_state`、`commit_and_push`）——可算的數字與文字不符。更嚴重的是**元件歸屬錯誤**：表格把 `parse(issue_body) -> Block \| null` 與 `content_hash(Block) -> sha256` 都標為元件 **C-2**，但依 `component-methods.md`（C-6 `managed-block` 的公開介面：`render`／`parse`／`content_hash`）與 `components.md`（C-6 的擁有者是 **U-2**，C-2 `record-reader` 屬 **U-1**，其 `parse` 簽章是 `parse(state_md_text, intents_json_text, record_path) -> ParsedRecord \| Unparseable`——與 `parse(issue_body) -> Block \| null` 完全是兩個不同的方法），這兩列的正確元件應為 **C-6**，不是 C-2。本檔別處（`business-logic-model.md` 的流程圖）正確地把這兩個方法標為「U-2」，與本表的「C-2」（實際屬 U-1）互相矛盾——同一份設計對同一組方法的歸屬給出兩個不同答案。 | 把 R-4c 表的 `parse`／`content_hash` 兩列的「元件」欄改為 **C-6**；同步核對標題數字（若確實只想強調四類方法，需說明 `parse`＋`content_hash` 算同一類，或把標題改為「五個」）。 |

### Validation Tool Results

本 stage 未在 frontmatter 列出可執行的機械驗證工具（`sensors: required-sections / upstream-coverage / linter / type-check` 由引擎的 sensor pipeline 另行觸發，非本次審查可直接呼叫）；本輪審查以逐檔人工核對為主，並針對 R-1.1 的雜湊比對與 R-4c 的方法簽章逐一開啟 `inception/application-design/{components,component-methods,services}.md` 與 `inception/units-generation/{unit-of-work,unit-of-work-story-map}.md` 核實。

### Summary

兩項 Critical 都是「本單元自己宣稱擁有、卻沒有設計」的落空：AC 5（反向 PR 遭拒後的受管區塊通知）完全沒有對應規則，使 S-6 benefit clause 的「誠實對齊」主張站不住；R-1.1 賴以判斷「要不要開 PR」的雜湊持久化欄位在本單元自己的資料模型（`domain-entities.md`）裡完全缺席，且無任何跨 Bolt／owner 標示，是本單元最核心機制的一個結構性空白。另有一項 Major 是 R-4c 表格的元件歸屬錯誤與標題數字對不上表格列數，屬可機械核對的文件缺陷。三項均非本輪之前三輪已結案的 E-1／E-2／R-6 群／承載形式／分支命名範圍。

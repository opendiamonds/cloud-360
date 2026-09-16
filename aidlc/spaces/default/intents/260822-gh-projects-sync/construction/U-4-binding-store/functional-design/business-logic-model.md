# Business Logic Model — U-4 record 回寫與同步狀態

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-4-binding-store · kind: library -->

## 這個單元在做什麼

維護 record 側的**持久狀態**：綁定編號、`<record>/sync-state.json`，以及把兩者推回觸發分支的 `commit_and_push`。

它與前三個單元的差別：U-1／U-2 零 I/O，U-3 做網路 I/O，**本單元做檔案系統與 git I/O**。驗證方式因此是「④git 與 repo 行為」（[ug:unit-of-work.md]），不是 fixture，也不是 API。

## 資料流

```
record_path ─► read_binding ──► int | null ──► null 觸發首建（U-3）
            └─► read_sync_state ─► SyncState（缺席欄位補預設，未知欄位保留）
                                        │
              本輪判定結果 ──────────────┤
                                        ▼
                              write_sync_state（原樣寫回未知欄位）
                              write_binding
                                        │
                                        ▼
         commit_and_push(觸發分支, [兩個檔], "…[aidlc-sync]…")
                    ├─ Pushed（含內部重試後成功）
                    └─ Rejected（分支保護，或重試 3 次後仍非快轉）─► C-5 通報 ＋ 紅燈
```

文字 fallback：讀綁定編號與同步狀態（讀取時容忍缺席欄位、保留未知欄位），套用本輪結果後寫回這兩份檔案，再以一次 commit 推回**觸發分支**；推送成功回 `Pushed`，重試無用才回 `Rejected` 並紅燈。

## `commit_and_push` 的三步與內部重試（[Q1=A]）

```
git push
   ├─ 成功 ─────────────────────────────────► Pushed
   ├─ stderr 含分支保護拒絕 ─────────────────► Rejected（立即，不重試）
   └─ stderr 含非快轉 ─┬─ 重試次數 < 3 ──► 重取兩檔最新內容 ► 重套變更 ► 再 push
                       └─ 重試次數 = 3 ──► Rejected
```

文字 fallback：推送失敗時先分辨成因——分支保護是永久性的，立刻放棄並紅燈；非快轉是暫時性的，重取檔案重套變更再推，最多三次。

**這個分辨必須解析 stderr**，只看 exit code 做不到——兩種失敗都是非零。規則、N=3 的理由與其可修改性見 `business-rules.md` R-3.5。

> 本設計把 [ad:component-methods.md] 原本合為一個 `Rejected` 的兩種成因在**內部**分開，但**對外的回傳型別一字未改**。這是缺口 H-1 的處置形狀：修行為、不修已核可的契約。

## 跨版本相容的三條規則（[Q2=A]）

C-1 只增不改、C-2 讀時補預設、C-3 寫時保留未知欄位。完整規則見 `business-rules.md` R-2 群，schema 見 `domain-entities.md`。

**C-3 是最重要也最容易被實作掉的一條**：它保護的是 Bolt 上線期間排隊中的舊 run 讀到新版檔案的情形，而多數 JSON 處理寫法預設就會丟棄未知鍵。必要的 fixture 已在 `business-rules.md` R-2.3 明列。

## 錯誤處理

| 產出 | 紅燈？ | 說明 |
| --- | --- | --- |
| `ExternalError`（`write_binding` 檔案寫入失敗） | **是** | [ad:services.md] 明列的兩種紅燈之一 |
| `Rejected`（重試無用的推送失敗） | **是** | 另一種 |
| `Pushed` | 否 | 含內部重試後成功 |

本單元是**兩種紅燈都會產生**的唯一單元（U-3 只產生 `ExternalError`）。這與它的位置一致：它是機制唯一寫回 repo 的地方，寫不進去就是真的需要人看。

`phases/construction.md` 的「在整合邊界一律有錯誤處理」在此的落點是上表三個回傳值；「錯誤必須被表面化」的落點是 `Rejected` 的紅燈與通報。**沒有靜默失敗的路徑**——內部重試不是靜默，它的結果仍完整反映在回傳值上。

## 邊界情形

| 情形 | 行為 | 依據 |
| --- | --- | --- |
| `sync-state.json` 的 `binding` 欄位缺席 | `read_binding` 回 `null` → 觸發首建（併入後由 R-2.2 的補預設值涵蓋） | R-1.1／R-2.2（缺口 L-1） |
| **回寫失敗導致綁定編號始終寫不進去** | 每 push 一次多一張卡。**唯一防線是紅燈 ＋ 通報** | R-1.1 的說明（`requirements.md` A-8 未驗證） |
| `sync-state.json` 缺席 | 補全部預設值，不視為錯誤 | R-2.2 |
| `sync-state.json` 含未知欄位 | 原樣保留寫回 | R-2.3 |
| `schema_version` 高於自己 | **不拒絕**，照 R-2.3 處理 | R-2.4（與 U-2 的 `parse` 刻意不同，理由見該處） |
| 並行推送導致非快轉 | 內部重試至多 3 次 | R-3.5 |
| 推 `ut`／`main` | 分支保護拒絕 → `Rejected` | R-3.1／R-3.4（此即完成判準第一條） |
| 回寫 commit 取消了既有 `ci.yml` run | **不是本單元的責任**——歸 U-10a | R-4 |

## 與上游的對應

方法契約、錯誤處理與 `paths` 白名單引自 [ad:component-methods.md] §C-4；跨輪相容要求與紅燈語意引自 [ad:services.md]；元件分層引自 [ad:components.md]；FR-A3／FR-A4 與假設 A-8 引自 `requirements.md`；[US:S-1 AC 6]／[AC 7] 引自 `stories.md`；單元邊界、驗證方式、完成判準與「不擁有 AC 7」引自 [ug:unit-of-work.md] 的 U-4；AC 歸屬引自 [ug:unit-of-work-story-map.md]。

**本檔對上游的補充**：`sync-state.json` 的 schema 與三條相容規則（缺口 H-2，[Q2=A]）、`commit_and_push` 的內部重試與成因分辨（缺口 H-1，[Q1=A]）。**方法簽章、回傳型別、`paths` 白名單、`[aidlc-sync]` 標記一條未改。**

## Review

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T15:12:15Z
**Iteration**: 1

### Findings

| # | 嚴重度 | 檔案:行 | 問題 | 建議 |
| --- | --- | --- | --- | --- |
| 1 | Major | `business-rules.md:38`（R-3.1） | 「正向同步（**U-6／U-7**）只推觸發分支」把 U-7（對帳 workflow）錯誤歸類為 `commit_and_push` 的呼叫者。實測反證四項：(a) 逐字讀過 U-7 的 `business-logic-model.md`／`business-rules.md`／`domain-entities.md` 三檔，資料流圖與各自「與上游的對應」段落**全數不提** U-4／C-4／`commit_and_push`／`write_sync_state`；(b) [ad:components.md] 的 workflow 呼叫表對 `aidlc-sync-reconcile.yml` 寫的是「C-7 →（內部）C-2／C-1／C-3／C-5」，同樣不含 C-4；(c) U-7 唯一的寫入動作是「補平（`write_status`）」，直寫 Project 看板，不經 git／不經本單元；(d) 連本檔宣稱依循的修正來源——U-8 `business-rules.md` R-4c（「已直接修正 U-4 的 R-3.1」）——原文也只講「正向路徑」，從未點名 U-6／U-7，「／U-7」是本檔自己疊上去、U-8 原文沒有的內容。且 U-7 與 U-8 同為 `schedule`／`workflow_dispatch` 觸發（[ad:services.md] S-B／S-C），本來就沒有「觸發分支」可言——即使 U-7 未來真的需要回寫，也不會落在「只推觸發分支」這一類。 | 刪除「／U-7」，改為「正向同步（U-6）只推觸發分支」；並在此處或發現 #2 的落點註明 U-7 完全不呼叫 C-4 這項事實，避免下一個讀者比照 U-6 去猜測 U-7 的呼叫方式。 |
| 2 | Major | `domain-entities.md:15,19`（`last_status`／`last_synced_at` 兩列） | schema 表宣稱 `last_status` 為「上一次**成功寫入看板**的 Status」、`last_synced_at` 為「上一次成功寫入的時刻」——但這兩個欄位只有 U-6 經 `commit_and_push` 落地時才會更新（見本檔 `資料流`：`write_sync_state → write_binding → commit_and_push`）。U-7 的補平（`write_status`）是另一條**真實會寫看板 Status** 的路徑（[ad:component-dependency.md] 依賴矩陣「C-7」列對「C-4 binding」為 `—`、對「C-3 board」為 `●`；U-7 `business-logic-model.md`「不一致 ► 補平（write_status）├─ Written」），且已由發現 #1 證實 U-7 從不呼叫 C-4／`write_sync_state`。結果是：每次對帳補平之後，`last_status`／`last_synced_at` 立即與看板實況不符；而 workflow run 跑在無狀態的 runner 上，即使 U-7 未來想更新這兩個欄位，只在工作目錄寫檔還不夠——不經 `commit_and_push` 這次更新根本不會跨 run 存活。本檔是 `sync-state.json` schema 的唯一定義處，卻對這條落差**完全沒有著墨**——對照之下，同一份 schema 對 `pending_reverse` 與 U-6 的 `Config.reverse_pending`「兩者是不同的東西」特地寫了一句釐清，`last_status` 這裡沒有對應揭露。這正是本輪要重點核對、與已修的 `pending_reverse` 同型的「誰寫、誰讀、誰清」缺口。 | 在 schema 表 `last_status`／`last_synced_at`（`last_field_value` 因寫入路徑相同一併算入，不另立一項）兩列，或「與上游的對應」段落，補一句明確語意邊界：「本欄位只反映經 U-4／`commit_and_push` 完成的回寫；U-7 補平走 C-3 直寫看板，不落地本檔，跨 run 不持久」。若判斷這個落差需要收斂（例如讓 U-7 也呼叫 `write_sync_state` ＋ `commit_and_push`），把「指派 U-7 或後續整合站」的待辦寫下來，而不是留空。 |
| 3 | Minor | `domain-entities.md:38-54`（「跨版本相容規則」C-1／C-2／C-3） | 本檔為 schema 演進三規則另開一組代號 C-1／C-2／C-3，與 [ad:components.md] 定義、貫穿本 intent 全部 12 個單元文件通用的元件代號 C-1(`sync-map`)／C-2(`record-reader`)／C-3(`board-client`) 直接撞號。單獨讀本檔 line 50「C-3 是最重要也最容易被實作掉的一條」，會先聯想成 board-client 元件，須靠上下文才能分辨這裡指的是另一組規則。 | 改用不與元件代號衝突的代號（如 V-1／V-2／V-3），並在首次出現處加一句消歧義說明。 |
| 4 | Minor | `business-rules.md:57`（R-3.5，`N = 3`） | 重試上限具體值 `N = 3` 是本站在 artifact 產生階段自行引入的數字。[Q1=A] 的選項文字只揭露「重試上限 N 是一個新的魔術數字」這個**代價**，並未把 3 這個具體值交給人工選擇或確認——嚴格說屬「本站裁定、未經人工提問」的一項。 | 不需要為此回頭開新問題（成本與效益不對稱，且理由與可調整但書已寫清楚）；僅記錄於此供追溯，維持現狀即可。 |

### 已核對、未發現問題的項目（逐項覆核 task 指定的檢查點）

- **C-1／C-2／C-3（跨版本相容規則本身）**：只增不改、缺席補預設、未知欄位原樣寫回，三條彼此一致，且與 [ad:services.md] 的服務契約（「跨輪相容性必須維持」）方向一致，未見恆真或自相矛盾。
- **C-3 規則的 fixture 指派**：`business-rules.md` R-2.3 與本檔都明確描述了這個 fixture 的內容與斷言目標。U-4 為 `kind: library`，此 fixture 屬本單元自己的交付範圍，且 `tcms-test-cases`（`project.md ## Mandated`，blocking）強制要求「待自動化」桶必須真的寫出腳本並跑綠——未發現指派落空的風險。
- **R-3.1 對 [ad:component-methods.md] 原文與 U-8 用法的核對**：原文「只推觸發分支」逐字確認（`component-methods.md:106`）；U-8 的 R-4c（`business-rules.md:110-114`）確認其對 `commit_and_push` 的用法是推 `aidlc-sync/reverse/<intent_id>-<date>` 分支，且 U-6 的 `domain-entities.md` D-1 對同一個分支前綴給出逐字一致的定義——U-8 這一半的對齊正確，問題只出在本檔額外把 U-7 也塞進「正向同步」那一類（發現 #1）。
- **其餘欄位（`schema_version`／`binding`／`last_reason_code`／`managed_block_hash`）**：`schema_version`／`binding` 為單調或一次性欄位，無清除需求，未見異常。`managed_block_hash` 由 C-6 產生、U-4 只儲存，寫入路徑跟隨 U-6 的 `render` 步驟；U-7 三份文件未見呼叫 C-6 或改寫 issue body 的證據（其補平只呼叫 `write_status`），故未發現 `managed_block_hash` 有與發現 #2 同型的落差。`last_reason_code` 與 `last_field_value` 的寫入路徑與 `last_status` 綁在同一次 `write_sync_state`，受影響程度與 `last_status` 相同，已併入發現 #2 的建議範圍。
- **審查範圍**：本次讀取僅涵蓋 dispatch record（`.aidlc-reviewer-dispatch.json`）exempt 清單內的檔案——U-4 自身六個檔案、`inception/` 全部核可產出、U-6／U-7／U-8 的 functional-design 三檔——未讀取或涉及其餘 sibling 單元的 construction 內容。

### Summary

兩項 Major 同源：`sync-state.json` 有兩個真實寫入者（U-6 經 `commit_and_push`、U-7 經 `write_status` 直寫看板），但本檔只完整交代了 U-6 與 U-8（`pending_reverse`）之間的欄位語意邊界，沒有把 U-7 這條路徑一併納入——R-3.1 因此誤將 U-7 歸類為 `commit_and_push` 的呼叫者，schema 表對 `last_status`／`last_synced_at` 的語意宣稱也未排除 U-7 這個不經過本檔的寫入路徑。兩者都是本輪任務明確指定要核對的「誰寫、誰讀、誰清」缺口，修正成本不高，但在標示完成前必須處理。

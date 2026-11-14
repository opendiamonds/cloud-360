## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-09T12:41:38Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `construction/session-store/functional-design/functional-spec.md` §一 `W1` 第 5 步（同形於 `W7` 第 4 步）；對照 `rules.md` 的 `BR1.x` 群組與 `entities.md`／`contract-summary.md:684-742`（`K-09.public_interface`） | `W1` 第 5 步寫「`U13` 回「無」時建立新 session：只含 `shared` 段，`pageModes` 兩鍵皆 `shared`，作業對象三層皆未選定」，`W7` 第 4 步同形。但 `K-09` 的五個方法（`load`／`set_work_target`／`append_message`／`set_sharing_mode`／`touch`）裡**沒有一個**被文件化為「建立一個全新、符合 `EC1`／`EC2` 預設值的 `BrainSession`」的持久化動作——`BR1.6` 只規定 `load` 在 key 不存在時回「無」，不規定任何寫入端的 upsert 行為；`BR2.4`／`BR3.1` 等規則的 trigger 都預設 session（或至少其 `pageModes`／`segments`）已經存在。送審前自檢 §八的「契約端點三問」表只確認五個既有方法「皆有具名呼叫者」，沒有問「哪個方法實際把 `W1` 第 5 步的全新預設值寫進 Redis」。開發者實作 `U10` 時無法從本站四份產出判斷：(a) 是否應新增一個 `create`／`ensure_exists` 方法（`OQ-N4` 已授權改 `public_interface`，故這不超出授權），或 (b) 五個既有方法中哪一個被期待在 key 不存在時隱式建立預設值再套用該次寫入。 | 在 `rules.md`／`entities.md`／`functional-spec.md` 明訂：哪一個 `K-09` 方法（新增或既有）負責把 `EC1`（`shared` 段存在）、`EC2`（`pageModes` 兩鍵預設 `shared`）、三層作業對象未選定的全新 `BrainSession` 寫入 Redis，並說明它與 `BR1.3`（TTL 續期）、`BR2.1`（段識別封閉集合）等規則的互動（例如：新建時是否也要立即套用 `shared` 段的建立邏輯，是否算作 `BR2.4` 的建立路徑之一）。 | New |
| R-02 | Minor | `rules.md` 的 `BR4.7`（含其逐字例外說明）；對照 `functional-spec.md` §七 IAM 格、`EC7`／`EC8` | `BR4.7` 的例外（`BR4.2` 初始化複製路徑不需重跑 `K-07` 驗證，理由是「複製來源是已驗證過的共享段值」）只論證了「複製動作本身不放大既有風險」，但沒有處理一個更根本的問題：`K-07` 的驗證只發生在**寫入當下**（`BR4.6`），而共享段的值可能在寫入之後因存取被撤銷或該 Project／System／Diagram 被刪除（`K-04` 的 `DG-2`——Project／System 刪除的 cascade——目前仍是未定案的 Open Question）而變成「已驗證但已過期」。這個過期風險不是 `BR4.7` 例外新引入的（共享段自己讀取時也一樣過期），但本單元的四份產出沒有任何一處明文承認「驗證的時效僅到下一次寫入，讀取不重驗」這個設計選擇，也沒有指出下游消費端（`U11`／`U12`）在真正**動用**這些識別碼執行動作時是否需要再驗一次——留給讀者自行推論。 | 在 `BR4.6`／`BR4.7` 或 §七 IAM 格補一句，明寫「驗證為寫入時點驗證，本單元不做讀取時重驗；識別碼的時效性風險（撤權、實體刪除）由消費端在真正動用時自行決定是否重驗」，把目前隱含的設計假設變成顯式記載，而不需要改變任何行為。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 人工逐字核對（未跑機械 sensor，因 CLI 版本未知；改以逐行開檔核對） | `hierarchy_service.py:261-273`、`hierarchy_facade.py:277-281`、`components.md:151/153-155`、`brain_ws_contract.py`（`SharingModePayload`／`WorkTargetPayload`／`SetSharingModePayload`／`SetWorkTargetPayload`／`HelloPayload` 現況）、`unit-of-work-dependency.md:51-53`（`work-orchestrator.depends_on` 含 `session-store`）、`unit-of-work.md:479`、`decisions.md`（`ADR-016`）、`contract-summary.md`（`x-session-key-derivation`、`OQ-N4`、`OQ-N3`）全部逐字核對通過，事實與定位皆準確 | 作者自述的三個「最不確定」之處（`[S1]`/`[S3]` 與 `x-session-key-derivation` 的矛盾、`K-02` 最小改動集不動 `hello` 的可行性、`OPEN-S10-1` 的「無需新 DAG 邊」）**全部查證為真**：矛盾是真實的且處置合理（已有 `OPEN-S10-2` 如實記載推翻範圍，未回改上游）；`hello` 不動的設計站得住（連線建立時是向新連線廣播全部段/全部頁的狀態，用識別欄位讓客戶端自行過濾，不需要伺服器知道連線屬於哪一頁）；`work-orchestrator.depends_on: [session-store, ...]` 確實已存在於 `unit-of-work-dependency.md:53`，「不需要新增 DAG 邊」的論證成立 |

### Summary

本單元的設計在三個作者自評「最沒信心」的地方都查證站得住：`[S1]`／`[S3]` 推翻 `x-session-key-derivation` 的「同一組」主張是真實存在的矛盾（而非誤讀），且處置方式（`OPEN-S10-2` 如實記載推翻範圍、不回改上游）符合既有紀律；`K-02` 最小改動集「不動 `hello`」在實際契約檔（`brain_ws_contract.py`）核對下可行；`OPEN-S10-1` 聲稱「不需新 DAG 邊」在 `unit-of-work-dependency.md` 逐字核對後成立。本輪找到的新缺口是 R-01：工作流程明確需要「建立一個全新 `BrainSession`」這個動作，但四份產出裡沒有任何 `K-09` 方法被指名承擔它——這是一個會讓實作者卡住猜測的具體缺口，而非品味建議。R-02 是對 `BR4.7` 例外論證邊界的提醒，屬可接受風險等級。零 Critical、一 Major、一 Minor，在 READY 門檻之內。

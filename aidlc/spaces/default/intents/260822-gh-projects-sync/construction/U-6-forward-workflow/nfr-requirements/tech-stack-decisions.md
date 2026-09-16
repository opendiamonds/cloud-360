# Tech Stack Decisions — U-6 正向同步 workflow

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-6-forward-workflow · kind: service -->

## 決定

**`.github/workflows/aidlc-sync-forward.yml`（觸發與 concurrency）＋ `aidlc-sync-forward-impl.yml`（`on: workflow_call`，全參數化）**，純 Actions，`shell: bash`。編排前四個 composite action（`aidlc-sync-map`、`aidlc-sync-block`、`aidlc-sync-board`、`aidlc-sync-record`）與 `aidlc-sync-notify`。

兩檔拆分為 [ad:decisions.md] **ADR-A10** 的要求（`on: workflow_call` 全參數化）。**非本站決定**，此處只記其後果：觸發設定與實作分離，使 [F1=A] 的「Project 編號、組織名、record 根目錄、自訂欄位名一律為 input，不得寫死」在 impl 層自然成立。

## 五支 composite action 的組裝點

| action | 誰的產出 | 本單元如何呼叫 |
| --- | --- | --- |
| `aidlc-sync-map` | U-1 | 每個 intent 一次；輸入含本單元算出的 `reverse_pending` |
| `aidlc-sync-block` | U-2 | `operation: render`／`parse`／`hash` 三種分派 |
| `aidlc-sync-board` | U-3 | 讀寫看板；需 `GH_TOKEN` |
| `aidlc-sync-record` | U-4 | 回寫；需 `GH_TOKEN` |
| `aidlc-sync-notify` | U-5 | 失敗時；需 `GH_TOKEN` |

**本單元是唯一同時引用五支的地方**，也是 `GH_TOKEN` 從 workflow secret 進入各 action 的**唯一入口**。

## 承接 bash 的四項既有代價，本單元不新增第五項

U-1 記「沒有原生 `null`」、U-2 記「正規化序列化難做」、U-3 記「GraphQL 錯誤在 HTTP 200 的 body 裡」、U-4 記「`jq` 兩種寫法只在跨版本時顯現差異」、U-5 記「`gh issue list` 須用 `--json` 不得解析表格輸出」。

**本單元的內容是 YAML 與流程控制，不是資料處理**，因此不引入新的 bash 陷阱。唯一要注意的是 composite action 的 output 在 workflow 層以 `steps.<id>.outputs.<name>` 取用——[Q1=A] 於 U-1 選的「四個具名 output」讓這一步是直接的字串取值，不需 `fromJSON`。

## 與上游的對應

ADR-A10 的兩檔拆分與 [F1=A] 的參數化要求引自 [ad:decisions.md]；五支 action 的承載形式分別引自 U-1～U-5 的 `tech-stack-decisions.md`；concurrency 與觸發設定見本單元的 `business-rules.md` R-1 群，一輪序列見 `business-logic-model.md`，跨單元契約見 `domain-entities.md`；`GH_TOKEN` 的 env 形狀為既有先例（見 U-3 的 `security-requirements.md` SEC-1 與 [kb:technology-stack.md]）；單元交付引自 [ug:unit-of-work.md] 的 U-6。

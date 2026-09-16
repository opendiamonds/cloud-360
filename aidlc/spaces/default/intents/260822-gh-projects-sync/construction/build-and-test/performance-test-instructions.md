# Performance Test Instructions — AI-DLC ↔ GitHub Projects 同步機制

<!-- Stage: build-and-test（Construction）· 上游 NFR：U-6／U-7／U-8／U-9 的 performance-requirements.md -->

## 這個系統的效能問題不是「快不快」

本 intent 沒有使用者請求路徑、沒有 RPS、沒有 p95 延遲曲線。四條效能需求全部是
**排程與預算**性質：

| NFR | 內容 | 承載單元 | 可量測性 |
| --- | --- | --- | --- |
| NFR-P1 | 自 record 被推送起算 5 分鐘內看板更新 | U-6 | **只能在真實 CI 上量**，量測落點在 U-7 的 `latency_samples` |
| NFR-P2 | 對帳每日一次，避開三個既有排程 | U-7 | **建置期可判**（讀 cron 值即可） |
| NFR-P3 | concurrency group 分組且 `cancel-in-progress: false`（上游寫三組，實作為**兩組**，見 P-T1） | U-6／U-7／U-8 | **建置期可判**（讀 workflow YAML） |
| NFR-P4／FR-D3 | 對帳單次處理量上限 | U-7 | **上限值未定**——待 PRE-1 第 2 項實測 C-T5 |

因此本檔分成兩半：**現在就能跑的建置期檢查**，與**只有真實 CI 才做得到的量測**。
把後者寫成「待辦」而不寫清楚它為什麼現在做不到，會讓下一個人以為是誰忘了跑。

## 現在就能跑的（建置期，二元可判）

### P-T1：concurrency group 的實際落點是**兩組**，不是三組（本輪實測推翻上游裁定）

```bash
python3 - <<'EOF'
import yaml
for f in ("aidlc-sync-forward.yml","aidlc-sync-reconcile.yml","aidlc-sync-reverse.yml"):
    c = yaml.safe_load(open(".github/workflows/"+f))["concurrency"]
    print(f, c["group"], c["cancel-in-progress"])
EOF
```

**本輪實測值**：

| workflow | `group` | `cancel-in-progress` |
| --- | --- | --- |
| `aidlc-sync-forward.yml` | `aidlc-sync-event-${{ github.repository }}-${{ …head.ref \|\| ref_name }}` | `false` |
| `aidlc-sync-reconcile.yml` | `aidlc-sync-reconcile-${{ github.repository }}` | `false` |
| `aidlc-sync-reverse.yml` | **`aidlc-sync-reconcile-${{ github.repository }}`（與對帳同一組）** | `false` |

判準因此是：**兩個相異 group（事件組、對帳組），三支全部 `cancel-in-progress: false`，
且反向與對帳同值**。

**這與 U-8 `performance-requirements.md` 缺口 P-2 的裁定相反，而相反是刻意的。**
`aidlc-sync-reverse.yml:39-71` 逐字寫下三個理由：

1. `functional-design/open-items.md` 的 **N:C-2 把 P-2 的「自成第三組」判為 Critical**
   ——它推翻了已過 gate 的 `application-design/services.md:58`（S-C 的 concurrency 欄
   逐字「與 S-B **同一組**」），處置逐字為「需 ADR 或回退」，而本 intent 至今**沒有**
   為它開出 ADR（ADR-0015／0016 對此零命中）。
2. 兩邊論證強度不對稱：`services.md` 的是**正確性**論證（兩者都碰 record，不應並行），
   P-2 的是**便利性**論證。
3. 已核可計畫的「查證 1」只盤點了 `open-items.md` 的四項，**N:C-2 不在其中**——據以
   推翻上游不是知情核可。

改回第三組是**一行的改動**（換成 `aidlc-sync-reverse-${{ github.repository }}`），
且 `run-reverse-tests.py::test_structure_triggers_concurrency_and_workflow_call` 有靜態
斷言鎖住現值，改的時候會紅燈，不會靜默漂移。**待 Bolt 3 gate 為 P-2 開 ADR 或確認回退。**

> 這一條原本寫成「三個 `group` 值互不相同」，是照著 U-8 的 NFR 裁定寫的、**沒有先讀
> 實作**。本輪跑了才發現實作刻意反著做且理由更強。留下這段記錄是因為它正是
> `application-design:c8`（出選項前先實測既有結構）要防的形狀。

### P-T2：cron 不撞既有排程

```bash
grep -rn "cron:" .github/workflows/ | sort
```

判準：本 intent 新增的 cron 值不等於既有三個——`daily-digest` `0 23 * * 1-5`、
`agentics-maintenance` `37 0 * * *`、`release-watch` `39 16 * * 1`。

### P-T3：`timeout-minutes` 落在**會實際執行的那個 job** 上

```bash
grep -n "timeout-minutes" .github/workflows/aidlc-sync-*.yml
```

**本輪實測**：`aidlc-sync-forward-impl.yml:73` 為 20、`aidlc-sync-reconcile-impl.yml:115`
與 `aidlc-sync-reverse-impl.yml:123` 為 30、`aidlc-sync-selftest.yml:129` 與 `:250` 各為 10。
三支**薄外層零命中**。

**零命中是正確的，不是缺口**：`timeout-minutes` 只存在於 job 與 step 層，**GitHub
Actions 沒有 workflow 層的 `timeout-minutes`**，而薄外層的 job 是 `uses:` 呼叫可重用
workflow——上界落在被呼叫那支的 job 上。判準因此是「**每一支會實際跑步驟的 job 都有
明確值**」，不是「每支 workflow 檔都有一行」。

**沒有上界時 GitHub 的預設是 360 分鐘，而這個 repo 已經被那個預設咬過一次**——PR #510
上一個 stalled browser download 跑到 5h59m24s 才被 6 小時上限砍掉、無可下載 log、重跑又
stall 一次，單一 PR 約七小時 runner、零測試執行。

**兩個已登錄的落差**：

- U-9 的 `performance-requirements.md` 字面寫「workflow 層 `timeout-minutes` 10」，但因
  該層不存在，實作是**每個 job 各 10** ⇒ 兩段串接的最壞情況是 **20 分鐘 wall clock**。
  已在 `aidlc-sync-selftest.yml:122-128` 就地註明並列入 Bolt 4 gate。
- gh-aw v0.81.6 在編譯 pre-agent-steps 時**靜默丟棄 `timeout-minutes`**（`env`／`id`／
  `if`／`uses`／`with`／`working-directory`／`continue-on-error` 都保留，只有它不保留）
  且回報 0 errors / 0 warnings。本 intent 的七支 workflow **是純 Actions、不經 gh-aw
  編譯，不受影響**；U-10b 改動的四支 gh-aw workflow 仍在那個風險面上，驗它們要看
  編譯後的 `.lock.yml` 而不是 `.md`。

### P-T4：離線測試套件自身的耗時

離線層是每個 PR 都會跑的東西，它自己的耗時就是成本。實測值見
`build-test-results.md` 的耗時欄。判準：**單支不超過 120 秒**（本輪最慢一支為
`run-reverse-tests.py`）。

> U-9 `code-summary.md` 已實測並記載：自我測試第一段的成本主體是**六支上游驅動**，
> 不是 fixture 數——這推翻了 `scalability-requirements.md:25` 的推論前提（成本隨
> fixture 數成長）。優化時看的是驅動數，不是 fixture 數。

## 只有真實 CI 做得到的（本階段無法執行）

### P-T5：NFR-P1 的 5 分鐘延遲

**量測機制是 U-7 的 `latency_samples`，而 U-6 與 U-7 之間沒有 DAG 邊。**
若 U-7 沒做出 `latency_samples`，NFR-P1 就沒有任何量測機制——它會變成一條無法證偽的
宣稱。這是本 intent 效能面最需要在 gate 上被看到的一句話。

延遲預算的五段拆解（U-6 `performance-requirements.md`）：

| # | 段落 | 可控性 |
| --- | --- | --- |
| 1 | 事件到 run 啟動 | **不可控**（GitHub 排隊，尖峰可達數十秒） |
| 2 | checkout ＋ 環境準備 | 低（無 `npm ci`、無 Docker build） |
| 3 | `reverse_pending` 查詢 | 可控（**一次**查詢，與 intent 數無關） |
| 4 | 逐 intent 處理 | **可控且是主要變數** |
| 5 | 回寫 ＋ push | 中（非快轉時最多重試 3 次） |

**第 4 段是唯一隨規模成長的**，而 [Q1=A] 於 U-3 定案以 `Issue.projectItems` 反查而非
列舉整個 Project，使單次同步成本與 Project 的 item 總數無關——這是 NFR-P1 在設計層的
主要保障。

**一個必須寫下的但書**：`cancel-in-progress: false` 意謂同分支事件**排隊**，而上游的
驗收準則寫的是「自觸發 push 完成」起算 ⇒ **排隊時間計入**。高頻 push 時該準則可能
不成立，這是「不取消換不遺漏」這個取捨的直接後果，不是實作缺陷。

### P-T6：NFR-P4 的批次上限值

**上限的實際值待 PRE-1 第 2 項實測 C-T5（框架單次操作次數上限）後才能定。本階段不臆測
數字。** 現況的上界可以算：每個 intent 最多 4 次呼叫（`read_item`／`read_issue_state`／
`write_status`／`write_field`）＋ 每輪兩次固定呼叫 ⇒ 6 個 record 時為 **6 × 4 ＋ 2 = 26 次**。
距離任何合理上限都很遠，但**這是現況判斷**，不是上限本身。

### P-T7：U-9 workflow 的 10 分鐘上界

**10 分鐘是估計值不是量測值**，須在 Bolt 4 首次真實執行後複核（U-9 交還清單第 4 項）。

## 觀察：U-7 與 U-8 每日各掃一次全部已綁定 intent

兩者都對每個已綁定 intent 呼叫 `read_item`，合計每日 **2N** 次讀取，而**讀回來的
`ItemState` 是同一份**（比較的東西不同：對帳比 record→看板，反向比看板雜湊→儲存雜湊）。

**這是觀察不是缺陷**：合併需要跨 Bolt 的設計變更（U-7 在 Bolt 2、U-8 在 Bolt 3），而
N 在可預見範圍內是數十量級。記下它是為了讓「N 變大時第一個該看哪裡」有紀錄。

## 與上游的對應

NFR-P1〜P4 與五段延遲拆解引自 U-6／U-7 的 `performance-requirements.md`；缺口 P-2
（自成第三組）與 2N 觀察引自 U-8 的同名檔；`timeout-minutes` 上界、
gh-aw v0.81.6 靜默丟棄的行為與 PR #510 的七小時事件引自 U-9 的同名檔與
`.github/workflows/ui-regression.md` 的註解；六支上游驅動才是成本主體一事引自 U-9 的
`code-summary.md`；concurrency group 的落點分工引自 U-6／U-7／U-8 的
`code-generation-plan.md` Step 10／11，實際落地值為本站以 `yaml.safe_load` 讀出；
實作反著做的三個理由引自 `.github/workflows/aidlc-sync-reverse.yml:39-71`（本站實讀）；C-T5 未定引自 `bolt-plan.md` 的 PRE-1 表。

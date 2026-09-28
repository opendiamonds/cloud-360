# Tech Stack Decisions — U-10a `ci.yml` 的回寫排除

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-10a-ci-writeback-exclusion · kind: packaging -->

## 決定

**對 `.github/workflows/ci.yml` 的 `on:` 區塊新增 `paths-ignore`，涵蓋 `<record>/sync-state.json` 的 glob（[Q1=A] 後為唯一需排除的路徑）。**

不新增任何工具、依賴或檔案。本單元是對既有檔案的修改，複雜度 **XS**。

## 實測的既有觸發設定（本站查證，非引用）

```yaml
on:
  pull_request:            # ← 無任何 branches 或 paths 過濾
  push:
    branches: [main, ut, "danniel/**", "chore/**"]
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

**兩個必須被寫下來的後果**：

### 1. `paths-ignore` 在 `pull_request` 上**無效**，機制已更換（2026-08-30T06:11:59Z，人工裁決）

**先前的設計是對 `ci.yml` 的兩個觸發器加 `paths-ignore`，並宣稱「一個機制解 AC 7 的兩半」。該宣稱經 reviewer 判為 Critical 並實測推翻。**

**為什麼無效**：`pull_request` 事件的 `paths`／`paths-ignore` 比對的是**整個 PR diff**（base↔head），不是本次 push 的變更。同步回寫進到一個已有 PR 的分支時，該 PR 的 diff 必然同時含開發者的 record 變更 ⇒ 過濾條件永不成立 ⇒ 新 run 照建。**而本節先前自己就寫過「真正會發動的是 `pull_request`」——選的機制恰好在自己指認的失敗路徑上無效。**

**實測的 `ci.yml` 現況**（本站實讀，非引用）：

```yaml
on:
  pull_request:                      # 無分支、無路徑過濾
  push:
    branches: [main, ut, "danniel/**", "chore/**"]
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

`group` 用 `github.ref`，所以同步的 run 與開發者的 run **落在同一組** ⇒ 取消。

### 2. 新機制：concurrency 分組 ＋ job 層 `if:`（兩半分別解）

[US:S-1 AC 7] 要求兩件事，**新機制以兩個手段分別滿足**（先前是一個手段宣稱解兩半，而它一半也沒解）：

| AC 7 的一半 | 手段 | 為什麼成立 |
| --- | --- | --- |
| **既有 run 不被取消** | `concurrency.group` 追加 `${{ github.actor }}` | 同步以 bot 身分推送，`github.actor` 與開發者不同 ⇒ 落在不同 group ⇒ `cancel-in-progress` 取消不到開發者的 run |
| **不新增一輪四個 job** | 四個 job 各加 `if:`，跳過 commit message 含 `[aidlc-sync]` 的 head commit | `[aidlc-sync]` 已是既有契約（[ad:component-methods.md] §C-4 要求 commit 訊息必含它，且 [req:FR-A4] 的自我排除已依賴它）⇒ 不新增第二套識別機制 |

**誠實記載的代價**：run **仍會被建立**（顯示為全部 Skipped），所以「不新增一輪四個 job」是以「**無 job 執行**」滿足，而非字面的「run 不存在」。先前的 `paths-ignore` 本來能達成字面版本——但它在真正的失敗路徑上不生效，所以那個較強的保證從來不存在。**這不是降級，是把一個假的保證換成一個真的。**

**`if:` 的取值來源**：`push` 事件用 `github.event.head_commit.message`；`pull_request` 事件該欄位不可得，改用 `github.event.pull_request.title` 不成立（PR 標題不是 commit 訊息）。**這一點是本機制的殘留缺口**——`pull_request` 側的 `if:` 需要另一個可得的判準（候選：`github.actor` 等於 bot 身分，與 concurrency 用的是同一個訊號）。**指派 code-generation 在實作 `ci.yml` 時定案並實測**，因為它依賴 bot 身分的實際值，而該值要到 PRE-1 鑄出憑證後才確定。


**這一點直接決定 `paths-ignore` 的充分性**：若重試會產生多個 commit，每個都要被排除；由於它們推的是同一份變更、涉及同一個路徑，一條 glob 即足。

## 路徑集合（[Q1=A] 的直接後果）

| 路徑 | 為什麼要排除 |
| --- | --- |
| `aidlc/spaces/*/intents/*/sync-state.json` | U-4 每輪回寫的唯一檔案（綁定編號依 [Q1=A] 併入此檔） |

**[Q1=A] 讓這張表只有一列。** 若當初選了獨立檔（Q1=B），這裡會是兩列，且第二列的檔名需要一份與 C-N1 同等的規定。

**約束**：glob 必須**盡可能窄**。不得寫成 `aidlc/**` 或 `**/*.json`——理由見 `security-requirements.md` SEC-1。

## 與上游的對應

`paths-ignore` 的設計落點與「本元件不能單方面解決」引自 [ad:component-methods.md] §C-4 的註；[US:S-1 AC 7] 引自 `stories.md`；NFR-C1（既有 CI 四道關卡不得被破壞）引自 `requirements.md`；C-N1 的路徑規定引自同檔；單元邊界、完成判準與「歸 U-10a 不歸 U-4」引自 [ug:unit-of-work.md] 的 U-10a 與 U-4 的「不擁有」欄；同批次約束（U-4 ＋ U-10a 為真捆綁）引自 `unit-of-work-dependency.md`；U-4 的回寫行為見其 `business-rules.md` R-3 群與 `domain-entities.md`；`ci.yml` 的觸發設定與 concurrency 為本站實測（並見 [kb:technology-stack.md] 對 CI 四道 job 的盤點）。

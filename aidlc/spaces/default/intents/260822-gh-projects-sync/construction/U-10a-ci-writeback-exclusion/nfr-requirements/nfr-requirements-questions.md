# NFR Requirements — U-10a `ci.yml` 的回寫排除

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-10a-ci-writeback-exclusion · kind: packaging -->

## 為什麼本單元在這一站有產出、在 functional-design 卻沒有

functional-design 的四項 `produces_kinds`（`business-logic-model`／`business-rules`／`domain-entities`／`frontend-components`）**都不含 `packaging`**，故本單元在該站被自動視為已涵蓋。nfr-requirements 的 `security-requirements` 與 `tech-stack-decisions` **沒有 kind 限制**，因此本站有兩份產出。

## CONDITIONAL 適用性判定

| 條款 | 判定 | 依據 |
| --- | --- | --- |
| Performance | ❌ | `produces_kinds` 限 `[service, ui]` |
| Security | ✅ | `paths-ignore` 會**改變 CI 閘門的觸發覆蓋範圍**，見 `security-requirements.md` SEC-1 |
| Scalability | ❌ | 限 `[service]` |
| Tech stack selection | ✅ | 需決定 `paths-ignore` 的**精確路徑集合**，而其中一個路徑上游未定義（缺口 L-1） |
| Skip if 兩者皆無 | ❌ | 上述兩項皆有 |

**判定：EXECUTE**。

## 問題

### Q1. 綁定編號寫在哪裡？（缺口 L-1）

`requirements.md` 的 **C-N1** 明確指定 `sync-state.json` 的路徑為 `<record>/sync-state.json` 且不得以 `.aidlc-` 開頭。但**綁定編號的落點從未被定義**：

- [US:S-1 AC 2] 只說「該 intent 的 record 內存在一個**可機器讀取的欄位**」。
- [ad:component-methods.md] 的 `write_binding(record_path, issue_number)` 只給 record 路徑。
- `commit_and_push` 的 `paths` 說「限 record 目錄下的**綁定編號**與 `sync-state.json`」——是路徑，但沒說是哪個。

**這卡住本單元**：`paths-ignore` 必須逐字寫出被排除的路徑。

A. **併入 `sync-state.json` 的一個欄位**：`paths-ignore` 只需鎖一個已有明確路徑的檔（C-N1 已定），不新增任何需要被排除的路徑；回寫也從兩次檔案寫入降為一次。代價：[ad:component-methods.md] 把 `read_binding`／`write_binding` 與 `read_sync_state`／`write_sync_state` 列為四個獨立方法，併檔後四者操作同一份檔——需在 U-4 明寫這不是複製而是同一份資料的兩組存取器。

B. **獨立檔 `<record>/sync-binding`**：與四個方法分列的形狀一致；編號是一次性寫入（首建時）而 sync-state 每輪可能更新，生命週期不同。代價：`paths-ignore` 多鎖一個路徑；且新增一個需要 C-N1 同等規定的檔（不得以 `.aidlc-` 開頭）。

C. **寫進 `aidlc-state.md` 的一個欄位**：不新增任何檔。代價：讓同步機制寫入它自己讀取狀態的那份檔；且 `paths-ignore` 就必須涵蓋 `aidlc-state.md`，等於**所有 AIDLC 工作的變更都不觸發 CI**——遠超出本單元範圍的副作用。列出僅為完整性。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T12:32:22Z（讀自 date -u）· 併入 sync-state.json 的一個欄位 -->

**落點**：本裁定同時影響 **U-4**（其 `domain-entities.md` 目前把綁定編號記為「不在這個檔裡」）。依 `project.md`（`units-generation:260822-ug-L2`）標出並指派：**U-4 的 `domain-entities.md` 與 `business-rules.md` R-1.3 須同步修訂**；確認人為 **Bolt 1 的 gate**（U-4 與 U-10a 同屬 Bolt 1，且兩者是真捆綁）。

## Q（code-generation 前補問）：`paths-ignore` 失效後改用哪一種機制

**背景**：reviewer 判 Critical——`pull_request` 事件的 `paths-ignore` 比對整個 PR diff 而非本次 push，同步回寫進到有 PR 的分支時過濾永不成立，[US:S-1 AC 7] 兩半皆不可滿足。實測 `ci.yml` 確認 `concurrency.group` 用 `github.ref`，同步的 run 與開發者的 run 落在同一組。

**選項**：

A. **`concurrency` 加 `github.actor` ＋ 四個 job 加 `if:`**：前者讓同步的 run 落在不同 group（不取消開發者的 run），後者跳過 `[aidlc-sync]` commit（無 job 執行）。兩半分別解，只改 `ci.yml`。代價：run 仍會被建立（顯示 Skipped），「不新增四個 job」以「無 job 執行」滿足而非字面的「run 不存在」。

B. **只改 `concurrency` group**：不加 `if:`。開發者的 run 不被取消，但同步回寫仍跑完整四個 job。改動最小，但 AC 7 只滿足一半，需回頭改該 AC。

C. **改變回寫落點**：同步不推有 PR 的分支，改推自建分支並開 PR（比照 U-8）。`ci.yml` 一字不改，問題從根源消失。代價：推翻 U-4／U-6 已核可的回寫設計（`commit_and_push` 只推觸發分支），且每次同步多一則 PR。

[Answer]: A  <!-- 2026-08-30T06:11:59Z（讀自 date -u）· 人工裁決 -->

**殘留缺口（已寫進 `tech-stack-decisions.md`）**：`pull_request` 事件取不到 `head_commit.message`，該側的 `if:` 判準需改用 bot 身分，實際值待 PRE-1 鑄出憑證後定，**指派 code-generation 實作 `ci.yml` 時定案並實測**。

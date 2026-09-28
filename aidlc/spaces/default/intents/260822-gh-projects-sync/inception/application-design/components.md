# Components — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: application-design（Inception 2.5）· Record: 260822-gh-projects-sync
     來源標籤：[req:*] 指 requirements.md；[US:S-n AC m] 指 stories.md；[kb:*] 指 codekb；
     [Qn]／[Fn] 指本站問題檔。設計決定的完整理由見 decisions.md。 -->

## 上游輸入

- **requirements.md**（Revision 1，已核可）：40 FR、15 NFR、6 約束、8 假設；本檔逐一承接。
- **stories.md**（Revision 1，已核可）：11 則故事、65 條 AC、全域 DoD、PRE-1、US-OQ-1～7。
- **codekb `architecture.md`**：「開發流程層架構」三節——`aidlc-state.md` 章節契約與 `getField()` 解析語意、gh-aw 編譯後的 job 拓撲與 concurrency 行為、`ci.yml`／`deploy.yml` 的共存面。
- **codekb `component-inventory.md`**：11 支 gh-aw workflow 的觸發、排程、safe-outputs 盤點；`.github/actions/` **不存在**，本 repo 無 composite action 先例。
- **codekb `dependencies.md`**：既有依賴基線。
- **team-practices**：scope 跳過 `practices-discovery`，由 `memory/team.md` 與 `project.md` 直接提供。

## 承載形式的總體決定

依 [Q1=A 經 F1 收斂]：**三條路徑全部是手寫 GitHub Actions workflow，不使用 gh-aw**。

決定性理由有二，兩者都可機械複驗（完整論證見 `decisions.md` ADR-A1）：

1. **`NFR-P3` 在 gh-aw 下無法照字面滿足。** [kb:architecture.md] 實測記載 gh-aw 的 concurrency group 由編譯器依觸發型別產生、作者寫不了，且 PR 觸發型固定 `cancel-in-progress: true`；而 `NFR-P3` 要求事件觸發兩路徑共用一組且 `cancel-in-progress: false`。
2. **`FR-B2` 要求判定不由 LLM。** gh-aw 編譯出的 workflow 必含 agent step，決定性邏輯只能放 `pre-agent-steps`，而該區塊有「靜默丟棄 `timeout-minutes` 且回報 0 warnings」的已知缺陷（v0.81.6 實測，PR #510 因此燒掉約 6 小時 runner 時間）。

依 [F1=A]，承載物**全部參數化**：Project 編號、組織名、record 根目錄、自訂欄位名、白名單一律為 input，**不得寫死**。可重用性是設計的性質，不是本次的交付能力——本次不交付散佈物（版本策略、安裝文件、範本 workflow、跨 repo 憑證指引）。

## 元件清單

依「若兩個元件總是一起改，它們就是同一個元件」切分。七個元件，分三層。

### C-1 `sync-map`（純函式層）

| 項目 | 內容 |
| --- | --- |
| 目的 | 把一個 record 的解析結果映射為 `(Status, 自訂欄位值, 決定理由)` 三元組 |
| 擁有 | [req:FR-B] 的六列對照表、[req:FR-B3] 的 `[S]`／`— SKIP` 區分、[req:FR-B6]／[req:FR-F4] 的 `Parked` 特判、[req:FR-J5] 的白名單判定 |
| 公開介面 | `map(parsed_record, config) -> Decision`；`Decision` 含 `status \| null`、`field_value`、`reason_code`、`traceable_row` |
| 不擁有 | 任何 I/O。不讀檔、不呼叫 API、不寫 log |
| 承載形式 | **composite action** `.github/actions/aidlc-sync-map/action.yml`（[US-OQ-7]） |
| 為什麼是 composite action | 它必須能被一支測試 workflow 以純文字 fixture 驅動（[US:S-10 AC 1]），而 inline `run:` 區塊沒有任何測試層取用得到；`scripts/` 下的 Python 被 `project.md ## Forbidden` 排除（本機制為無人值守自動化）。本 repo **無 composite action 先例**，此為首例 |
| 關鍵約束 | `map()` 對任一可解析 record **恰好輸出一個 Status 或明確的「不寫」**（[US:S-2 AC 15] 的總函式性）；`Status = null` 是合法輸出，代表「決定不寫」，`reason_code` 說明為何 |

### C-2 `record-reader`（純函式層）

| 項目 | 內容 |
| --- | --- |
| 目的 | 解析 `aidlc-state.md` 與 `intents.json`，產出 `sync-map` 的輸入 |
| 擁有 | [req:FR-J6] 的 `getField()` 語意複製（行錨定、全檔搜尋、第一個 match 即回傳、缺席回 `null` 而非空字串）、[req:FR-J4] 的 stage 清單逐檔解析、[req:FR-J3] 的必要區塊缺失判定 |
| 公開介面 | `parse(state_md_text, intents_json_text, record_path) -> ParsedRecord \| Unparseable` |
| 不擁有 | 檔案系統存取（文字由呼叫端傳入，使 fixture 驅動成為可能）、任何寫入 |
| 承載形式 | 與 C-1 同一個 composite action。**理由是介面緊密耦合＋部署便利，不是「總是一起改」**：`ParsedRecord` 的形狀由 C-2 決定、C-1 直接消費，且兩者都是零 I/O 純函式，共用一個 composite action 讓 fixture 驅動的測試與部署都更精簡。**兩者仍是兩個元件**——改對照表的判定順序不需要動 `getField` 的行錨定規則，反之亦然（reviewer iteration 1 Finding 6：先前版本借用了「總是一起改」這個切分判準的字面，但那會導出「應合併為一個元件」的相反結論） |
| 關鍵約束 | 「欄位缺席」與「欄位存在但值為空」必須走**不同分支**（[US:S-2 AC 9]）——`Parked` 在現況 record 是缺席而非空值，混同會讓 park 特判永不觸發 |

### C-3 `board-client`（外部邊界層）

| 項目 | 內容 |
| --- | --- |
| 目的 | Projects v2 的唯一出入口 |
| 擁有 | GraphQL 查詢與 mutation、欄位 id 解析、分頁、寫入前回讀比對（[req:FR-C1]）、首建專屬檢查（[req:FR-C2]）、重複建立防護（[US:S-1 AC 6]） |
| 公開介面 | `read_item(binding) -> ItemState`、`create_item(intent, config) -> binding`、`write_status(binding, expected, desired) -> WriteResult`、`write_field(binding, value)`、`read_issue_state(binding) -> open\|closed`（[US:S-9 AC 5]） |
| 不擁有 | 決定寫什麼（那是 C-1）、決定要不要通報（那是 C-5） |
| 關鍵約束 | `write_status` **必先回讀**；不符時回 `Aborted(actual, expected)` 而**不送出寫入**，且不自行開 issue（開 issue 是 C-5 的職責）。這使「中止」與「通報」可分別測試 |
| 本 repo 無先例 | [kb] 實測：11 支 workflow 沒有一支寫過 Projects v2，無 `projects` toolset 使用、無相關 safe-output。分頁、欄位 id 查詢、錯誤碼處理全部是新寫的 |

### C-4 `binding-store`（repo 邊界層）

| 項目 | 內容 |
| --- | --- |
| 目的 | record 側的持久狀態：綁定編號與 `sync-state.json` |
| 擁有 | [req:FR-A2] 的綁定編號讀寫、[req:C-N1] 的 `<record>/sync-state.json`、[req:FR-A3] 的回寫 commit（訊息含 `[aidlc-sync]`，僅涉 record 目錄下那兩個檔） |
| 公開介面 | `read_binding(record_path)`、`write_binding(record_path, issue_number)`、`read_sync_state(record_path)`、`write_sync_state(record_path, state)`、`commit_and_push(branch, paths, message)` |
| 關鍵約束 | 回寫**只推觸發分支**，永不推 `ut`／`main`（由 [Q2=A] 的分支保護在機制外強制；[US:S-10 AC 5] 的**兩個例子中只有這一個**可由分支保護產生真的 403，另一個「改 record 目錄以外的檔案」在本設計下無機制可產生 403——見 ADR-A2 與 PRE-1-a）；且 commit 必須帶 `paths-ignore` 等價手段避免觸發 `ci.yml`（[US:S-1 AC 7]） |

### C-5 `notifier`（通報層）

| 項目 | 內容 |
| --- | --- |
| 目的 | 把失敗與異常變成人看得到的東西 |
| 擁有 | [req:FR-E1／E3] 的通報 issue、[req:FR-J2] 的分岔通報、[US-OQ-1] 的重複失敗收斂 |
| 公開介面 | `notify(failure_identity, detail) -> IssueRef`、`resolve_if_open(failure_identity)` |
| 失敗身分 | `(intent id, reason_code)` 二元組。**記憶體是 GitHub issue 本身**（[Q5=A]）——以該鍵搜尋開啟中的通報 issue，命中則追加 comment 並更新標題計數，不命中才開新的。**不新增任何持久狀態**，`sync-state.json` 不承載失敗歷史 |
| 關鍵約束 | 「依 [req:FR-C1] 主動中止」與「對帳成功補平」**都不使 workflow 紅燈**（[US:S-8 AC 1] 的兩項適用前提）；只有外部錯誤（API 失敗、權限不足、逾時）才紅燈 |

### C-6 `managed-block`（呈現層）

| 項目 | 內容 |
| --- | --- |
| 目的 | issue 內 `<!-- aidlc:managed -->` 受管區塊的產生、解析與雜湊 |
| 擁有 | [req:FR-G4] 的內容雜湊比對防線、[US-OQ-3] 的「刻意不寫」敘述、[Q6=A] 的「空值 = 不受管」規則說明、`Done` 卡片下掛開啟中 issue 的說明（OOS-2 的必然後果）、[req:FR-F3] 的 `[S]`／`— SKIP` 差別 |
| 公開介面 | `render(decision, context) -> block_text`、`parse(issue_body) -> block \| null`、`content_hash(block) -> sha256` |
| 與自訂欄位的分工（[Q3=C] 的收斂） | **完整敘述一律在受管區塊；自訂欄位只放一個短前綴**（`frozen:`／`parked @`／`skipped`），限一個字元類。**兩處不一致時以受管區塊為準**——此優先序由本站定案，理由見 `decisions.md` ADR-A4 |

### C-7 `reconciler`（編排層）

| 項目 | 內容 |
| --- | --- |
| 目的 | 每日對帳：掃描、補平、計數、產出三份清單與一致率 |
| 擁有 | [req:FR-D1～D4]、[US:S-9] 的全部 AC（一致率、三份獨立清單、補平計數、延遲量測、issue 與 Status 不相稱偵測） |
| 公開介面 | `reconcile(config) -> ReconcileReport` |
| 關鍵約束 | 處理清單 = 「有綁定編號」且「`Parked` 為空」（[req:FR-D2]）；既有 71 個未綁定 item 的 `updatedAt` 前後不變（[US:S-7 AC 2]）；單次處理量有上限且以 workflow input 宣告（[US:S-7 AC 3]） |

## Workflow 承載（三支 ＋ 一支測試）

| Workflow | 觸發 | 呼叫的元件 | 對應需求 |
| --- | --- | --- | --- |
| `aidlc-sync-forward.yml` | `push`（任一分支）＋ `pull_request`（opened／synchronize／closed） | C-2 → C-1 → C-3 → C-4 → C-6 →（失敗時）C-5 | [req:FR-A]、[FR-B]、[FR-C]、[FR-F]、[FR-J] |
| `aidlc-sync-reconcile.yml` | `schedule`（每日一次，避開三支既有排程）＋ `workflow_dispatch` | C-7 →（內部）C-2／C-1／C-3／C-5 | [req:FR-D]、[req:NFR-O1／O2] |
| `aidlc-sync-reverse.yml` | `schedule` ＋ `workflow_dispatch` | C-3（讀）→ C-6（雜湊比對）→ C-4（寫檔）→ 開 PR | [req:FR-G] |
| `aidlc-sync-selftest.yml` | `pull_request`（僅當同步相關路徑變動） | 以 fixture 驅動 C-1／C-2；對**獨立測試 Project** 驅動 C-3 | [US:S-10] 全部 AC |

> **經 ADR-0015 §13 更正（指標補於 2026-08-30T01:31:09Z）**：`aidlc-sync-reconcile.yml` 的元件集合**應含 C-4**。缺它時 U-7 補平看板後無法回寫 `SyncState`，三欄過期使 U-6 下一輪的 `write_status` 必然回 `Aborted` 並開一則**假通報**——補平愈成功、假通報愈多。**另**：`schedule` 只在預設分支（本 repo 為 `main`）觸發，而 `main` 落後於 `ut`，故 `actions/checkout` 必須釘 `ref: ut`，否則對帳會拿過期 record 且**靜默失真**（人工裁決 Q6=A，使用者原話「不應該在main上跑」；同樣適用於 `aidlc-sync-reverse.yml`）。此處原文維持，見 `../decisions/0015-functional-design-upstream-amendments.md`。確認人為 Bolt 2 的 gate。

> **經 ADR-0015 §5 更正（指標補於 2026-08-30T00:48:38Z）**：上表 `aidlc-sync-reverse.yml` 的元件集合**應含 C-5**。缺它時反向同步的外部失敗只會讓 workflow 紅燈而**不產生通報 issue**，[req:FR-E1]／[US:S-8 AC 1] 的「外部失敗 → issue」保證在該路徑上不成立。此處原文維持，見 `../decisions/0015-functional-design-upstream-amendments.md`。確認人為 Bolt 3 的 gate。

**concurrency 配置**（[req:NFR-P3] 照字面滿足，這是選純 Actions 的直接收益）：

- `aidlc-sync-forward.yml`：`group: aidlc-sync-event-${{ github.repository }}-${{ github.event.pull_request.head.ref || github.ref_name }}`，`cancel-in-progress: false` ——**同一分支上的 PR 與 push 兩條路徑共用同一組**（PR 事件取 head 分支名、push 取分支名），後到者排隊；**不同分支互不排隊**。理由與殘留風險見 `services.md` S-A。
- `aidlc-sync-reconcile.yml`：`group: aidlc-sync-reconcile-${{ github.repository }}`，`cancel-in-progress: false` ——**自成一組**，與事件路徑可並行。
- `aidlc-sync-reverse.yml`：與 reconcile 同組（兩者都是排程、都碰 record，不應並行）。

**`name`（body H1）須與現有 11 支 gh-aw 及 4 支 Actions workflow 皆不同**（[req:NFR-C2]，[kb] 記載 gh-aw 的 `name` 同時決定其 concurrency group）。

## 可重用性的具體形狀（[F1=A]）

`aidlc-sync-forward.yml` 等三支各自拆為兩層：

- **內層**：`.github/workflows/aidlc-sync-*-impl.yml`，`on: workflow_call`，宣告 inputs：`project_number`、`project_owner`、`record_root`、`stage_field_name`、`whitelist`、`reconcile_batch_size`；secrets：`app_id`、`app_private_key`。
- **外層**：`.github/workflows/aidlc-sync-*.yml`，只宣告觸發條件與本 repo 的實際值，`uses: ./.github/workflows/aidlc-sync-*-impl.yml`。

其他 repo 未來要用時，只需複製外層那支三行 workflow 並改 inputs。**本次不交付**版本標記、安裝文件與範本——那是 [F1] 的 B 案，未被選中。

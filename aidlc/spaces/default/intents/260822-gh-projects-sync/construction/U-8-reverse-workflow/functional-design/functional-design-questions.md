# Functional Design — U-8 反向同步 workflow

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-8-reverse-workflow · kind: service -->

## CONDITIONAL 適用性判定

| 條款 | 判定 | 依據 |
| --- | --- | --- |
| New data models | ✅ | 「同步專用檔案」從未被命名（缺口 N-1）；反向紀錄的形狀未定義 |
| Complex business logic | ✅ | over-suppression 的逐 intent 判定、雜湊比對、PR 生命週期 |
| Business rules need design | ✅ | 見下方兩項裁定 |
| Skip if simple logic changes | ❌ | 新 workflow |

**判定：EXECUTE**（`kind: service` → 三份產出）。

## 本站承接的上游指派

**D-1（反向 PR 的識別標記）** 於 U-6 定案為「分支名前綴 `aidlc-sync/reverse/` ＋ label `aidlc-sync-reverse`」，**產生者是本單元**。U-6 用它算 `reverse_pending`、U-10b 用它做**排除**。本單元必須**同時**設定兩者。

> **「U-10b 用它做 `branches-ignore`」已於 2026-08-29T15:21:33Z 由 U-6 兩處更正，本處為 iteration 3 M-2 的傳播補正（2026-08-30T00:05:00Z）。** `branches-ignore` 過濾的是 PR 的 base 而非 head，而反向 PR 的 base 一律 `ut`，故該過濾器**不排除任何 PR**；U-10b 實際採用的是 `paths-ignore`。本單元是該標記的**產生者**，殘留在此的錯誤機制敘述會直接誤導實作。

---

## 本站裁定（**未經人工提問**）

> 以下為本站依既有事實與已核可決定所作的裁定，理由完整記載以便覆核。**不是人工裁決。**

### E-1. 「同步專用檔案」＝ `sync-state.json` 的新欄位（缺口 N-1）

[req:FR-G2] 逐字：「反向同步**只寫入同步專用檔案**，不得改動 AI-DLC 引擎擁有的欄位」，驗收準則為「PR 的 diff 不含 `aidlc-state.md` 的任何一行」。**「同步專用檔案」是什麼，上游從未指名。**

**裁定：反向紀錄寫進 `<record>/sync-state.json` 的新欄位 `pending_reverse`。**

```
pending_reverse = { observed_status, observed_at } | null
```

四個理由：

1. **它本來就是「同步專用」的檔**——C-N1 為它訂了路徑且明文要求進版控，正是為了跨 runner 比對。沒有比它更符合 FR-G2 字面的檔案。
2. **與 L-1 的裁定一致**：綁定編號已於 U-10a 定案併入同一個檔。再開第三個 record 側檔案會讓 `paths-ignore`（U-10a）與 `paths` 白名單（U-4）都要多鎖一個路徑。
3. **PR 的 diff 自然只含 `sync-state.json`**，[req:FR-G2] 的驗收準則（不含 `aidlc-state.md` 任何一行）**結構上成立**，不需靠紀律。
4. **U-6 的 `reverse_pending` 偵測（讀 PR 的 diff 路徑）照常運作**——路徑是 `<record>/sync-state.json`，intent id 從路徑即可取出。

**代價**：`sync-state.json` 的 schema 再加一個欄位，需依 U-4 的 [Q2=A] 相容規則（只增不改、未知欄位保留）演進。**已由 U-4 的 `domain-entities.md` 承接該欄位**（先前寫「指派」，實際早已落地；措辭於送審前自檢更正，2026-08-29T23:42:35Z）；確認人為 **Bolt 3 的 gate**（U-8 落在 Bolt 3，U-4 在 Bolt 1——**跨 Bolt 的 schema 依賴**，見下方警示）。

> **⚠ 跨 Bolt 警示**：U-4 在 **Bolt 1** 上線、U-8 在 **Bolt 3**。若 Bolt 1 的 `sync-state.json` schema 未預留 `pending_reverse`，Bolt 3 上線時舊格式的檔案會缺該欄位——**這正是 U-4 的 R-2.2（讀取時補預設值）要處理的情形**，機制已存在。但 `schema_version` 是否要在 Bolt 3 遞增，需在該 Bolt 決定。

### E-2. **一個 intent 一個 PR**，不是全部合成一個

[ug:unit-of-work.md] 的 U-8 實作註記把 **over-suppression** 標為「本路徑的**真正風險**」：先例（`aidlc_sync_pull.py --all-intents`）一次處理全部 intent 並開**單一** PR，在該形狀下「某 intent 有未處理反向紀錄」無法只從 PR 開關狀態判定——**一個開著的 PR 會讓全部 intent 一起 `suppressed`**。

上游的處置是「以讀 PR 的 diff 是否含該 intent 的 record 路徑判定」，並標明**未實測**。

**裁定：每個有人為變更的 intent 各開一個 PR。**

理由：**這讓逐 intent 判定從「推導出來的」變成「結構上就是」**。一個 PR 的 diff 只含一個 intent 的路徑，[US:S-6 AC 3] 的反例要求（X 在 PR 內、Y 不在，Y 照常寫）**不可能失敗**——因為 X 的 PR 與 Y 無關。

**這不牴觸上游的機制**：U-6 仍然讀 PR 的 diff 路徑算 `reverse_pending`，只是每則 PR 只貢獻一個 intent id。**上游的 mechanism 維持，它的風險消失。**

**代價**：
- 看板上多個 intent 同時被人改動時會產生多個 PR。**但反向 PR 只在有人為變更時才開**——那是低頻事件，不是每日常態。
- 每個 PR 各觸發一次 `on: pull_request` 的 workflow 評估。**U-10b 的排除對每個都生效**，成本不隨 PR 數放大。

  > **成本論證的機制已更換（iteration 3 M-2，2026-08-30T00:05:00Z）**：先前寫「`branches-ignore` 對每個都生效（前綴相同）」，而該機制已被證偽（見上）。**E-2「一個 intent 一則 PR」的結論不變**，但支撐它的是 U-10b 的 `paths-ignore`——它比對的是變更路徑（反向 PR 只動 `<record>/sync-state.json`），對每則 PR 同樣一律生效，故「成本不隨 PR 數放大」仍然成立，只是理由不同。依 `project.md` 的 `functional-design:c22`，只修理由不改決定。
- CAP-11 的「未實測」標記**不因此消除**——它現在標的是「一個 PR 一個 intent 的形狀是否如預期運作」，仍需 Bolt 3 實測，但**失敗模式從「全域誤暫停」降為「該 intent 未暫停」**，嚴重度顯著下降。

[Answer]: 本站裁定，非人工裁決  <!-- 2026-08-29T13:19:07Z（讀自 date -u） -->

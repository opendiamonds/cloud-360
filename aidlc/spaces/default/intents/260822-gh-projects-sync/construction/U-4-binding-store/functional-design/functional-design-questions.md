# Functional Design — U-4 record 回寫與同步狀態

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-4-binding-store · kind: library -->

## CONDITIONAL 適用性判定

| 條款 | 判定 | 依據 |
| --- | --- | --- |
| New data models | ✅ | `sync-state.json` 的 schema 完全未定義，只知道「需含版本欄位」 |
| Complex business logic | ✅ | read-modify-write ＋ 並行衝突 ＋ 跨版本相容 |
| Business rules need design | ✅ | 見下方兩個缺口 |
| Skip if simple logic changes | ❌ | 新模組 |

**判定：EXECUTE**（`kind: library` → 三份產出）。

## 已由上游定案、本站不重問

| 事項 | 出處 |
| --- | --- |
| 四個方法的簽章；`read_binding` 缺席回 `null`（觸發首建） | [ad:component-methods.md] §C-4 |
| `commit_and_push` **只推觸發分支**；`paths` 限 record 目錄下的綁定編號與 `sync-state.json`；訊息必含 `[aidlc-sync]` | 同上 |
| `write_binding` 檔案寫入失敗 → 拋 `ExternalError` | 同上 |
| **[US:S-1 AC 7]（回寫不得取消既有 `ci.yml` run）不歸本單元**，歸 U-10a | [ug:unit-of-work.md] 的 U-4「不擁有」欄（消依賴環） |
| `sync-state.json` 需含版本欄位、跨輪相容性必須維持 | [ad:services.md] 的服務契約 |

## 本站發現的上游契約缺口

### 缺口 H-1：`Rejected` 把兩種成因不同的失敗合成一個回傳值

[ad:component-methods.md] 對 `commit_and_push` 寫了兩件事，但它們指向**同一個** `Rejected`：

1. 「push 被**分支保護**拒絕 → 回 `Rejected`，交 C-5 通報 ＋ **紅燈**」
2. `read_sync_state`／`write_sync_state` 那一列：「read-modify-write；**並行衝突**由 `commit_and_push` 的 push 失敗表現」

兩者的性質完全不同：

| 成因 | 性質 | 正確處置 |
| --- | --- | --- |
| 分支保護拒絕 | **永久**——重試一百次也一樣 | 紅燈 ＋ 通報，需人介入 |
| non-fast-forward（並行推送） | **暫時**——重讀重推即可成功 | 重試，不該紅燈 |

**擋住**：[req:FR-A3] 的回寫在並行情境下會**誤報紅燈**。而 [ad:services.md] 明列只有 `ExternalError` 與 `Rejected` 紅燈——把暫時性衝突歸進 `Rejected`，等於每次並行都拉一次假警報，稀釋真警報的價值。
**落點**：本站 Q1 裁定。

### 缺口 H-2：`sync-state.json` 的相容規則只有目標，沒有規則

[ad:services.md] 要求「跨輪相容性必須維持——舊格式的檔案在新版讀取時不得崩潰。schema 需含版本欄位」。**目標明確，規則未定**：新版讀舊檔怎麼補預設值、**舊版讀新檔**怎麼辦（Bolt 上線期間排隊中的舊 run 仍會執行）、未知欄位在 read-modify-write 後是否保留。

**擋住**：`write_sync_state` 的行為在跨版本情境下未定義。
**落點**：本站 Q2 裁定。

---

## 問題

### Q1. `commit_and_push` 的兩種失敗怎麼區分？（缺口 H-1）

A. **在 `commit_and_push` 內部重試 non-fast-forward，簽章不變**：偵測到非快轉時重新 pull／rebase 該 record 的兩個檔案並重推，重試 N 次後仍失敗才回 `Rejected`。看得到的效果：**不動已核可的回傳型別**；暫時性衝突不再誤報紅燈；read-modify-write 本來就是需要這個迴圈的模式。代價：`commit_and_push` 從「一次動作」變成「有內部迴圈的動作」，失敗時較難從外部分辨它試了幾次；且重試上限 N 是一個新的魔術數字。

B. **把 `Rejected` 拆成兩個回傳值**：`Rejected`（分支保護，永久）與 `Conflicted`（非快轉，暫時）。看得到的效果：語意最清楚，呼叫端能各自處置。代價：**更動已通過三輪 reviewer 的 [ad:component-methods.md] 回傳型別**，屬對已核可上游的修改，依紀律應回上游走 Modify 而非在本站就地改。

C. **不重試，接受誤報**：並行衝突照回 `Rejected` 並紅燈。看得到的效果：實作最單純。代價：由於選取是 registry 驅動且以漂移判定，下一輪事件會自然重做——**資料上沒有損害**，但每次並行都拉一次假警報。[ad:services.md] 已把紅燈定義為「需要人看」的訊號，稀釋它的代價會隨時間累積。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T12:05:34Z（讀自 date -u）· 內部重試非快轉，簽章不變 -->

### Q2. `sync-state.json` 的跨版本相容規則？（缺口 H-2）

A. **只增不改 ＋ 未知欄位原樣保留**：schema 演進限於新增欄位；讀取時對缺席欄位補預設值；**read-modify-write 時把不認得的欄位原樣寫回**。看得到的效果：新版讀舊檔、**舊版讀新檔**都不崩潰也不遺失資料——後者正是 Bolt 上線期間排隊中的舊 run 會遇到的情形。代價：欄位只能加不能改語意，schema 會累積歷史包袱；且「原樣保留」需要實作端刻意不做欄位白名單過濾，這在 JSON 處理中是**反直覺**的（多數寫法會靜默丟棄未知鍵）。

B. **版本閘門：讀到高於自己的版本就拒絕寫入**：與 U-2 的 `parse` 對未知版本回 `null` 同精神（保守不猜）。看得到的效果：舊版絕不覆寫新格式；行為與 U-2 一致，一套心智模型。代價：拒絕寫入代表**該輪的同步狀態沒被記錄**，下一輪會重做；若新舊版本同時運行一段時間，舊 run 會持續空轉且無人察覺（拒絕寫入不紅燈——它不是錯誤）。

C. **A ＋ B 併用**：未知欄位原樣保留（A），**且**讀到主版本號高於自己時拒絕寫入（B）。看得到的效果：次要演進（加欄位）由 A 吸收不中斷；破壞性演進（改語意）由 B 擋住。代價：需要區分「主版本」與「次版本」，多一層規則；且什麼算破壞性變更需要人判斷，不是機械可判的。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T12:05:34Z（讀自 date -u）· 只增不改 ＋ 未知欄位原樣保留 -->

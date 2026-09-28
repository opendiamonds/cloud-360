# Business Rules — U-4 record 回寫與同步狀態

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-4-binding-store · kind: library -->

## R-1 群：綁定編號

| # | 規則 | 來源 |
| --- | --- | --- |
| R-1.1 | `read_binding` 缺席回 `null`——此值**觸發首建**（U-3 的 `create_item`） | [ad:component-methods.md] §C-4 |
| R-1.2 | `write_binding` 檔案寫入失敗 → 拋 `ExternalError`（紅燈） | 同上 |
| R-1.3 | 綁定編號是 `sync-state.json` 的 `binding` 欄位（缺口 L-1 定案）；`read_binding`／`write_binding` 與 `read_sync_state`／`write_sync_state` 是**同一份檔案的兩組存取器**，不是兩份資料 | 缺口 L-1（於 U-10a 的 nfr-requirements 定案）。四個方法的簽章仍引自 [ad:component-methods.md] §C-4，**一字未改** |

> **R-1.3 已更正**：先前寫「兩份獨立資料，不得合併」。上游從未定義綁定編號的儲存落點，該缺口在 U-10a 被逼出來（`paths-ignore` 必須逐字寫出路徑）。併入後 `paths-ignore` 只需鎖一個已有 C-N1 規定的路徑。「四個獨立方法」與「一份檔案」不矛盾——前者是介面、後者是儲存，`team.md` 的單一真實來源因此成立。

**R-1.1 是一條有真實後果的規則，不是形式**：`requirements.md` 的 A-8 明記「同步身分對 feature 分支有寫入權且不受分支保護阻擋」**未驗證**。若回寫失敗，下次 push 時 `read_binding` 又回 `null` ⇒ 又走首建 ⇒ **每 push 一次多一張卡**。

U-3 的 R-3.1（先檢查是否已有綁定編號）攔得住 workflow 重跑，**攔不住回寫失敗**——因為它依賴的正是回寫失敗時不存在的東西。**這條路徑上唯一真正的防線是 R-1.2 與 R-3 群的 `Rejected` 會紅燈 ＋ 通報。**

## R-2 群：`sync-state.json` 的跨版本相容（[Q2=A]）

| # | 規則 |
| --- | --- |
| R-2.1 | schema 演進限於**新增欄位**；不得改既有欄位的語意或型別 |
| R-2.2 | 讀取時對缺席欄位**補預設值**，不視為錯誤（新版讀舊檔） |
| R-2.3 | read-modify-write 時**把不認得的欄位原樣寫回**（舊版讀新檔） |
| R-2.4 | `schema_version` 只增不減；讀到高於自己的版本**不拒絕**，照 R-2.3 處理 |

**R-2.3 必須被測試鎖住，理由是它反直覺。** 多數 JSON 處理寫法會靜默丟棄未知鍵——那正是這條規則要防的行為。

**必要的 fixture**：給一份含未知欄位的 `sync-state.json`，執行一次 read-modify-write，斷言**未知欄位仍在且值未變**。沒有這個 fixture，R-2.3 會在第一次有人重構 JSON 處理時無聲消失。

**R-2.4 與 U-2 的 `parse` 刻意不同**：U-2 對未知版本回 `null`（保守不猜），本單元照常處理。差別的理由是後果不同——U-2 猜錯會**覆寫**一個更新版本機制維護的看板 item；本單元照常處理只是保留了自己不認得的欄位，不會破壞任何東西。兩者都是「選對自己情境的保守方向」，不是不一致。

## R-3 群：`commit_and_push`（[Q1=A]）

| # | 規則 | 來源 |
| --- | --- | --- |
| R-3.1 | **不得推 `ut`／`main`**。正向同步（**U-6**）只推觸發分支；**對帳（U-7）推其排程觸發分支**；反向同步（U-8）推自建的 `aidlc-sync/reverse/*` 分支 | [ad:component-methods.md] |

> **這一句被改過兩次，方向相反。**
>
> - **iteration 1（2026-08-29T15:25:28Z，Major）**：「／U-7」被移除。當時的理由成立——U-7 三份產出零次提及 C-4／`commit_and_push`，且 [ad:components.md] 把 reconcile 的元件集合定為 `C-7 →（內部）C-2／C-1／C-3／C-5`，**沒有 C-4**。
> - **iteration 3（2026-08-30T00:57:28Z）**：U-7 加回來了。**移除的前提被人工裁決翻掉**——Q5=A（見 `../U-6-forward-workflow/functional-design/functional-design-questions.md`）決定由 **ADR-0015 §13** 給 reconcile 的元件鏈補上 C-4，讓 U-7 補平看板後一併回寫 `SyncState`；否則 U-6 的 `write_status` 每次都拿過期的 `expected` 去比，補平愈成功、假通報愈多。U-7 的呼叫規則見其 `business-rules.md` 的 **R-6 群**。
>
> **記下這個來回本身**：iteration 1 的移除不是誤判，它如實反映了當時的元件鏈；改變的是元件鏈，不是判斷。純比對兩份文件的人會看到一個「加回又拿掉又加回」的欄位而誤判為反覆，故在此寫明兩次各自的依據（`refined-mockups:c3` 的形狀）。
>
> **實作期須確認（ADR-0015 §13 標出、不裁定）**：`schedule` 觸發只在**預設分支**上執行，所以 U-7 的「觸發分支」是預設分支而非 `ut`。這與 R-3.1 的「不得推 `ut`／`main`」是否相容，須在 Bolt 2 開工前確認——若預設分支就是 `main`，兩者直接衝突。

> **R-3.1 的措辭在 U-8 的審視下修正過。** 原文寫「只推觸發分支」，但 U-8 推的是新建的反向分支——字面上兩者衝突。這條規則的**實質**是「不得直接推整合主幹」，`branch` 本來就是 `commit_and_push` 的參數；「只推觸發分支」描述的是正向路徑的**呼叫方式**，不是方法的內建限制。此為本站內部的對齊修正，不是新定案，[ad:component-methods.md] 的簽章一字未改。
| R-3.2 | `paths` 限 record 目錄下的綁定編號與 `sync-state.json` | 同上 |
| R-3.3 | commit 訊息**必含** `[aidlc-sync]` | 同上（[req:FR-A4] 的自我排除依賴它） |
| R-3.4 | 分支保護拒絕 → `Rejected`，交 C-5 通報 ＋ **紅燈** | 同上 |

### R-3.5：非快轉的內部重試（[Q1=A]）

推送失敗且成因為**非快轉**（並行推送）時，`commit_and_push` **在內部**重新取得該分支上那兩個檔案的最新內容、重新套用本輪的變更、重推。重試上限 **N = 3**。

| 情形 | 回傳 |
| --- | --- |
| 首次或重試中任一次推送成功 | `Pushed` |
| 重試 3 次後仍非快轉 | `Rejected` |
| 分支保護拒絕（任何一次） | `Rejected`，**立即**——不重試（重試一百次也一樣） |

**簽章維持 `Pushed | Rejected` 不變**（[Q1=A]），因此不動已核可的 [ad:component-methods.md]。

**N = 3 是本站引入的數字，沒有上游依據**——[Q1=A] 的選項本文已載明「重試上限 N 是一個新的魔術數字」。選 3 的理由是：非快轉在本設計中只可能來自另一個同步 run 正在寫**同一個 record**，而 [ad:services.md] 的 S-A concurrency group 已把同分支的事件序列化，故真正的並行來源只剩「事件路徑與排程對帳同時跑」——那是**兩個**寫入者，3 次重試足以讓其中一個先完成。**若實測發現不足，改的是這個數字，不是規則形狀。**

**必要的區分能力**：本規則要求實作能分辨「分支保護拒絕」與「非快轉」。兩者在 `git push` 的輸出中形狀不同（前者為 `protected branch hook declined` 類訊息，後者為 `non-fast-forward`／`fetch first`），但**都以非零 exit code 表現**——只看 exit code 無法區分，必須解析 stderr。這與 U-3 的「GraphQL 錯誤在 HTTP 200 的 body 裡」是同型的陷阱。

## R-4：本單元**不擁有** [US:S-1 AC 7]

回寫 commit 不得取消既有 `ci.yml` run 這件事**歸 U-10a**，不歸本單元。

理由（[ug:unit-of-work.md] 的 U-4「不擁有」欄逐字）：讓那件事為真的機制是 `ci.yml` 的 `paths-ignore`，不是本單元的回寫行為。若兩處都掛，U-4 需要 U-10a 才驗得完、U-10a 需要 U-4 才有 commit 可測——**依賴圖會出現環**。

**但兩者是同批次約束**（`unit-of-work-dependency.md` 的真捆綁之一）：U-4 先上而 `paths-ignore` 未上線 ⇒ 每次回寫都取消開發者當下的 CI run。**本單元的完成不代表該 AC 已滿足。**

## 與上游的對應

四個方法的契約引自 [ad:component-methods.md] §C-4；`sync-state.json` 的跨輪相容要求引自 [ad:services.md]；紅燈語意引自同檔；FR-A3／FR-A4 與假設 A-8 引自 `requirements.md`；[US:S-1 AC 6]／[AC 7] 引自 `stories.md`；單元邊界、完成判準、「不擁有」欄與同批次約束引自 [ug:unit-of-work.md] 與 `unit-of-work-dependency.md`；AC 歸屬引自 [ug:unit-of-work-story-map.md]；元件分層引自 [ad:components.md]；`content_hash` 的歸屬引自 U-2 的 `domain-entities.md`。

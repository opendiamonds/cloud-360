# Domain Entities — U-4 record 回寫與同步狀態

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-4-binding-store · kind: library -->

## `sync-state.json` 的 schema（缺口 H-2 的落點）

[ad:services.md] 只要求「需含版本欄位、跨輪相容性必須維持」，schema 本身未定義。本檔補上。

檔案位置 `<record>/sync-state.json`（[req:C-N1]）。

| 欄位 | 型別 | 語意 |
| --- | --- | --- |
| `schema_version` | 正整數 | 本檔的 schema 版本。**只增不改**（[Q2=A]） |
| `binding` | 整數 \| `null` | **綁定的 issue 編號**（缺口 L-1 定案）。`null` 代表尚未首建 |
| `last_status` | `Status` \| `null` | 上一次成功寫入看板的 Status；`null` 代表尚未寫過 |
| `last_field_value` | 字串 \| `null` | 上一次成功寫入的自訂欄位值 |
| `last_reason_code` | `ReasonCode` \| `null` | 上一次判定的 `reason_code`（含「決定不寫」的情形） |
| `managed_block_hash` | sha256 \| `null` | 上一次寫入時受管區塊的雜湊（由 U-2 的 `content_hash` 產生，本單元只儲存） |
| `last_synced_at` | ISO 8601 字串 \| `null` | 上一次成功寫入的時刻；`null` 代表**尚未成功寫過**（首建之後、第一次寫入之前）。**型別於 iteration 3 m-3 補上 `null`（2026-08-30T00:05:00Z）**：同表其餘六欄皆明寫 `\| null`，唯獨此欄沒有，而 R-2.2 允許欄位缺席補預設，U-6 的 R-5.6／R-6.2c 又都以「PR 關閉時刻晚於 `last_synced_at`」為判準——缺席時的比較結果原本未定義。**定為：`null` 時該比較一律判為真**（從未寫過 ⇒ 任何 PR 關閉時刻都晚於它 ⇒ 告示尚未送出過），與這兩條規則「告示只出現一次」的意圖一致 |

> **這些欄位曾有第二條「寫看板但不寫本檔」的路徑，該路徑已被關閉（2026-08-30T01:31:09Z）。** U-7 的對帳補平經 C-3 `write_status` 直接寫看板，而 [ad:components.md] 原給 reconcile 的元件集合**不含 C-4**——它無法更新本檔任何欄位。**人工裁決 Q5=A 從源頭解決**：ADR-0015 §13 為 reconcile 補上 C-4，U-7 補平後依其 R-6 群一併回寫。
>
> **引言於本輪更正（reviewer iteration 4 Group A M-2）**：先前寫「本站判定這是可接受的（而非宣稱 U-7 會寫）」，與下方已改的表格直接相反——表格改了、框住它的引言沒改。界限如下：
>
> | 欄位 | 補平後 | 後果 |
> | --- | --- | --- |
> | `last_status`／`last_field_value`／`last_reason_code` | **不再過期** | **U-7 補平後會一併回寫這三欄**（ADR-0015 §13 給 reconcile 的元件鏈補上 C-4）。過期問題從源頭消失，本欄位群恆為「機制上次寫進看板的值」 |
> 
> > **這一列被改過兩次，兩次方向相反，完整記下來以免下一個人重走同一條路。**
> >
> > - **iteration 2（2026-08-29T16:21:11Z，Critical）**：原寫「重寫一次**相同的值**（冪等）——自癒」，那是錯的。U-7 補平後看板已是**新值**而本檔停在**舊值**，U-6 拿本檔的舊值當 `expected` ⇒ `write_status` 內部回讀比對必然不符 ⇒ `Aborted` ⇒ **每一次正常補平都製造一則假通報**。當時的修法是讓 U-6 改取當下 `read_item`（R-5.7）。
> > - **iteration 3（2026-08-30T00:57:28Z，Critical C-1）**：那個修法讓 `write_status` 的守門恆真、`Aborted` 不可達，[req:FR-C1]／[req:FR-C3]／[US:S-3 AC 1–2] 全部不可滿足。**假陽性被換成了所有真陽性一起消失。**
> >
> > **定案（人工裁決 Q5=A，`U-6/functional-design-questions.md`）**：`expected` 回到本檔的三欄，過期改從**源頭**解決——**ADR-0015 §13** 給 reconcile 補上 C-4，U-7 補平後一併回寫。誰寫看板誰就負責記錄自己寫了什麼。本檔的三欄因此恆為「機制上次寫進看板的值」，而 `ItemState` 仍是「看板現在是什麼」——**兩者的區分（U-6 的 R-5.8）不變，變的是誰負責讓本檔保持新鮮**。
> | `managed_block_hash` | **不受影響** | 補平只寫 Status 欄位，**不重寫受管區塊**（reconcile 的元件鏈含 C-4 但不含 C-6），區塊雜湊沒變 |
>
> 第二列是關鍵：若補平會重寫受管區塊而雜湊沒更新，U-8 就會把它誤判為人為變更並開反向 PR。**因為 reconcile 不碰受管區塊，這條路徑不成立。** 完整推導見 U-6 的 R-5 群。
>
> **`managed_block_hash` 有兩個寫者**：常態路徑是 **U-6 的 R-5.4**（寫入看板後回讀取值）；修復路徑是 **U-7 的 R-6.8**（U-6 曾寫成功但回寫失敗時，由對帳把看板上已存在區塊的雜湊補記進來）。本欄位先前完全沒有寫者，該缺口在 U-6 收斂；修復路徑於 2026-08-30T03:35:44Z 補上（iteration 6 確認審指出 U-4 此處未隨 R-6.8 更新）。
| `pending_reverse` | 物件 \| `null` | **未處理的反向變更**（缺口 N-1 定案，見下）。`null` 代表無 |

`pending_reverse` 非 `null` 時的形狀：`{ observed_status, observed_at }`。

> **缺口 N-1 的落點在本檔（跨 Bolt，務必留意）。** [req:FR-G2] 要求反向同步「只寫一個同步專用檔案」且其 PR diff「不含 `aidlc-state.md` 的任何一行」，但**上游從未指名那個檔**。U-8 的 functional-design 裁定為本檔的 `pending_reverse`，理由是它讓 FR-G2 的驗收**結構性成立**（PR 的 diff 只可能含這一個檔）而非靠紀律。
>
> **它必須在 `schema_version` 1 就存在，不是後來新增。** U-4 在 **Bolt 1** 交付、U-8 在 **Bolt 3**——若 Bolt 1 不含此欄，Bolt 3 就得改 schema，而 C-1 雖允許新增欄位、C-2／C-3 也能吃下，但那會讓 Bolt 1 與 Bolt 2 之間存在一份「讀得到卻沒人寫」的欄位，並多一次不必要的版本演進。**本單元只負責讀寫與保存它，不解讀其內容。** 寫入由 U-8 的 R-1.3 定義；**本機制不清除它**（U-8 的 R-6 群：它在 `ut` 上非 `null` 等價於曾有一則反向 PR 合併過，且無任何單元讀它做控制流）——先前此處寫「何時清空由 U-8 與 U-6 決定」而兩者皆未定義，該缺口已於 functional-design 的 reviewer iteration 1 被抓出並在 U-8 收斂。U-6 不寫此欄位，它用的是每輪即時算出的 `Config.reverse_pending`（該單元 R-2 群），兩者是不同的東西。

**綁定編號就在這個檔裡**（缺口 L-1，於 U-10a 的 nfr-requirements 定案）。

> **先前此處寫「綁定編號不在這個檔裡」，已更正。** 缺口的成因：上游從未定義綁定編號的儲存落點——[US:S-1 AC 2] 只說「record 內存在一個**可機器讀取的欄位**」、[ad:component-methods.md] 的 `write_binding(record_path, issue_number)` 只給 record 路徑、`commit_and_push` 的 `paths` 說「限 record 目錄下的綁定編號與 `sync-state.json`」。**U-10a 的 `paths-ignore` 必須逐字寫出那個路徑**，缺口因此在該單元被逼出來。
>
> 定案併入本檔的直接後果：`paths-ignore` 只需鎖 `<record>/sync-state.json` 一個已有 C-N1 明確規定的路徑，**不需要為綁定編號新增一個同等規定的檔**；且回寫從兩次檔案寫入降為一次。
>
> **`read_binding`／`write_binding` 與 `read_sync_state`／`write_sync_state` 仍是四個獨立方法**（[ad:component-methods.md] 的簽章一字未改）——它們是**同一份檔案的兩組存取器**，不是兩份資料的複製。`team.md` 的「單一真實來源」因此成立而非被違反。

**`managed_block_hash` 由 U-2 產生、本單元只儲存**：本單元不得自行計算它，否則 U-2 的格式知識會有第二份物化（`team.md` 的「單一真實來源」）。

## 跨版本相容規則（[Q2=A] 定案）

> **命名提醒**：本節的 `C-1`／`C-2`／`C-3` 是**本檔的相容規則編號**，與本 intent 其他各處的 `C-1`～`C-7`（[ad:components.md] 的元件識別碼，本單元自己是 **C-4**）**是不同的命名空間**。引用時務必連同出處一起寫，避免與元件混淆。

三條，缺一不可：

| # | 規則 | 保護的情形 |
| --- | --- | --- |
| C-1 | schema 演進**限於新增欄位**，不得改既有欄位的語意或型別 | 所有 |
| C-2 | 讀取時對**缺席欄位補預設值**，不視為錯誤 | 新版讀舊檔 |
| C-3 | read-modify-write 時把**不認得的欄位原樣寫回** | **舊版讀新檔** |

**C-3 是三條中唯一反直覺的一條，也是最重要的一條。**

它保護的情形是：Bolt 上線期間，一個**排隊中的舊 run** 讀到新版本寫出的檔案。若舊 run 用欄位白名單解析再整份重寫（這是 JSON 處理最常見的寫法），新版新增的欄位會被**靜默丟棄**——而新版下一輪會發現那些欄位不見了，把它當成「從未寫過」重新推導。

多數 JSON 序列化寫法預設就會丟棄未知鍵，所以 C-3 必須被**刻意實作**且**被測試鎖住**。見 `business-rules.md` R-2.3。

**已知代價（[Q2=A] 選項本文即已載明）**：欄位只能加不能改語意，schema 會累積歷史包袱。這是為了讓兩個方向的跨版本讀取都不損資料而付的價。

## `commit_and_push` 的回傳（缺口 H-1 的落點）

簽章 `(branch, paths, message) -> Pushed | Rejected` **維持不變**（[Q1=A]）。

| 回傳 | 何時 | 紅燈？ |
| --- | --- | --- |
| `Pushed` | 推送成功（**含內部重試後成功**） | 否 |
| `Rejected` | 分支保護拒絕，**或**內部重試 N 次後仍非快轉 | **是**——交 C-5 通報 ＋ 紅燈 |

**`Rejected` 現在只在「重試無用」時出現**，其語意因此收斂為「需要人介入」，與 [ad:services.md] 對紅燈的定義（需要人看的訊號）一致。重試邏輯與 N 的定義見 `business-rules.md` R-3 群。

## 與上游的對應

`pending_reverse` 的存在理由與形狀引自 U-8 的 `functional-design/business-logic-model.md`（缺口 N-1 的裁定），本單元只承接其儲存契約；四個方法的簽章與錯誤處理引自 [ad:component-methods.md] §C-4；`sync-state.json` 的位置與「需含版本欄位、跨輪相容」引自 [ad:services.md] 的服務契約與 `requirements.md` 的 C-N1；`Status`／`ReasonCode` 型別引自 U-1 的 `domain-entities.md`；`content_hash` 的歸屬引自 U-2；單元邊界、完成判準與「不擁有 [US:S-1 AC 7]」引自 [ug:unit-of-work.md] 的 U-4；AC 歸屬引自 [ug:unit-of-work-story-map.md]；元件分層引自 [ad:components.md]；FR-A3 引自 `requirements.md`。

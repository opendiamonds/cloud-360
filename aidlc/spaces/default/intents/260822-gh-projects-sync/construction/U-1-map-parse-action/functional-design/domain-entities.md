# Domain Entities — U-1 映射與解析 composite action

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-1-map-parse-action
     本檔定義 U-1 擁有的型別、它們的欄位語意與生命週期。
     上游 [ad:component-methods.md] §共用型別已給欄位名，本檔補語意、值域與缺漏。 -->

## 本單元擁有的型別

依 [ug:unit-of-work.md] 的 U-1 定義，本單元擁有 [ad:components.md] 的 C-1 `sync-map` 與 C-2 `record-reader`，兩者合併為一個 composite action。下列型別的**語意**由本檔定義；欄位名沿用 [ad:component-methods.md] §共用型別，**一個都沒有改**。

### `ParsedRecord`

C-2 `parse` 的成功輸出。零 I/O——全部欄位都從傳入的文字推導。

| 欄位 | 值域 | 語意與來源 |
| --- | --- | --- |
| `intent_id` | 非空字串 | record 目錄名。**不從 `aidlc-state.md` 內文取**，由 `record_path` 參數推導 |
| `current_stage` | 字串 \| `null` | `get_field(text, "Current Stage")`。**缺席回 `null`、存在但空回空字串**，兩者不可混同 |
| `runtime_status` | 字串 \| `null` | `get_field(text, "Status")`。判定第 3 條讀的就是它（[US:S-2 AC 3] 明文「讀 `Status` 欄位而非推導 checkbox」） |
| `parked` | 字串 \| `null` | `get_field(text, "Parked")`。**`null`（缺席）與空字串（存在但無值）都視為「未暫停」**；只有非空字串才觸發判定第 1 條 |
| `parked_at_stage` | 字串 \| `null` | 同上取法。僅用於組 `field_value` 的 `parked @ ` 前綴內容，不參與判定 |
| `stages` | `[{slug, checkbox, in_scope}]` | `list_stages` 的輸出，見下 |
| `binding` | 整數 \| `null` | 綁定的 issue 編號。`null` 代表尚未首建（[req:FR-A1] 的首建路徑判別依據） |

> **`parked` 的三態壓成二態是刻意的**：[ad:component-methods.md] §C-2 的 `get_field` 第 3 條註記指出，現況 record 的 `## Runtime State` 只有 `- **Revision Count**: 0`，`Parked` 是**缺席**而非空值；若把缺席誤讀成空字串以外的東西，park 特判永不觸發。本檔把「缺席」與「空」都定為「未暫停」，使該註記所警告的失敗模式在兩個方向上都不成立。

### `stages[]` 的元素

| 欄位 | 值域 | 語意 |
| --- | --- | --- |
| `slug` | 非空字串 | stage 識別字，逐檔解析（[req:FR-J4] 明文不得寫死） |
| `checkbox` | `" "` \| `"-"` \| `"?"` \| `"R"` \| `"x"` \| `"S"` | 方括號內的單一字元，原樣保留不正規化 |
| `in_scope` | 布林 | **依 [Q3=C] 定案**：該行尾綴為 `EXECUTE` 則真、`SKIP` 則偽 |

> `checkbox == "S"`（jump 跳過）與 `in_scope == false`（`— SKIP`）是**兩件不同的事**，[req:FR-B3] 要求區分。前者是「這一站在範圍內但被跳過」，後者是「這一站根本不在範圍內」。合併會讓 [US:S-4 AC 4] 的差別消失。

### `Unparseable`

| 欄位 | 值域 | 語意 |
| --- | --- | --- |
| `intent_id` | 字串 \| `null` | 能從 `record_path` 推得就給，推不得為 `null` |
| `missing` | 非空字串陣列 | 缺失項的識別字。目前值域：`"stage-progress-section"`（無 `## Stage Progress` 區塊）、`"stage-lines"`（[Q3=C] 新增：區塊在但零行 match） |

> `missing` **必須非空**——空陣列的 `Unparseable` 無法說明為何無法解析，會讓 [US:S-9] 的「無法解析」清單變成一串沒有理由的 id。

### `Decision`

C-1 `map` 的唯一輸出。[US:S-2 AC 15] 的總函式性要求：對任一輸入**恰好**產生一個 `Decision`，沒有第三種結果、不拋例外。

| 欄位 | 值域 | 語意 |
| --- | --- | --- |
| `status` | `Status` \| `null` | `null` 是**合法輸出**，代表「決定不寫」 |
| `field_value` | 字串（可為空） | 自訂欄位值，格式見 `business-rules.md` |
| `reason_code` | `ReasonCode` | **一律非空**。`status` 非 `null` 時為 `"mapped"` |
| `traceable_row` | 非空字串 | 命中的對照表列識別字，或不寫的理由。供受管區塊與對帳報告引用 |

`Status` 與 `ReasonCode` 的值域逐字沿用 [ad:component-methods.md]，本檔不擴充。

### `scope_note`（第五個 output，型別段補記）

字串，由 `ParsedRecord.stages` 純函式推導，格式與值域見 `business-rules.md` 的 **R-6 群**。**不是 `Decision` 的欄位**——[req:FR-B3] 明訂 `[S]`／`— SKIP` 對 Status 無影響，故它不進 `map()` 的輸出，而是 composite action 與 `Decision` 四欄並列的第五個 output。消費者是 U-6（轉交進 `Context`）與 U-2（渲染進 `Block.scope_note`）。

### `Config`（缺口 F-1 的落點）

[ad:component-methods.md] 在六個方法簽章使用 `Config` 但**未定義它**。本檔補上 `map` 與 `field_value_for` 這兩個 U-1 方法所需的部分；C-3／C-7 所需的欄位由那些單元的 functional-design 各自補充，**本檔不代為定義**。

| 欄位 | 型別 | 為什麼 U-1 需要它 |
| --- | --- | --- |
| `whitelist` | 字串集合 | [req:FR-J5] 的白名單判定。命中者的 `reason_code` 為 `"whitelisted"` 而非 `"unparseable"`（[US:S-3 AC 6] 的前後半） |
| `reverse_pending` | 字串集合 | **[Q2=A] 定案**。判定第 2 條所需（[req:FR-G3]）。由 workflow 層在逐 record 迴圈**之前**組出，來源是**開啟中的反向同步 PR 的變更路徑**（U-8 的機制，見 `business-rules.md` R-3.2 的來源更正）。**不是** `sync-state.json`——先前版本如此寫，已於 reviewer iteration 1 更正 |
| `record_root` | 字串 | record 根目錄。[F1=A] 要求不得寫死 |
| `field_max_length` | 整數，預設 50 | 自訂欄位長度上限。參數化而非常數，理由同上 |

> **`Config` 同時裝「設定」與「本輪狀態」是刻意的兩用**，不是命名疏失。[Q2=A] 的選項本文已載明此代價，取的是「`map()` 維持已核可簽章一字不改、且仍是純函式」——同樣的 `(ParsedRecord, Config)` 必得同樣的 `Decision`，[US:S-10 AC 1] 的 fixture 驅動因此不受影響。`reverse_pending` 由呼叫端算好傳入，`map()` 自己不做任何 I/O，[ad:components.md] 的「C-1 不擁有任何 I/O」仍然成立。

### `Config` 的承載形式（Q1=A ＋ Q2=A 的連帶裁定）

composite action 的 `inputs` 是固定名稱的字串，而 `whitelist` 與 `reverse_pending` 是變長集合。序列化形式定為：

- **純量設定**（`record_root`、`field_max_length`）→ 各自一個具名 input。
- **集合型設定**（`whitelist`、`reverse_pending`）→ 各自一個**換行分隔的單一字串** input；空字串代表空集合。

理由：與 [Q1=A] 選的「YAML 層一眼看得出這個 action 吃什麼／產出什麼」一致；換行分隔在 `inputs` 與 `$GITHUB_OUTPUT` 兩側都不需跳脫處理，而**跳脫正是 [Q1=B] 的 JSON 方案被放棄的理由**——同一個理由不應該在輸入側被反向套用。

## 生命週期

三個型別都是**單次 workflow run 內的程序內值**，不落地、不跨 run 存活。[ad:services.md] 明記狀態只存在兩處（Project #16 本身、record 目錄下的 `sync-state.json` 與綁定編號），本單元一處都不寫。

```
state_md_text ─┐
intents_json ──┼─► parse ─► ParsedRecord ─┐
record_path ───┘         └► Unparseable ──┼─► map ─► Decision ─► （交給呼叫端）
                                  Config ─┘
```

文字 fallback：`parse` 吃三段文字，產出 `ParsedRecord` 或 `Unparseable`；兩者之一連同 `Config` 進入 `map`，產出唯一的 `Decision`，由 composite action 的 **五個** output 交給呼叫端（`Decision` 的四欄 ＋ `scope_note`，後者於 iteration 3 增設，見 `business-logic-model.md` 介面表）。全程無 I/O、無網路、無檔案系統存取。

## 與上游的對應

單元邊界與擁有關係引自 [ug:unit-of-work.md] 的 U-1 條目；AC 歸屬引自 [ug:unit-of-work-story-map.md]（S-2 的 AC 1–3、5–10、14、15 與 S-3 的 AC 3、5 完整屬本單元；**另有三條 partial**——S-2 AC 4 與 S-3 AC 6 的**判定**屬本單元、清單成員身分屬 U-7（見 `business-rules.md` R-4 群與上游標出的缺口 G-1）；**S-3 AC 4**（分岔仍寫入並開 issue）的判定屬本單元、開 issue 屬 U-5）；需求編號引自 `requirements.md`；元件職責與「不擁有 I/O」的約束引自 [ad:components.md]；型別欄位名與方法簽章引自 [ad:component-methods.md]；「狀態只存在兩處」與 registry 驅動選取引自 [ad:services.md]。

**本檔新增而上游沒有的**有兩項：`Config` 的欄位（F-1）與 `missing` 的 `"stage-lines"` 值（[Q3=C] 的連帶）。

> **這個「兩」與缺口總數無關**（reviewer iteration 3 Minor）：本站標出的缺口共**四項**（F-1～F-4，見 `functional-design-questions.md`），此處數的是**這一份檔案**相對上游的新增項，只有 F-1 落在本檔、F-2 落在 `business-rules.md`、F-3 指派回上游、F-4 指派 U-6。兩個數字量的不是同一件事。

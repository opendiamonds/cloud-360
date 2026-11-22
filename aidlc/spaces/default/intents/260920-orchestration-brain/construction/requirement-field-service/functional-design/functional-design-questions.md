# Functional Design 問題檔 — `U20 requirement-field-service`

> 單元類型 **`service`**（`unit-of-work.md:308`），故 `produces_kinds` 要求
> `entities.md`、`rules.md`、`functional-spec.md`、`traceability.json` 四份；
> `frontend-components.md` 只對 `ui` 適用，本單元不產出。
>
> Depth **Minimal**，故只問「預設錯了會造成真實重工」的題目。本站四題。

## 一、上游已定案、本站不重問

| 事項 | 定案 | 出處（逐字核對過） |
|---|---|---|
| 欄位為**按 agent 分組的固定欄位**，不是自由鍵值對 | 定義是程式內常數，值是資料 | `[R12]`=D；`components.md:598-614`；`K-17` `field_definition_source` |
| 三態：從未填過／已填／已清空 | 從未填過＝無列；清空＝有列、`value` 為 null、`clearedAt` 有值 | `ADR-015`；`schema_rbac.sql` 的 `ck_system_requirement_fields_cleared_has_null_value` |
| 欄位定義被移除後的處置 | 值列保留、畫面不渲染該組、未填計數只算當前已宣告的欄位 | `[UG:G9]`=A；`schema_rbac.sql` 表 COMMENT |
| 未填計數與分組明細**同一次查詢推導、同一個回應回傳** | 不變量 `I-4` | `K-17` `read_fields` note；`[US:V-12]`／`[US:Q-14]` |
| 唯一性鍵 | `(system_id, agent_group, field_key)` 三欄 | `schema_rbac.sql` 的 `uq_system_requirement_fields_group_key`（`U18` 已交付） |
| per-project 判定只有一份 | 委由 `K-16` 的 `MembershipFacade.resolve_project_role`，本單元不自行查 `project_members` | `K-17` `delegation`；`ADR-012` |
| 系統→專案的對應 | 經 `HierarchyFacade.get_project_of_system`，不直呼 `hierarchy_service` | `hierarchy_facade.py:374`；`U7` 的 `BR1.5` |
| `write_field` 冪等、覆寫同一列 | 已定 | `K-17` `retry_and_idempotency` |
| 拒絕時的例外 | `RequirementFieldForbidden(story_id='K4', action, system_id)`，不是 `HTTPException` | `K-17` `on_denied` |
| 清空控件不在本輪畫面 | `U23` 不提供清空控件；`clear_field` 的呼叫端只有 `U13`／`U21` | `[US:D-15]`、`J-20` |
| 驗證方式 | `TestClient` HTTP ＋ allow/deny 雙向；PBT **不適用**於未填計數 | `unit-of-work.md:380`；`contract-summary.md:2147` |

**一處由已交付程式裁決、不出題的契約字面張力**：`K-17` 的 `anti_double_check` 寫
「`K4` 全域層由其 router 的 `require_story_action` 承擔、facade 不得重複」。但本單元
有一個**同進程**呼叫端 `U13 brain-gateway`，它不經 FastAPI 的 dependency 鏈——照字面
做，`U13` 的路徑上**全域層根本不會被檢查**。已交付的 `U19`（`membership_facade.py:93-111`
的 `_authorize_global`）遇到的是同一件事，它的處置是：**facade 以 `user_can` 自行評估
全域層，router 不掛 `require_story_action`**，權限矩陣仍只有一份。本站照該先例辦，
不出題；`anti_double_check` 要防的「同一層檢查兩次」仍然成立（只是那一次改在 facade）。

## 二、本單元承載的故事與其 AC

`unit-of-work-story-map.md:216` 指派 **`US11.2`、`US11.3`** 兩則給 `U20`。逐條判定：

| AC | 落在 `U20`？ | 理由 |
|---|---|---|
| `AC11.2.1` | **部分** | 「未填」的文字標示是 `U23` 的畫面；本單元提供它的資料來源（每欄的 `filledState`） |
| `AC11.2.2` | **是** | 「欄位錯綁到別組即紅燈」——`UnknownFieldKey` 是本單元的伺服器側判定 |
| `AC11.2.3` | **部分** | 「輸入的值不消失」是 `U23` 的畫面；本單元保證失敗時**不寫入半套**、回明確錯誤 |
| `AC11.3.1` | **是** | 計數 N 由本單元的單一查詢推導 |
| `AC11.3.2` | **是** | 填滿一欄後計數為 N−1——寫入與重讀都在本單元 |
| `AC11.3.3` | **是** | 全部已填時計數為 0 |

## 三、本站查出的缺口（提問的前提）

**`U18` 交給本單元的未決張力（`OPEN-CG18-6`）。** 已交付的
`system_requirement_fields.updated_on_behalf_of` 是 `INTEGER REFERENCES users (id)`
（`schema_rbac.sql` 的 `J)` 區塊），但它要記的是「代**哪個 agent** 寫」：

- `K-17` 的 `write_field` 簽章逐字為 `on_behalf_of: str|None`；
- `U18` 的 `entities.md` 該屬性逐字為「`users.id` 或 agent 識別」；
- 線框 §17 與 `mockups.md` M12 要顯示「由大腦（**成本 agent** 請求）」。

agent 不是 `users` 表的一列，所以照現狀寫，代寫的那一筆會被外鍵擋下。`U18` 的
code-summary 明寫「這條外鍵必須在 `U20` 落地前改掉」並指派本單元。**已查證：`U18`
的 DDL 只在本分支（`git branch -r --contains` 只有
`origin/danniel/docs/orchestration-brain-ideation`），尚未併入 `ut`、未部署**，所以
改它不需要針對既有環境寫 `ALTER`。

## 四、問題

### FD1. 「代寫者」欄要記什麼？

A) **改成記 agent 的識別字串**（建議）：欄位改為 `VARCHAR(64)`、拿掉指向 `users` 的外鍵，
   值必須是程式內已宣告的 agent 組識別字（例如 `cost`）。代價：改一次已交付的 `U18`
   表定義，觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步，以及
   `run_meta_schema_migration.py` 的後條件清單同步。因為尚未部署，不需要 `ALTER`。
B) **維持指向 `users`，代寫時記一個「大腦」系統帳號**：要新增一列系統帳號的 seed
   （同 `U9` 的保留 actor 做法，也是 seed 語意變更、同樣觸發 blocking 同步）；
   畫面上「哪個 agent」改由該欄所屬的 `agent_group` 推得。缺點：代寫者永遠是同一個
   帳號，若日後一個 agent 會替**別組**的欄位請求寫入，就分不出是誰請求的。
C) **維持現狀不改表**，`on_behalf_of` 一律留空，「代寫」改由另一個欄位或日誌表達。
   缺點：`U18` 的欄位 COMMENT 逐字寫明「一律留空會讓使用者無法分辨哪些值是自己填的——
   而那是這個欄位存在的唯一理由」，等於讓該欄失去意義。

[Answer]: A <!-- 2026-10-11T22:23:54Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

### FD2. 第一版要宣告哪些 agent 組與欄位？

欄位定義是程式內常數（上游已定），但**具體有哪些組、哪些欄位**，上游只有線框 §17 的
畫面範例：成本 agent 五欄（SLA、尖峰 TPS、使用客群、月預算上限、計費區域）、架構
agent 兩欄（可用性目標、資料保存年限）。

A) **照線框 §17 的兩組七欄**（建議）：與已核可畫面一致，`U23` 與 e2e 有具體欄位可對。
B) **只宣告成本 agent 一組**：本 intent 唯一真的會「要欄位」的是成本 agent；架構組等
   架構 agent 確定需要時再加。缺點：線框 §17 畫的是兩組，`AC11.2.2` 的「N 個分組」
   在 N=1 時驗不出「錯綁到別組」。
C) **定義留空，由後續 intent 補**：本單元只交付機制。缺點：`AC11.3.*` 的計數全為 0，
   沒有任何 AC 能真的驗。

[Answer]: A <!-- 2026-10-11T22:23:54Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

### FD3. 使用者把欄位內容刪光再按儲存，要怎麼處理？

已核可畫面沒有「清空」控件（`[US:D-15]`），但使用者仍可能把輸入框刪空後按儲存。

A) **視為清空**（建議）：空字串或只有空白的寫入，照 `ADR-015` 的清空語意處理
   （保留列、`value` 設 null、記 `clearedAt` 與 `updatedBy`），該欄回到「未填」。
   不新增任何控件，但使用者有了一條撤銷錯值的路；「已清空」這一態也因此在使用者
   路徑上變得可達（目前只有 `U13`／`U21` 能觸發）。
B) **拒絕寫入**：回驗證錯誤、值不變。使用者無法經畫面清空一個填錯的值，只能改成別的值。
C) **照存空字串**：該欄會被算成「已填」但內容是空的——與「未填」計數的語意矛盾，不建議。

[Answer]: A <!-- 2026-10-11T22:23:54Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

### FD4. 專案的一般成員能不能改需求欄位？

兩層串聯已定：全域層看 `K4`（目前 `view`／`edit` 依角色不同，見 `rbac_seed_data.py:349-358`），
per-project 層看該使用者在該專案的角色。本題問的是 per-project 那一層的對應。

A) **成員即可讀寫**（建議）：只要是該專案成員（`project_admin` 或 `member`）就能讀；
   要寫還須全域 `K4.edit`。理由：需求欄位是給 agent 用的工作資料，不是權限設定；
   限縮給管理者會讓一般成員在對話中說出的值也無法被大腦寫回（大腦是以該使用者的身分寫）。
B) **成員可讀、只有 `project_admin` 可寫**：寫入集中在管理者。缺點同上——一般成員的
   對話寫回會被拒，而 `U13` 拿到的是一個使用者看不懂的失敗。
C) **非成員也可讀**（只要有全域 `K4.view`）：與 `FR12.6` 的兩層串聯（任一層不過即拒）
   直接矛盾，不建議。

[Answer]: A <!-- 2026-10-11T22:23:54Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

## 五、Revision 1（審查 `review-01` 之後，2026-10-11T22:35:43Z）

**FD1 選項 A 的代價揭露不足，已向使用者更正並重新取得裁決。** 審查 `R-01` 查出：
選項 A 原文寫「因為尚未部署，不需要 `ALTER`」，而為了讓已用舊定義建表的資料庫收斂，
實際還需要（1）一段可重跑的收斂敘述（移除舊外鍵、改欄位型別，既有值一律設為 null——
目前沒有任何程式寫過此欄，故實際上不會有值），涵蓋本機資料庫與「若 `U18` 先合併上線」
的 staging；（2）驗證腳本對此欄型別與「無外鍵」的斷言；（3）`DEPLOY.md` 2.2.9 補一行
此欄說明。原文另稱要同步 `DEPLOY.md` 的「外鍵數 8→7」，該數字其實不在 `DEPLOY.md`。
選項 B、C 的代價不變。上方選項 A 的原文保留不改寫，以本段為更正。

### FD1-R. 知道完整代價後，FD1 還是選 A 嗎？

A) 維持 A：改成記 agent 識別　B) 改選 B：大腦系統帳號　C) 改選 C：不改表、一律留空

[Answer]: A <!-- 2026-10-11T22:35:43Z 使用者經選單重新作答 -->

### FD5. 審查其餘發現的處置

A) 現在全部修進設計　B) 只修兩個 Major　C) 全部帶進程式產生

[Answer]: A <!-- 2026-10-11T22:35:43Z 使用者經選單作答；本站審查額度已用完，修正後不再送審 -->

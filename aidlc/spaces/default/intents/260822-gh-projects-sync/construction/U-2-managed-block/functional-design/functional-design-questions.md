# Functional Design — U-2 受管區塊渲染與雜湊

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-2-managed-block · kind: library -->

## CONDITIONAL 適用性判定

| 條款 | 判定 | 依據 |
| --- | --- | --- |
| New data models | ✅ | `Block` 型別的欄位與其與 `Decision` 的關係，[ad:component-methods.md] 只給簽章未給結構 |
| Complex business logic | ✅ | `render` / `parse` / `content_hash` 三者的互逆性與涵蓋範圍 |
| Business rules need design | ✅ | **[ad:decisions.md] ADR-A6 明文把一項設計指派給本 stage**，見下方 Q1 |
| Skip if simple logic changes | ❌ | 新模組，非既有邏輯修改 |

**判定：EXECUTE**（`kind: library` → 三份產出，`frontend-components` 不適用）。

## 已由上游定案、本站不重問

| 事項 | 出處 |
| --- | --- |
| 受管區塊**必載的四項內容**（Status 與 `traceable_row` 或不寫的原因類別＋ISO 8601 時間戳、`[S]`／`— SKIP` 差別、OOS-2 說明、「空欄位＝不受管」說明） | [ad:component-methods.md] §C-6（[US-OQ-3] 定案） |
| 三個方法的簽章與錯誤處理（`parse` 無標記回 `null`） | 同上 |
| **不得以欄位級比對取代整塊雜湊** | [ad:decisions.md] ADR-A6 的 Alternatives Rejected；[req:FR-G4] 逐字要求「受管區塊**內容雜湊**比對」 |
| 格式一旦上線即為契約 | ADR-A6 的 Decision |

## 本站承接的契約缺口（iteration 3 補記，2026-08-30T00:48:38Z）

前表列的是「上游已定案、不重問」的事項；下表列的是**上游未定案、由本站補上**的，先前漏列（reviewer iteration 3 Group B F7：第二批改動未傳播到本檔）。

| 缺口 | 處置 | 承載 |
| --- | --- | --- |
| **`Context` 型別無定義**——`render: (Decision, Context) -> string` 只使用它，`component-methods.md` 從未給結構。形狀與 U-1 承接的 F-1（`Config`）相同 | 於 `domain-entities.md` 定義三個欄位：`decided_at`／`scope_note`／`rejection_notice` | 本 stage（本單元） |
| **`Block` 無欄位承載 [US:S-6 AC 5] 的告示** | `Block` 增設 `rejection_notice`，渲染規則為 `business-rules.md` 的 R-1.5 | **ADR-0015 §12**（含一次 `format_version` bump） |
| **受管區塊沒有寫者**——`render()` 的輸出在全 stage 產出中無任何具名持久化者 | §C-3 增設 `write_body: (binding, block_text) -> WriteResult` | **ADR-0015 §11** |
| **`Context.scope_note` 取不到**——`ParsedRecord` 不跨 U-1 composite action 邊界 | U-1 的 action 增設第五個 output `scope_note`，由 U-6 轉交 | 本 stage（U-1） |

---

## 問題

### Q1. 用什麼**機制**（而非流程紀律）讓格式變更與重新基準化不能脫鉤？

**這是 ADR-A6 明文指派給本 stage 的設計**，不是本站自找的題目。

失敗模式（ADR-A6 逐字稱之為「本設計最危險的單一失誤模式」）：改了 `render` 的輸出格式卻沒重新基準化 ⇒ 下一輪反向同步發現**全部**受管 item 的雜湊都對不上 ⇒ 全部誤判為人為變更 ⇒ 產生一個涵蓋所有 intent 的巨大反向 PR，且正向同步對全部 intent 進入 `suppressed`。

A. **格式指紋內嵌，錯配時自動重新基準化**：受管區塊帶一個 `fmt=<渲染範本的 sha256 前 8 碼>` 標記。反向同步比對時，若 block 的 `fmt` ≠ 當前渲染器的 `fmt`，判定為**格式變更而非人為變更** ⇒ 不進漂移清單、不開 PR，改為重新渲染並就地重新基準化。看得到的效果：指紋是**從範本推導**的，改了範本它必然改變，**忘不掉**——這是三案中唯一真正「機制而非紀律」的。代價：**它把 ADR-A6 的「單一 PR 內完成一次性遷移」改成「逐 item 惰性遷移」**，屬對已核可 ADR 的實質變更，需回上游修訂而非在本站默默採用。且遷移期間新舊格式並存。

B. **golden fixture ＋ CI 閘門**：把 `render` 的輸出釘成快照測試。改格式必然使 CI 紅燈，作者被迫在同一個 PR 內同時更新快照與執行基準化腳本。看得到的效果：貼合 ADR-A6 的「單一 PR」形狀，不改動已核可的遷移模型；用既有的測試層（`unittest`／U-9 的 fixture 集）承載，零新依賴。代價：**CI 只保證作者「注意到」，不保證他真的跑了基準化**——快照更新後 CI 就綠了。這仍是紀律，只是加了一道提醒。

C. **格式版本常數 ＋ 遷移登錄表**：渲染器有 `FORMAT_VERSION`；另有一份 `format-migrations` 登錄檔，CI 斷言「快照與當前渲染器一致」**且**「`FORMAT_VERSION` 等於登錄表最後一筆的版本」。改格式 ⇒ 快照紅燈；更新快照但沒 bump 版本 ⇒ 版本檢查紅燈；bump 了版本但沒加登錄 ⇒ 登錄檢查紅燈。看得到的效果：三道互鎖，比 B 難繞過；仍在單一 PR 內完成，不動 ADR-A6。代價：登錄表本身可以被寫成空殼（加一筆但不真的跑基準化），**天花板仍是「無法保證基準化真的執行」**；且多一份要維護的檔案。

X. Other（請說明）

[Answer]: C  <!-- 2026-08-29T11:42:38Z（讀自 date -u）· 版本常數＋遷移登錄表三道互鎖 -->

### Q2. ISO 8601 時間戳進不進 `content_hash` 的涵蓋範圍？

受管區塊必載「機制決定不寫的原因類別**與 ISO 8601 時間戳**」（[US-OQ-3] 定案）。而 `content_hash` 是防迴圈第一道（[req:FR-G4]），比對邏輯是「與上次相同 ⇒ 無人為變更」。

若時間戳進入雜湊涵蓋範圍，兩次語意完全相同的判定會產生不同雜湊；若機制在這種情況下重寫區塊，看板上每一輪都會有一次無意義的變更。

A. **時間戳進雜湊，但只在語意變化時才重寫區塊**：`render` 的輸出（含時間戳）整份進雜湊；是否重寫由**上游的漂移判定**決定（[ad:services.md] S-A 明文「有漂移才寫」），語意沒變就根本不會走到重寫。看得到的效果：`content_hash` 逐字滿足 FR-G4 的「內容雜湊」，不需為時間戳開特例；churn 由既有的漂移判定擋住，不新增機制。代價：漂移判定與區塊重寫之間形成一條**隱含依賴**——若未來有人讓區塊在無漂移時也重寫（例如加一個「定期刷新」），churn 會立刻出現而沒有任何測試會失敗。

B. **時間戳排除在雜湊之外**：雜湊只算區塊中時間戳以外的部分。看得到的效果：即使重寫，雜湊仍穩定，churn 在機制層被擋住。代價：`content_hash` 不再是「整塊內容」的雜湊，而是「內容減去一個欄位」——這**逼近** ADR-A6 已否決的「欄位級比對」形狀，需說明兩者的界線在哪，否則會被讀成繞過已核可的決定。

C. **不放時間戳，改放「上次語意變化的時間」**：即語意不變時該值也不變。看得到的效果：時間戳可以留在雜湊內且不產生 churn，兩個目標同時達成。代價：**改變了 [US-OQ-3] 已定案的欄位語意**（「決定不寫的時間」變成「上次語意變化的時間」），屬對已核可內容的變更，需回上游確認；且這個值要能算出來，等於要多存一份狀態。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T11:42:38Z（讀自 date -u）· 時間戳進雜湊，churn 由漂移判定擋 -->

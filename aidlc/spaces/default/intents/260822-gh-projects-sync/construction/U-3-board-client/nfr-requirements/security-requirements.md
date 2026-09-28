# Security Requirements — U-3 看板客戶端

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-3-board-client · kind: library -->

> **本單元是整個 intent 中唯一持有憑證、唯一呼叫外部 API 的單元。** 前面幾個單元的 IAM 判定都是「不適用」，到這裡才真正適用。

## ADR-0006 security baseline 的四面向逐項判定

| 面向 | 判定 | 內容 |
| --- | --- | --- |
| **IAM** | **完全適用** | 見 SEC-1、SEC-2、SEC-3 |
| **Encryption** | **適用（由平台承擔）** | 傳輸為 HTTPS（GitHub API），憑證由 GitHub secret 機制靜態保管。本單元**不自行儲存憑證**、不落地任何機敏檔案（NFR-S4） |
| **Network exposure** | **不適用** | 全部是**出站**呼叫至 GitHub API；不開埠、不新增端點（NFR-S5） |
| **Audit logging** | **適用** | 每次 Status 寫入須可回答「哪個 intent、哪個 stage、什麼時間」（NFR-S6）。本單元是寫入的發生點，三要素分別來自 `binding`、`Decision.field_value`、呼叫時刻；記錄落在受管區塊（U-2）與 workflow log |

## SEC-1：憑證經 `env` 傳入，不得成為 action 的 `input`

**規則**：`action.yml` **不得**宣告任何用於承載憑證的 `input`；憑證一律經 `env: GH_TOKEN` 由呼叫端 workflow 傳入。

三個理由，依強度排序：

1. **`input` 是 action 的公開介面。** 把憑證放進介面等於邀請每一個呼叫端「傳一個你手上有的 token」，而正確的做法是只有配置好的那一支 workflow 能提供它。
2. **repo 既有形狀**：多支 workflow 已以 `GH_TOKEN: ${{ secrets.* }}` 的 env 形式傳遞（實測 `.github/workflows/`）。沿用既有形狀不引入第二種心智模型。
3. `gh` CLI 原生讀 `GH_TOKEN`，走 input 再 export 只是多一跳。

> 這與 U-1／U-2 的 SEC 約束（「不得宣告任何 secret 型 input」）**方向一致但理由不同**：那兩個單元是**根本不該碰憑證**；本單元**必須**碰，但要從正確的通道拿。

## SEC-2：本單元拿到的權限**大於**它需要的

NFR-S1 定義機制所需的權限為**三項**（原宣告兩項，**ADR-0014 補入第三項**）：**組織層 Projects 讀寫** ＋ **repo 內容寫入** ＋ **Issues 寫入**（後者的用途限於 record 目錄下的綁定編號與 `sync-state.json`，以及開 PR）。

> **權限集合現為四項（ADR-0015 §8）**：ADR-0014 補入的是第三項 Issues 寫入，而 §8 進一步指出**開 PR 與推分支在 GitHub 權限模型中是兩個獨立權限**，第四項為 `Pull requests: write`（佐證：`deploy.yml:174-175` 在本 repo 上正在運行的設定即分列兩行）。本檔沿用的是 NFR-S1 當時的三項計數，更正指令與閘門（Bolt 0，須在憑證鑄造前）見 `../../../inception/decisions/0015-functional-design-upstream-amendments.md` §8。指標補於 2026-08-30T01:31:09Z。

而 NFR-S2 要求 Projects 憑證為**獨立 secret**、不重用既有憑證。

**兩者合起來的後果必須被寫下來**：本單元需要 Projects 讀寫**與 Issues 寫入**兩項，但它拿到的是完整的憑證——**repo 內容寫入的權限也在它手上**。

> **「本單元只需要 Projects 那一半」已被本 stage 自己的改動推翻（2026-08-30T01:31:09Z，reviewer iteration 4 Group B M-5）。** ADR-0015 §11 為 §C-3 增設 `write_body`（受管區塊寫進 issue body，先前全設計無寫者），該方法需要 **`Issues: write`**。本單元因此橫跨權限集合的兩項，最小權限的落差比先前記載的小，但**方向不變**：它仍拿到 repo 內容寫入這項它用不到的權限。

`business-rules.md` 的 R-5.1／R-5.2 規定本元件不得提供「推 commit 到 `ut`」或「改 record 目錄以外的檔案」的方法，**但那是介面層的約束，不是權限層的**。[ad:component-methods.md] 已明文區分：「介面不提供」與「嘗試時回 403」是兩件事。

具體後果：

- 一個違反 R-5 的實作改動**不會被權限擋下**，只會被 code review 擋下。
- [US:S-10 AC 5] 的兩個例子中，只有「直推保護分支」可由分支保護產生真的 403；「改 record 目錄以外的檔案」在本設計下**無機制可產生 403**。候選機制（Repository Rulesets 的 file-path restriction）已列 **PRE-1-a** 實測。

**若 PRE-1-a 判定不可行**：該 AC 需回 user-stories 改寫（`project.md` 的 `user-stories:c4`）。**本單元不得以「介面不提供」為由把它標為通過。**

## SEC-3：測試 Project 的隔離靠設定，不靠權限

[ad:decisions.md] ADR-A3 定案驗證對**獨立測試 Project** 進行，[ug:unit-of-work.md] 的 U-3 驗證方式亦逐字如此。

**但同一份憑證同時能寫測試 Project 與正式的 Project #16。** 隔離因此取決於 `Config` 的 Project 編號值是否正確，而不是取決於權限邊界——**一個把測試設定指到 Project #16 的錯誤，沒有任何機制會擋。**

`business-rules.md` 的 R-3.2（目標 Project 不符 `Config` → 中止，[req:FR-C2]）**擋的是相反方向**：它防止機制寫到「不是設定指定的」Project，前提是設定本身正確。它擋不住設定本身寫錯。

**承接方式（本站標出，落點不擅自指派）**：最低成本的收斂是為測試路徑鑄一份**只對測試 Project 有寫入權**的獨立憑證。這需要組織層動作，屬 `external-dependency-map.md` 的 E-1 家族，且**不在本 intent 已核可的範圍內**——本站只記載風險與其形狀，不擴大範圍。

## SEC-4：錯誤訊息可能挾帶憑證片段

`ExternalError { http_status }` 與 `Failed { http_status, message }` 會被交給 C-5 通報，而通報會開 issue——**公開可讀**（本 repo 為 public）。

`gh api graphql` 的錯誤輸出在某些情況下會回顯請求內容。**規則**：交給 C-5 的 `message` 欄位**只得包含 GraphQL `errors[].message` 與 HTTP 狀態碼**，不得包含完整的請求／回應 body、不得包含任何標頭。

這條與 `project.md ## Forbidden` 的「不得把敏感資料寫進任何 log 或決議紀錄」同向，但落點更具體：它管的是**錯誤路徑**，而錯誤路徑正是最容易在趕時間時被寫成「把整包丟出去比較好除錯」的地方。

## 與上游的對應

四面向的依據為 `requirements.md` 的 NFR-S1～S6 與 `project.md` 的 ADR-0006 落點；權限邊界與「介面不提供 ≠ 回 403」引自 [ad:component-methods.md] §C-3；403 半邊缺口與 PRE-1-a 引自 [ad:decisions.md] ADR-A2，獨立測試 Project 引自 ADR-A3；FR-C1／FR-C2／FR-A3／FR-G1 引自 `requirements.md`；[US:S-10 AC 5] 引自 `stories.md`；單元邊界與驗證方式引自 [ug:unit-of-work.md] 的 U-3，AC 歸屬引自 [ug:unit-of-work-story-map.md]；紅燈語意與通報職責引自 [ad:services.md] 與 [ad:components.md]；錯誤型別的產生點見本單元的 `business-logic-model.md`、規則見 `business-rules.md`、`ItemState` 的取得路徑見 `domain-entities.md`；憑證的 env 形狀為實測 `.github/workflows/` 的既有先例（並見 [kb:technology-stack.md]）。

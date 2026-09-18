# Team Allocation — Bolt 與執行者的對應

> Stage: delivery-planning（Inception 2.8）· Intent: 260802-last-login-column
> 上游來源：`../requirements-analysis/requirements.md`（下稱 requirements）、`../user-stories/stories.md`（下稱 stories）、`../refined-mockups/mockups.md`（下稱 mockups）、`../application-design/components.md`（下稱 components）、`../units-generation/unit-of-work.md`、`unit-of-work-dependency.md`、`unit-of-work-story-map.md`、`../practices-discovery/team-practices.md`（下稱 team-practices）。
> Bolt 定義見 `bolt-plan.md`。

## 結論先行：單人專案，無 Program Board

**`team-formation`（1.5）在本 workflow 未執行**（state 標記為 `[S]` skipped），且本專案為**單一決策者**（Danniel）。因此本檔沒有多團隊配置可做 —— stage 檔的 Program Board 類比（團隊數 > 1 時適用）在此不成立。

如實記載為單人配置，**不虛構團隊結構**。

## 配置

| Bolt | 包含單元 | 執行者 | 人工決策點 |
|---|---|---|---|
| B1 | U4 `security-reviewer-permission` | `aidlc-developer-agent`（AI）＋ 人工核可 | 部署後人工核對目標角色可進入管理頁 |
| B2 | U1 `backend-activity-policy`、U2 `user-object-serialization` | `aidlc-developer-agent`（AI）＋ 人工核可 | 部署後重啟並確認欄位存在 |
| B3 | U5 `api-type-contract`、U3 `admin-page-column` | `aidlc-developer-agent`（AI）＋ 人工核可 | 顯示端在地化策略定案；刻意漂移實測兩道 gate |

**每個 Construction stage 仍有各自的核可 gate** —— AI 執行不等於自動放行。依 `team.md` 的既有實務，每個 stage 完成後產出 summary 並等人工確認。

## 人工必須介入的三類事

依上游已記載的缺口，下列事項**不能由 AI 單方判定完成**：

| 類別 | 具體事項 | 落在哪個 Bolt |
|---|---|---|
| **無自動化驗證，須人工核對** | U4 在既有環境的權限套用結果；U1 的 C-2 交易契約與 C-3 補欄；stories AC-3.1a 的導覽入口 | B1、B2 |
| **上游未定案，須於實作時決定** | 顯示端的在地化策略（AC-1.6）；型別檔的 lint 作用域；規格檔的檔名與路徑；U5 標記機制的最終形式 | B2、B3 |
| **工具無法驗證，須人工或輔助工具** | AC-2.2 的對比度（現行工具鏈無自動化對比度檢查） | B3 |

## 未採用的配置

| 選項 | 為何不採 |
|---|---|
| 多團隊平行 | 無第二個執行者。`bolt-plan.md` Q2=A 已定案嚴格序列 |
| 依單元指派不同 agent persona | 本專案的 Construction 由 `aidlc-developer-agent` 統一執行（stage 檔在 1.5 SKIP 時的預設）；per-unit 的專長差異由各 stage 自己的 lead agent 承擔，不在本檔重複配置 |

---

## Revision 1（2026-08-11）— PU-6 使用者清單分頁

**團隊配置無變化**：單一決策者（Danniel）＋ AI agents 執行全部建造工作，approval gate 為人機協作的控制點。

**唯一值得記載的變化是負載分佈**：Bolt 邊界調整後，B2 縮小為單一單元（U1）、B3 擴大為三個單元（U2＋U5＋U3，含本 intent 唯一的 XL 單元）。在單一執行者的前提下這不影響配置，但它改變了 **approval gate 的資訊量** —— B3 的 gate 要一次審過後端契約、建置資產與前端呈現三件事。**若審查負擔過重，可在 B3 內部設中途檢查點**（非新 Bolt、不觸發部署），這是執行時的選擇，本站不預先規定。

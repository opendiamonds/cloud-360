# Phase Check — Inception → Construction

> 由 delivery-planning（Inception 2.8）Step 6 產出 · Intent: 260802-last-login-column
> 日期：2026-08-09
> 檢查對象：Inception 八個 stage 的全部產出，以及它們與 Ideation 的追溯關係。

## 判定

**PASS** —— 七項機器可核對的追溯檢查全數通過，無斷鏈、無孤兒、無幻影引用。

三項已知缺口在文件中**如實記載且已標出承載單元**，不構成阻擋（見下方「帶入 Construction 的缺口」）。

## 追溯檢查（以腳本核對，非人工目測）

| # | 檢查 | 方法 | 結果 |
|---|---|---|---|
| ① | 每條功能需求有承載單元 | 比對 `requirements.md` 的 18 條 FR 與 `unit-of-work-story-map.md` 的需求對應表 | **全部有** |
| ② | 每條非功能需求有承載單元 | 同上，7 條 NFR | **全部有** |
| ③ | 每則使用者故事有承載單元 | 4 則 US | **全部有** |
| ④ | 每條驗收標準有歸屬單元 | 25 條 AC 逐條比對 | **25／25** |
| ⑤ | 每個設計元件有歸屬單元 | `components.md` 的 8 個元件 vs `unit-of-work.md` | **全部有** |
| ⑥ | Bolt 計畫涵蓋所有單元 | 5 個單元 vs `bolt-plan.md` | **是** |
| ⑦ | 故事對應表無幻影引用 | 反向檢查：對應表中的 AC 是否都真實存在於 `stories.md` | **是**（零幻影） |

## 各層的規模

| 層 | 數量 | 產出 |
|---|---|---|
| 功能需求 | 18 條 FR | `requirements-analysis/requirements.md` |
| 非功能需求 | 7 條 NFR | 同上 |
| 約束 | 8 條 | 同上 |
| 使用者故事 | 4 則 US、25 條 AC | `user-stories/stories.md` |
| 設計元件 | 8 個（C-1〜C-8） | `application-design/components.md` |
| 架構決策 | 9 則（AD-1〜AD-9） | `application-design/decisions.md` |
| 工作單元 | 5 個（U1〜U5） | `units-generation/unit-of-work.md` |
| 依賴邊 | 4 條，無循環 | `units-generation/unit-of-work-dependency.md` |
| Bolt | 3 個 | `delivery-planning/bolt-plan.md` |

## 追溯鏈的完整形狀

```
Ideation（intent → feasibility → scope → mockups → handoff）
  ↓
requirements（18 FR / 7 NFR / 8 約束）
  ↓
stories（4 US / 25 AC）  ←→  refined-mockups（視覺與可及性規格）
  ↓
components（8 元件）＋ decisions（9 ADR）
  ↓
units（5 單元 / 4 條邊 / DAG 無循環）
  ↓
bolts（3 個，序列 B1 → B2 → B3）
```

**一條非 DAG 的橫向關係也被保留**：stories 刻意區分的驗收依賴（US-3 ..> US-1）貫穿到 `unit-of-work-dependency.md` 與 `bolt-plan.md`，成為 B1 排最前的決定性理由。

## 上游修訂的追溯完整性

Inception 期間發生**兩次回跳修訂**，兩次都依 `project.md` 的既有規則處理（原答案不動、以 Revision 段疊加、舊 artifact 歸檔、重走 gate）：

| 修訂 | 觸發來源 | 處置 | 歸檔位置 |
|---|---|---|---|
| scope-definition Revision 1 | 下游 stage 的答案觸發 scope 擴充 | 疊加修訂、重走 gate | `archive/2026-08-04-scope-definition/` |
| application-design Revision 1 | units-generation Q2=B 與 AD-5 抵觸 | 新增 AD-9（AD-5 的具名例外）與元件 C-8；AD-5 原文未改寫 | `archive/2026-08-09-application-design/` |

第二次修訂連帶使 units-generation 追加 Q1a（C-8 的歸屬），同樣以 Revision 段疊加、原答案不動。

## 帶入 Construction 的缺口（如實記載，不構成阻擋）

這些在 Inception 期間被發現、記載並標出承載單元，但**尚未關閉**：

| 缺口 | 承載 | 性質 |
|---|---|---|
| NFR-7 的桌面回歸無 AC 落點 | U3／B3 | 自 refined-mockups 起追蹤；AC-4.3 的 Given 限定小螢幕 |
| AC-3.1a 在現行 e2e 無可執行驗收路徑 | U4／B1 | 環境無該角色的測試帳號；stories 的 DoD 已記載處置選項 |
| U4 的既有環境套用無自動化驗證 | U4／B1 | 以啟動日誌三態 + 部署後人工核對承接 |
| U1 的 C-2 交易契約與 C-3 補欄無自動化驗證 | U1／B2 | 純函式測試不碰 DB、端點測試只斷言回應欄位 |
| AC-2.2 的對比度須人工驗證 | U3／B3 | 現行工具鏈無自動化對比度檢查 |
| 顯示端在地化策略未定 | U3／B3 | AC-1.6 的驗收面；上游未定，B3 必答 |
| application-design 的 11 項殘留 | 分散 U1／U4／U5 | 完整清單見 `application-design/memory.md` 的 Open questions |
| U5 的兩道 gate 為自我驗證 | U5／B3 | 需以一次刻意漂移實測 gate 確實變紅 |

**這些缺口的共同性質**：多數來自 repo 既有的測試涵蓋現況（router 層零 HTTP 測試、前端只有 6 個 e2e case、無覆蓋率量測），不是本 intent 引入的，也不是切分或設計能解決的。它們被逐一記載而非掩蓋，正是為了讓 Construction 知道哪些事情**不會有自動化的東西替你把關**。

## Constraint compliance（Inception 全期）

| 約束 | 判定 | 依據 |
|---|---|---|
| ADR-0006 security baseline 四面向 | **compliant** | requirements 有逐項判定表；AD-9 補上 C-8 的四面向判定；IAM 面向由 U4 承載、network exposure 由 U5 承載 |
| Property-based testing（hard constraint） | **compliant** | C-1 為明確落點（U1／B2）；team-practices 已記載 ADR-0006 原點名的三個模組在本 repo 不存在，現況為 N/A |
| 文件語言：繁體中文 | **compliant** | `validate_repo_contract.py` 全期通過 |
| schema／deploy 同步（blocking） | **compliant** | requirements C-4 已正確引用；B1 與 B2 的 Definition of Done 各自明列 |
| 不新增含 prod／production／secrets 的路徑 | **compliant** | contract 檢查通過 |
| production 不在範圍 | **compliant** | requirements C-8；全部落在自有 staging |

## 未進入 Construction 的事

| 事項 | 為何 |
|---|---|
| `UserSchema` 兩個端點的既有欄位漏傳缺陷 | 本 intent 明確劃在範圍外（獨立項目）；但 U2 的三構造點契約會連帶處理新欄位 |
| migration 工具的導入 | AD-3 列為獨立技術債 |
| 前端型別產生擴及其餘 51 處資料抓取 | Q5=A 定案只接一處 |
| 覆蓋率量測工具 | practices-discovery 列為待補承載機制 |

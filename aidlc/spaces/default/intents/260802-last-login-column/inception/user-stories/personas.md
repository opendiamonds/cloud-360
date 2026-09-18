# Personas — 帳號最後活動時間（稽核欄位）

<!-- Stage: user-stories（Inception 2.4，mob）· 來源標籤定義見 user-stories-questions.md 的 ## Sources。
     依 Q1=A：只為已確認利益的受益者編寫完整 persona；可見但利益未指認的角色以事實形式記載，不推定其目標。 -->

## 上游輸入

- **requirements**（`../requirements-analysis/requirements.md`）：18 條 FR 與 7 條 NFR，本檔的 persona 目標須能對應其中的受益敘述。
- **business-overview**（`aidlc/spaces/default/codekb/cloud-360/business-overview.md`）：平台定位與既有角色體系，界定 persona 在系統中的位置。
- **component-inventory**（`aidlc/spaces/default/codekb/cloud-360/component-inventory.md`）：使用者管理頁與權限判定元件的既有職責，界定 persona 實際接觸的介面。
- **team-practices**（`../practices-discovery/team-practices.md`）：本輪生效的測試底線，影響 persona 相關驗收的表述方式。

## 已確認利益的 Persona

### P-1 `Security_Reviewer` — 稽核查驗者（主要 persona）

| 面向 | 內容 |
| --- | --- |
| **角色** | 執行存取稽核的安全審查者；本 intent 為其開通使用者管理介面的檢視權限（FR-4） |
| **目標** | 1. 判定每個帳號「是否仍在使用」，形成可辯護的稽核結論<br>2. 取得**可抄錄、可比對**的證據，而非印象或口頭確認<br>3. 一次掃完整份帳號清單，不必逐一詢問各帳號的持有者 |
| **痛點** | 1. 系統今日**完全沒有**任何活動紀錄，稽核問題無法從系統回答（requirements C-1）<br>2. 在本 intent 之前，此角色連使用者管理頁都進不去 —— 即使資料存在也無法自行取用 |
| **技術熟悉度** | 高 —— 熟悉權限模型與稽核流程，但不需要理解系統內部實作 |
| **使用頻率** | 低頻、批次 —— 依稽核週期（季度）進行，一次掃視全表 |
| **使用節奏** | **批次掃讀**：進入頁面 → 由上而下掃視整欄 → 對逾期者抄錄絕對時間值 → 形成結論 |
| **來源** | [intent] `intent-statement` 的受益者表；[flow] Flow 1 |

### P-2 `Platform_Admin` — 平台管理者（次要 persona）

| 面向 | 內容 |
| --- | --- |
| **角色** | 日常的帳號管理者；本 intent 之前即擁有使用者管理介面的完整權限 |
| **目標** | 1. 在處理特定帳號時，**順帶**知道該帳號是否還活躍<br>2. 管理決策（是否停用、是否調整角色）所需的資訊不必離開當前頁面 |
| **痛點** | 1. 決定是否停用一個帳號時，缺乏「這個人還在用嗎」的客觀依據<br>2. 若要查證，目前沒有任何可查的地方 |
| **技術熟悉度** | 高 —— 平台的日常操作者 |
| **使用頻率** | 中高頻、單點 —— 因應個別帳號的管理需求而進入 |
| **使用節奏** | **單點查看**：因某個特定帳號的事由進入頁面 → 在該列視野內同時看到角色、狀態與活躍度 → 直接處置 |
| **來源** | [intent] `intent-statement` 的受益者表；[flow] Flow 2 |

## 兩個 Persona 的關鍵差異

這兩者使用**同一個欄位、同一個畫面**，但使用方式截然不同 —— 這是本 intent 設計取捨的主要張力來源：

| 面向 | P-1 `Security_Reviewer` | P-2 `Platform_Admin` |
| --- | --- | --- |
| 進入頁面的理由 | 為了稽核**整份清單** | 為了處理**某一個帳號** |
| 對欄位的使用 | 掃視全欄找出異常 | 讀取單列的一格 |
| 對絕對時間格式的需求 | **高** —— 需抄錄進稽核紀錄（FR-2.2 的主要驅動） | 低 —— 只需知道「久不久」 |
| 對逾期標示的需求 | **高** —— 即讀辨識，免逐筆計算（FR-3.1 的主要驅動） | 中 —— 輔助判斷 |
| 對小螢幕的需求 | 中 —— 稽核多在桌面進行 | 中 —— 可能臨時處理 |

**優先序**：`Security_Reviewer` 為**主要 persona** —— 本 intent 的立項理由是存取稽核需求（intent-statement 的問題陳述），且絕對時間格式與逾期標示兩項設計決策皆以其需求為主要驅動。`Platform_Admin` 為次要 persona，其價值為既有工作流程的增益而非新能力的解鎖。

## 可見但利益未指認的角色

`Project_Admin` 與 `Platform_Owner` **具備使用者管理介面的可見性**，因此本 intent 上線後這兩個角色也會看到新欄位與逾期標示（FR-4.2：四個管理類角色皆可見，不做欄位級控制）。

但依 `stakeholder-map` 的已確認狀態，**這兩個角色在本工作中的利益未被指認**：intent-capture 的受益者題（Q5）只涵蓋 `Platform_Admin`，Q11／Q12 確認的是「可見性放寬」而非「利益確認」。

因此本檔**不為這兩個角色編寫目標與痛點** —— 那會是發明的內容，違反 inception 護欄「不得引入無來源需求」，也違反 stakeholder-map「不推定其利益內容」的明確要求。

| 角色 | 已確認的事實 | 未確認的事項 |
| --- | --- | --- |
| `Project_Admin` | 可見使用者管理介面，將看到新欄位 | 其對本欄位的使用目的與價值 |
| `Platform_Owner` | 可見使用者管理介面，將看到新欄位 | 同上 |

若未來需要為這兩個角色設計差異化體驗，須先回到 intent 層確認其利益，不在本階段推定。

## Assumptions & Open Questions

- [assumption] `Security_Reviewer` 的稽核節奏為季度，此推斷源自 requirements 對 90 天門檻的定案理由（對應季度稽核節奏），未經該角色的實際使用者獨立確認
- [assumption] `Security_Reviewer` 的稽核操作僅為「讀取＋人工抄錄」，系統不提供匯出（承 user-flow 的既有 assumption；匯出在 scope 為「未承諾」狀態）
- [assumption] （開放問題）`Project_Admin` 與 `Platform_Owner` 看到本欄位後是否會產生新的使用需求，本階段不推定；若日後浮現，須回到 intent 層確認

# User Flow — 帳號最後活動時間（稽核欄位）

<!-- Stage: rough-mockups（Ideation 1.6）· 來源標籤定義見 rough-mockups-questions.md 的 ## Sources。 -->

## 上游輸入

- **intent-statement**（`../intent-capture/intent-statement.md`）：兩類受益者的目的 — `Security_Reviewer` 取得稽核證據、`Platform_Admin` 免另行查詢。
- **scope-document**（`../scope-definition/scope-document.md`，Revision 1）：價值流終點為存取稽核判定。
- **intent-backlog**（`../scope-definition/intent-backlog.md`）：PU-2／PU-3／PU-4 的使用者面。

## 核心流程圖

三條 Flow 的關鍵節點與匯流關係（依 stage-protocol.md 的 ASCII 方向箭頭標準）：

```
[登入平台] -----> [進入使用者管理頁]
                        |
          +-------------+-------------+
          |                           |
          v                           v
[桌面: 掃讀表格新欄]        [小螢幕: 逐卡片掃讀]
          |                           |
          +-------------+-------------+
                        |
                        v
        [判讀: 正常 / (!) 逾期 / — 無紀錄]
                        |
          +-------------+-------------+
          |                           |
          v                           v
[稽核: 抄錄絕對時間值]      [管理: 沿用既有操作處置]
          |                           |
          v                           v
[稽核結論: 帳號是否仍在使用]  [帳號治理決策 (如停用)]
```

<!-- Text fallback: 使用者登入後進入使用者管理頁，依裝置以表格或卡片掃讀最後活動時間欄，判讀正常／逾期／無紀錄三種狀態；Security_Reviewer 路徑抄錄絕對時間值形成稽核結論，Platform_Admin 路徑沿用既有操作進行帳號治理處置。錯誤路徑（清單載入失敗）沿用既有頁面錯誤呈現後重試，見各 Flow 的 Error paths。 -->

## Flow 1 — Security_Reviewer 稽核查驗（主流程）

- **Persona**：`Security_Reviewer`（檢視權限由 PU-4 開通）
- **Trigger**：執行存取稽核，需查驗帳號是否仍在使用
- **Steps**：
  1. 登入平台 → 側邊導覽出現「使用者管理」入口（權限開通後可見）→ 進入頁面
  2. 使用者清單載入 → 掃讀「最後活動時間」欄
  3. 逾期帳號由 `(!)` 標示即讀辨識 → 抄錄絕對時間值作為稽核證據
  4. 無紀錄（`—`）帳號 → 聚焦／hover 讀取說明（上線前無資料）→ 依稽核規則另行判定
- **Success outcome**：完成全帳號活躍度查驗，證據（絕對時間值）可直接抄錄
- **Error paths**：
  - 清單載入失敗 → 既有頁面錯誤呈現 → 重試
  - 權限未開通（PU-4 未上線）→ 導覽無入口 → 依 scope 此為未完成態，非錯誤

## Flow 2 — Platform_Admin 日常帳號管理（次流程）

- **Persona**：`Platform_Admin`
- **Trigger**：日常帳號管理（角色調整、啟停用）時順帶關注活躍度
- **Steps**：
  1. 進入「使用者管理」（既有動線，無變更）
  2. 在同一列視野內看到最後活動時間與逾期標示 → 無需離開頁面即可判斷帳號狀態
  3. 對逾期帳號採取既有操作（如停用）— 本 feature 不新增操作，僅提供資訊
- **Success outcome**：管理決策所需的活躍度資訊零額外查詢成本
- **Error paths**：同 Flow 1 的載入失敗路徑

## Flow 3 — 小螢幕存取（PU-5）

- **Persona**：同 Flow 1／2
- **Trigger**：以行動裝置開啟使用者管理頁
- **Steps**：
  1. 頁面依斷點切換為卡片式佈局
  2. 逐卡片掃讀「最後活動」列 — 標示語彙與桌面一致
  3. 既有操作於卡片首行完成
- **Success outcome**：小螢幕上可完成與桌面等值的查驗與管理
- **Error paths**：同 Flow 1

## 資訊架構備註

- 本 feature 不新增頁面與導覽節點；唯一的 IA 變化是 `Security_Reviewer` 的導覽多出既有「使用者管理」入口（權限開通的副作用）[intent-statement]。
- 欄位資訊層級：身分（使用者）→ 狀態（授權、角色）→ **活動（新欄）** → 操作 — 對應 [Q1] 的欄位位置決定。

## Assumptions & Open Questions

- [assumption] `Security_Reviewer` 的稽核操作僅為「讀取＋人工抄錄」；系統不提供匯出（scope-document 列為未承諾）
- [assumption] （開放問題）逾期帳號的後續處置（停用等）沿用既有操作，本 feature 不設計新流程；若稽核實務需要批次處置，屬未來另立 intent

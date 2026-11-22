# User Personas — A1 混合雲繪圖功能 (Compound Cloud Diagram)

> Stage: user-stories (2.4) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [requirements](../requirements-analysis/requirements.md)
> - [business-overview](../../../codekb/cloud-360/business-overview.md)
> - [component-inventory](../../../codekb/cloud-360/component-inventory.md)
> - [team-practices](../practices-discovery/team-practices.md)

---

## 1. 角色概述與優先級矩陣 (Persona Overview & Priority Matrix)

為使 A1 混合雲繪圖功能之各項故事能緊扣終端業務場景與人機交互體驗，本專案建立三位具代表性之關鍵角色：

| Persona ID | 角色名稱與職稱 | 角色定位 | 優先級 (Ranking) | 核心關注維度 |
| :--- | :--- | :--- | :--- | :--- |
| **P1** | **Alex — 企業雲端架構師 (Enterprise Cloud Architect)** | Primary (主要決策者與產出審核者) | Rank 1 (Highest) | 跨雲拓撲幾何規範、三雲隔離邊界、跨雲專線協議標籤 |
| **P2** | **Brenda — 售前解決方案顧問 (Presales Solution Consultant)** | Primary (前線高頻使用者與展示者) | Rank 2 | Toolbar 一鍵切換、對話意圖自動辨識、最佳縮放視角 |
| **P3** | **Charlie — 平台 SRE 與維運工程師 (Platform SRE / DevOps)** | Secondary (系統可用性與治理維護者) | Rank 3 | n8n 逾時降級容錯、零系統崩潰、相容性與無障礙標準 |

---

## 2. 核心角色詳細定義 (Detailed Persona Profiles)

### Persona 1: Alex — 企業雲端架構師 (Enterprise Cloud Architect)
- **個人背景**: 擁有 10 年以上大規模雲端架構規劃經驗，負責金控與跨國企業之核心系統現代化與多雲策略佈局。
- **工作場景與脈絡 (Context)**: 主持架構評審會議 (Architecture Review Board)，必須向技術主管與資安長說明跨雲業務核心（如 AWS 運算與資料分析）如何安全串接週邊雲服務（如 Azure Active Directory 身分驗證、GCP BigQuery 外部數據倉庫）。
- **核心目標 (Goals)**:
  1. 能在單一張 Draw.io 畫布上完整呈現 AWS、Azure、GCP 三個公有雲之服務節點與巢狀容器。
  2. 雲與雲之間邊界清晰，具備 Hub-and-Spoke 隔離空間，避免群組重疊與混亂。
  3. 跨雲連線採直角折線，且清楚標註連線協議（如 "Direct Connect", "VPN Tunnel", "HTTPS API"）。
- **痛點 (Pain Points)**:
  1. 過去 A1 只能單一雲繪圖，若要呈現混合雲需繪製三張圖後手動拼貼，耗時且失真。
  2. 傳統繪圖工具連線常穿透節點或群組，導致架構圖難以通過合規與資安審核。
- **成功指標**: 能直接匯出符合合規規範的 Draw.io XML，節省 80% 的跨雲架構圖整理時間。

### Persona 2: Brenda — 售前解決方案顧問 (Presales Solution Consultant)
- **個人背景**: 專注於雲端解決方案評估與客戶 POC 提案，經常需要在會議中即時展示架構雛形。
- **工作場景與脈絡 (Context)**: 在客戶會議室或線上提案時，一邊與客戶溝通多雲業務需求，一邊透過 A1 平台快速生成概念驗證拓撲圖。
- **核心目標 (Goals)**:
  1. 透過畫布 Toolbar 直接點擊切換為「混合雲 (Compound)」模式，所見即所得。
  2. 透過 ChatBox 對話自然語言輸入「畫一個跨 AWS 與 GCP 的金融架構」，AI 智能判斷多雲意圖並自動調用混合雲繪圖。
  3. 繪圖完成後，畫布能自動全景最適縮放 (Fit-to-Window)，無需手動拖拉即可向客戶完整展示。
- **痛點 (Pain Points)**:
  1. 現場若需複雜手動設定才能切換多雲，會打斷對話節奏，降低客戶信心。
  2. 混合雲架構畫布過大時，若沒有自動縮放，客戶第一眼只看到單一角落，失去視覺震撼感。
- **成功指標**: 會議中於 10 秒內一鍵或一句話呈現完整三雲提案架構圖。

### Persona 3: Charlie — 平台 SRE 與維運工程師 (Platform SRE / DevOps)
- **個人背景**: 負責 A1 系統之 SLA、生產環境穩定度及外部服務通訊治理。
- **工作場景與脈絡 (Context)**: 監控 A1 後端各項微服務與對外 HTTP 請求狀態，確保高並發與外部依賴異常時系統依然具備高彈性與高可用。
- **核心目標 (Goals)**:
  1. 向外部 n8n 圖示服務發送請求時，上行 payload 必須嚴格統一為 `{"service": name, "provider": "compound"}`。
  2. 設有嚴格 5.0 秒逾時中斷機制，若 n8n 服務當機或逾時，必須提供灰底向量 SVG Fallback，產圖流程絕不中斷或報錯。
  3. 符合既有 RBAC 權限管制（`A1.edit` 可產圖，`A1.view` 僅可檢視），且不引入任何新增的外部 Python / npm 依賴。
- **痛點 (Pain Points)**:
  1. 外部第三方 Webhook 不穩定導致使用者端直接噴出 500 錯誤與客訴。
  2. 跨雲架構圖產圖若耗時過長（超過 10 秒）會占用後端 worker 執行緒，引發系統抖動。
- **成功指標**: n8n 故障演練時圖表生成成功率 100%，混合雲總體組裝耗時不超過 8.0 秒。

---

## 3. 角色關係與使用者旅程對齊 (Persona Relationships & User Journey)

```
[客戶多雲需求] 
       │
       ▼
 [Brenda: 售前顧問] ──(Toolbar / Chat 觸發混合雲)──► [A1 繪圖引擎]
                                                             │
 [Alex: 企業架構師] ◄──(檢視直角折線、三雲邊界與協議)─────────┤
                                                             │
 [Charlie: SRE 維運] ◄──(保障 5.0s 逾時、灰底 SVG Fallback)───┘
```

- **協同關係**: Brenda 觸發初步多雲圖形後，交由 Alex 進行進階節點拓撲細化與合規審核；Charlie 則在背景全程守護通訊契約與系統彈性。
- **驗收一致性**: 所有產出之 User Stories 與驗收標準 (AC) 均直接追溯至上述三位 Persona 之核心痛點與驗收條件。

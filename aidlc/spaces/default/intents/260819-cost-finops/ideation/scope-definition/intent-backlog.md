# Intent Backlog — 成本估算與 FinOps（C1 第一輪）

<!-- Stage: scope-definition（Ideation 1.4）· 來源標籤定義見 scope-definition-questions.md 的 ## Sources。
     Proto-Units 為 inception units-generation 的前身：以能力為單位，不預作技術切分。 -->

## 上游輸入

- 能力集與邊界承襲本階段 `scope-document.md`，其上游為 **intent-statement**、**feasibility-assessment** 與 **constraint-register**。
- market-research 已依 scope 跳過，無市場面輸入。

## Proto-Units（依 Risk-first 交付順位排列 [Q2]）

### PU-1 公開價目覆蓋查證 — Must（第一段）

- **價值**：把「哪些雲打官方 API、哪些走 Override」變成可驗證的清單，避免先做完畫面才發現幾乎沒有官方價 [feas:R1]
- **內容**：查證各雲公開免帳號官方價目是否可用；輸出本輪官方價 vs Override 的雲別。三雲皆無則整輪仍繼續，全部 Override [Q4]
- **依賴**：無（風險鏈頭）
- **DoD 要點**：雲別清單可被後續 PU 引用；不引入 staging 憑證、不讀客戶帳單（Won't Have）[Q3]
- **順位理由**：Risk-first [Q2]

### PU-2 從架構圖擷取可估價資源 — Must（第一段）

- **價值**：報價對到圖上元件，而不是另一份表 [intent:Q1]
- **內容**：列出圖上資源；對不到價目的列名、不計入總額、顯示 N 項尚未定價 [feas:Q7]
- **依賴**：無資料依賴於 PU-1；排序在 PU-1 之後以免對錯雲
- **DoD 要點**：未定價列可見且不計入總額

### PU-3 單價（官方或 Manual Override）— Must（第一段）

- **價值**：可重算的數字來源 [intent:Q3]
- **內容**：公開免帳號價目覆蓋得到的雲打官方 API；其餘與 API 失敗走 Manual Override 並標記 [feas:Q2] [intent:Q15]
- **依賴**：PU-1（知道走哪條價路徑）、PU-2（有列可定價）
- **DoD 要點**：來源時間可見；覆寫有稽核紀錄（constraint-register audit logging）；僅 FinOps 能覆寫單價 [feas:Q5]

### PU-4 TCO 畫面 — Must（第一段）

- **價值**：架構師產圖後能對外說明拆解與總額 [intent:Q2]
- **內容**：總額、圓餅、每日時數覆寫；不含 egress 列 [feas:Q3]
- **依賴**：PU-3
- **DoD 要點**：時數覆寫立即重算月費；架構師可改時數 [feas:Q5]

### PU-5 入口（Sidebar C 與產圖後 CTA）— Must（第一段）

- **價值**：找得到、產圖後接得上 [intent:Q13]
- **內容**：Sidebar 大類 C；產圖成功後 CTA「查看預估成本」
- **依賴**：與 PU-4 無硬技術前置，但 CTA 指向的畫面應已存在；排序與 PU-4 同段
- **DoD 要點**：有 C1 檢視權的角色看得到入口

### PU-6 每圖預算與超支警告 — Must（第二段）

- **價值**：預算影響可見、超支雙方都看得到 [intent:Q10] [intent:Q16]
- **內容**：每張架構圖一個月上限；超支時成本畫面視覺標示；超支期間每次進入產品都看到橫幅；無 inbox [feas:Q4] [feas:Q6]
- **依賴**：PU-4（要有可比較的總額）
- **DoD 要點**：FinOps 與工程主管可設預算；收件人為 FinOps、工程主管、雲端架構師 [feas:Q5] [intent:Q11]
- **順位理由**：第二段；被插隊時第一段可在沒有本 PU 的情況下上線 [Q1]

### PU-7 測試底線與部署資產同步 — Must（橫切）

- **價值**：沒有它，其餘 PU 在本 repo 的 CI 與部署契約下不能標示完成 [Q5]
- **內容**：cost calculator property-based testing；新 HTTP 端點 `TestClient`；權限種子 allow/deny；schema／seed 時同步 `schema_rbac.sql` 與 `DEPLOY.md` [memory:M1] [memory:M7]
- **依賴**：隨各 PU 的實際變更觸發，不排在鏈尾才開始
- **DoD 要點**：第一段上線時，PU-1～5 觸發到的測試與部署資產已完成；第二段上線時補齊 PU-6
- **順位理由**：獨立 Must 項以便集中追蹤 [Q5]，不是塞進各 PU 的隱性 DoD

## 排序與依賴總覽

```
PU-1 --> PU-2 --> PU-3 --> PU-4 --> PU-6
                         \-> PU-5
PU-7 橫切於各段上線前
```

<!-- Text fallback: PU-1 公開價目查證為鏈頭；其後擷取、單價、TCO 畫面線性推進，入口與畫面同段；預算與超支為第二段、依賴 TCO 畫面；測試與部署資產橫切，在各段上線前必須完成已觸發的部分。 -->

第一段可單獨上線的集合：PU-1～5 加上該段的 PU-7 [Q1]。第二段：PU-6 加上其 PU-7。不設 Should／Could。Unit 切分與 Bolt 經濟排序交由 units-generation 與 delivery-planning。

## Assumptions & Open Questions

- [assumption] 第一段單獨上線時仍須完成該段的 PU-7，不是「沒測也可以先上」[Q1] [Q5]
- [assumption] PU 粒度不是最終 Unit 切分，由 units-generation 檢驗
- [assumption] PU-3／PU-6 的權限切法留設計階段 [feas:Q5]
- [assumption] PU-6 橫幅的具體頁面留設計 [feas:Q6]

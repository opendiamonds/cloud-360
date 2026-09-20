# RAID Log — 成本估算與 FinOps（C1 第一輪）

<!-- Stage: feasibility（Ideation 1.3）· 來源標籤定義見 feasibility-questions.md 的 ## Sources。
     Likelihood／Impact 採 Low／Medium／High 三級；處置採 mitigate／avoid／accept／transfer。 -->

## 上游輸入

- 風險脈絡承襲 intent-capture 的 **intent-statement**（`../intent-capture/intent-statement.md`）：官方報價 API、不得使用 production credentials、本輪只做 C1、Manual Override、預算與超支警告皆為已決項。
- market-research 已依 scope 跳過，其可選產出 **competitive-analysis**、**market-trends**、**build-vs-buy** 不存在（scope 設計使然），無市場面風險輸入。

## Risks（風險）

| # | 風險 | Likelihood | Impact | 處置 | 說明 | Source |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | 公開免帳號官方價目無法覆蓋意圖中的雲，導致多數列靠 Manual Override，數字又變回「口頭估」 | Medium | High | mitigate（設計階段） | 設計階段必須查證各雲公開價目能否免帳號讀取，並列出本輪官方價 vs Override 的雲別；不在 ideation 預判 | [Q1] [Q1a] [Q2] [intent:Q1] |
| R2 | 既有 view／edit／review 無法表達「改時數／設預算／覆寫單價」三種變更，導致授權過寬或過窄 | Medium | High | mitigate（設計階段） | 產品語意已鎖 [Q5]；切法（欄位級約束或新動作）是設計必答，本階段不預選手段 | [Q5] [memory:M6] [memory:M8] |
| R3 | 未對應項很多時，總額看起來完整但其實排除了 N 項，使用者仍覺得報價不可信 | Medium | Medium | mitigate | [Q7] 要求列名並顯示「N 項尚未定價」，避免靜默省略；對應規則的品質留設計／實作 | [Q7] [intent:Q1] [code:C1] |
| R4 | 從 staging 呼叫公開官方價目端點遭遇節流、中斷或過期價 | Medium | Medium | mitigate（設計階段） | 失敗走 Manual Override [intent:Q15]；新鮮度以來源時間戳揭露 [stories:C1]；快取／重試不在本階段選定 | [Q2] [intent:Q15] [stories:C1] |
| R5 | 超支橫幅每次進入都出現，造成疲勞而習慣性忽略 | Medium | Low | accept | [Q6] 明確拒絕「關閉後不再出現」；疲勞是該選擇的後果，本輪不做 inbox 升級 | [Q6] [intent:Q16] |
| R6 | 競爭優先事項插隊，C1 半成品留在 staging | High | Medium | accept＋monitor | [Q8] 已確認可被插隊；小步前進與 stage gate 維持，不為趕工拿掉 PBT／TestClient 底線 | [Q8] [memory:M1] [memory:M5] |
| R7 | 單價覆寫或預算變更沒有稽核紀錄，違反 security baseline | Low | High | avoid | 稽核紀錄列為必做約束，不是可選 | [memory:M8] [intent:Q15] [Q4] |
| R8 | 誤把公開 list price 對外說成雲端帳單或優化後折扣 | Medium | Medium | mitigate | 畫面必須呈現定價假設與來源時間；C2 本輪不做 | [stories:C1] [intent:Q9] |

## Assumptions（假設）

| # | 假設 | 驗證時點 | Source |
| --- | --- | --- | --- |
| A1 | 不要求三雲都打得到官方 API；公開價目覆蓋不到的雲走 Manual Override 仍算 C1 交付 | 設計階段查證各雲公開價目 | [Q1a] [Q2] |
| A2 | 內部平台估價資料無外部法規框架適用（未經法務獨立確認） | 若適用情境改變時重驗 | 合規掃描；日記省略 PCI／HIPAA 專題 |
| A3 | 「進入產品」= 已登入後進入受保護畫面；具體頁面留設計 | requirements-analysis／設計 | [Q6] |
| A4 | C1 故事 AC 的 egress 本輪不交付是驗收切片，不是刪除 baseline 故事 | 本 intent 的 user-stories 階段寫明承繼／延期 | [Q3] [intent:Q9] [stories:C1] |
| A5 | 設計階段能在不擴大產品語意的前提下表達 [Q5] 三種變更 | 設計階段 | [Q5] |

## Issues（議題）

| # | 議題 | 狀態 | Source |
| --- | --- | --- | --- |
| I1 | C1 故事驗收列出 egress，本輪 TCO 不含 | 已解（本輪切片：egress 列留給 C3；不回改 baseline `stories.md`） | [Q3] [intent:Q9] [stories:C1] |
| I2 | Q1「三雲都要能報價」與 Q2「必須帶金鑰就不查官方價」字面衝突 | 已解（Q1a：畫面可用 ≠ 三雲都打官方 API） | [Q1] [Q2] [Q1a] |
| I3 | 主要使用者是架構師，但種子權限下架構師不能改 C1 | 已解產品語意（架構師可改時數）；權限切法未解，見 R2 | [intent:Q2] [code:C4] [Q5] |

## Dependencies（依賴）

| # | 依賴 | 方向 | Source |
| --- | --- | --- | --- |
| D1 | 設計階段查證各雲公開、免帳號官方價目是否存在，並列出官方價 vs Override 的雲別 | 本功能 → 設計 | [Q1a] [Q2] [R1] |
| D2 | 設計階段定案三種變更如何對應權限模型 | 本功能 → 設計 | [Q5] [R2] |
| D3 | Construction 必須交付帶 property-based testing 的 cost calculator | 本功能 → build-and-test | [memory:M1] [code:C9] |
| D4 | 新 HTTP 端點的 `TestClient` 測試；若改種子則 allow/deny；成本畫面資料形狀的 e2e | 本功能 → 測試底線 | [memory:M5] [memory:M6] |
| D5 | 若新增資料結構或改權限種子，同步 `schema_rbac.sql` 與 `DEPLOY.md` | 本功能 → 部署資產 | [memory:M7] |
| D6 | 產圖後 CTA 依賴 A 柱已能產出架構圖 | 本功能 ← A 柱 | [intent:Q13] [intent:Q4] |
| D7 | 本輪不做 C2／C3／核准流；那些能力不構成本輪完成條件 | 本功能 ✕ 後續 intent | [intent:Q9] [intent:Q14] |

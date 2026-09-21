# Constraint Register — 成本估算與 FinOps（C1 第一輪）

<!-- Stage: feasibility（Ideation 1.3）· 來源標籤定義見 feasibility-questions.md 的 ## Sources。 -->

## 上游輸入

- 約束的業務脈絡承襲 intent-capture 的 **intent-statement**（`../intent-capture/intent-statement.md`），其「適用的既有約束」段為本登錄的起點。
- market-research 已依 scope 跳過，其可選產出 **competitive-analysis**、**market-trends**、**build-vs-buy** 不存在（scope 設計使然），本登錄無市場面約束來源。

## 技術約束

| # | 約束 | 影響 | Source |
| --- | --- | --- | --- |
| T1 | 查報價必須走雲端官方報價，且不得使用 production credentials、不得把憑證字串寫進 repo | 存取策略只能是公開免帳號官方價目端點；必須帶金鑰的雲本輪不查官方價 | [intent:Q12] [Q2] [memory:M2] [memory:M3] |
| T2 | 架構圖擷取沒有 SKU／機型／區域，只有標籤與樣式 | 官方價對應必然不完整；未對應項必須列名且不計入總額 | [code:C1] [Q7] |
| T3 | 圖沒有持久雲別；雲別靠關鍵字辨識 | 跟圖走；辨識失敗走 Manual Override，不另選預設雲 | [code:C2] [code:C3] [Q1] |
| T4 | 沒有 cost calculator 或官方報價客戶端 | 本輪要新建該能力；測試必須含 property-based testing | [code:C9] [memory:M1] |
| T5 | 沒有站內通知原語 | 本輪只做超支期間每次進入產品的橫幅，不做 inbox | [code:C8] [Q6] |
| T6 | 側欄與路由沒有成本入口 | 必須新增 C 柱與產圖後 CTA 才能滿足已決入口 | [code:C6] [code:C7] [intent:Q13] |
| T7 | 今日只有 FinOps 能改 C1；架構師與工程主管只能看 | 產品語意 [Q5] 與種子現況不一致，屬必改約束，切法留設計 | [code:C4] [code:C5] [Q5] |
| T8 | 既有權限動作只有 view／edit／review | 時數、預算、單價覆寫是三種變更；不得在 ideation 預選切法 | [Q5] |
| T9 | 本輪 TCO 不含 egress／資料傳輸列 | 不得把 C3 路徑分析做進本輪，也不得靜默假裝 C1 AC 的 egress 已滿足 | [Q3] [intent:Q9] [stories:C1] |
| T10 | 每月預算上限以架構圖為單位 | 超支判定與警告綁單圖，不是專案或單次快照 | [Q4] |

## 組織與流程約束

| # | 約束 | 影響 | Source |
| --- | --- | --- | --- |
| O1 | 資料庫結構或 seed 行為變更時，`schema_rbac.sql` 與 `DEPLOY.md` 必須同步更新（blocking） | 新預算／估價／通知資料或權限種子變更未同步則不得標示相關 Construction／部署完成 | [memory:M7] |
| O2 | 新增或修改 HTTP 端點需 `TestClient` 測試；授權矩陣變更需 allow/deny 雙向測試；前端資料形狀變更需 e2e 斷言 | 估價端點、權限調整、成本畫面皆有對應的測試底線 | [memory:M5] [memory:M6] |
| O3 | cost calculator 為 property-based testing hard constraint | 測試不得只有 example-based | [memory:M1] |
| O4 | 合併進 `ut` 即部署至自有 staging | 官方價目的對外連線與憑證禁令在 staging 即生效，沒有「先在 production 再處理」的緩衝 | [memory:M2] |
| O5 | 有競爭優先事項，本功能可被插隊 | 無外部時間盒，但交付日期不可視為承諾 | [Q8] |
| O6 | 本輪不實作 FinOps 核准流 | 「數字怎麼算」的否決權已定義、不在本輪建造 | [intent:Q14] |

## 法規與政策約束

security baseline 四面向逐項判定（不得留空）[memory:M8]：

| 面向 | 判定 | 處置 | Source |
| --- | --- | --- | --- |
| IAM | **適用** | [Q5] 改變誰能改時數、預算、單價；必須維持「架構師不能覆寫單價、非 FinOps／工程主管不能設預算」的產品語意；種子變更需 allow/deny 測試 | [Q5] [memory:M6] |
| encryption | **不適用** | 本輪資料為公開價目與內部估價數字，沿用既有儲存加密；不新增需獨立密鑰的資料類別 | [Q2] [memory:M2] |
| network exposure | **適用（出站）** | 從自有 staging 呼叫公開官方價目端點；不得為了查價而開對雲端 production 的憑證或管理面 | [Q2] [intent:Q12] [memory:M2] |
| audit logging | **適用** | 單價 Manual Override 與預算變更必須留下誰、何時、改了什麼的紀錄；超支橫幅本身不是稽核證據 | [intent:Q15] [Q4] [memory:M8] |

| # | 約束 | 影響 | Source |
| --- | --- | --- | --- |
| R1 | 雲端供應商 production、production credentials 不在範圍內 | 估價不得讀客戶帳單或 Cost Explorer | [memory:M2] [intent:Q12] |
| R2 | 不得 commit 三雲 credential 字串 | 即使日後改採 staging 價目憑證（本輪未選），也不得進 git | [memory:M3] |
| R3 | 無外部法規框架被指認為適用 | 屬假設，見 A2 | （本 stage 省略 PCI／HIPAA 專題；日記記載理由） |
| R4 | 官方數字是公開 list price，不是發票 | 對外說明時不得宣稱「這是雲端帳單」 | AWS 平台視角；[stories:C1] 要求標示定價假設與來源時間 |

## Assumptions & Open Questions

- [assumption] 內部平台，無外部法規框架適用於估價資料；未經法務或合規方獨立確認
- [assumption] 公開免帳號官方價目至少覆蓋部分雲，其餘雲 Manual Override 仍可交付 C1 畫面 [Q1a] [Q2]
- [assumption] （開放問題）view／edit／review 三旗能否承載 [Q5] 三種變更，留待設計階段
- [assumption] （開放問題）超支橫幅出現在登入後的哪些受保護頁，留待設計；本階段只鎖定「超支期間每次進入都看到」[Q6]

# Feasibility Assessment — 成本估算與 FinOps（C1 第一輪）

<!-- Stage: feasibility（Ideation 1.3）· 來源標籤定義見 feasibility-questions.md 的 ## Sources。
     [Q<n>] 指本 stage 問題檔的已選答案；[intent:*] 指 intent-capture 產出；[code:C*] 指問題檔 Sources 登錄的查證事實；[memory:M*] 指 memory 層規則；[stories:C1] 指 baseline 故事柱 C1 驗收。 -->

## 上游輸入

- 本評估的必要上游為 intent-capture 的 **intent-statement**（`../intent-capture/intent-statement.md`）：問題陳述（報價不可信、無法對到架構圖資源）、成功指標與已確認的 C1 產品邊界皆承襲自該文件。
- market-research 已依 scope 跳過，其可選產出 **competitive-analysis**、**market-trends**、**build-vs-buy** 不存在；本評估不依賴市場面輸入，此缺席屬 scope 設計而非缺漏。

## 評估結論

**可行（conditional GO）**。C1 第一輪可在現有產品上落地，無外部法規或雲端 production 阻擋 [intent:Q12] [memory:M2]，但可行性建立在下列已確認前提上：

1. **官方價目存取策略已定錨**：只用公開、免帳號的官方價目端點；某雲若讀目錄必須帶金鑰或計費專案，該雲本輪不查官方價，改走 Manual Override [Q2] [intent:Q15]。
2. **「三雲都要能報價」= 成本畫面可用，不是三雲都打官方 API**：架構圖被辨識為哪一雲就走那一雲的價目路徑；官方 API 僅限公開免帳號價目覆蓋得到的雲 [Q1] [Q1a]。
3. **本輪 TCO 不含 egress／資料傳輸列**；C1 故事驗收裡的 egress 留給 C3 [Q3] [intent:Q9] [stories:C1]。
4. **每月預算上限掛在每張架構圖**；超支警告綁該圖的估價 [Q4] [intent:Q10]。
5. **誰能改什麼已定產品語意**：雲端架構師可改每日時數；FinOps 分析師與工程主管可設預算；只有 FinOps 能做單價 Manual Override [Q5] [intent:Q2] [intent:Q15]。權限模型怎麼切是設計階段必答題，見 raid-log R2。
6. **超支站內通知**為：只要該圖估價仍超支，每次進入產品都看到橫幅；沒有歷史 inbox [Q6] [intent:Q16]。
7. **對不到官方價目的元件**必須列名、不計入總額、顯示「N 項尚未定價」，並可再覆寫 [Q7] [intent:Q15]。
8. **無外部時間盒，但有競爭優先事項**，本工作可被插隊 [Q8]。

未滿足則不可稱為可行的硬條件：cost calculator 必須含 property-based testing [memory:M1]；新 HTTP 端點必須有 `TestClient` 測試 [memory:M5]；若改權限種子必須有 allow/deny 雙向測試 [memory:M6]；schema／seed 變更必須同步部署資產 [memory:M7]。

## 技術可行性

以能力層描述現況與落差（技術細節的出處見問題檔 Sources）：

| 面向 | 現況 | 落差與可行性 |
| --- | --- | --- |
| 資源擷取 | 可從架構圖抽出元件標籤、樣式與連線，沒有價目 SKU、機型或區域 [code:C1] | 「對到圖上資源」做得到列名；對到官方價目依賴後續對應規則，對不到的走 [Q7] |
| 雲別 | 可從圖的關鍵字辨識 aws／gcp／azure；圖本身沒有持久的雲別欄位 [code:C2] [code:C3] | 跟圖走 [Q1] 可行；辨識失敗走 Manual Override，不另選預設雲 |
| 官方報價 | 沒有 cost calculator、也沒有任何官方報價客戶端 [code:C9] | 本 intent 將讓 ADR-0006 的 cost calculator 落點從「尚無模組」變成必須實作；存取策略已由 [Q2] 收窄為公開免帳號端點 |
| 預算與警告 | 沒有預算物件、沒有超支狀態 | 每張圖一個月上限 [Q4] 與畫面標示 [intent:Q16] 為新能力，不依賴既有模組 |
| 站內通知 | 沒有 inbox、未讀數或進產品橫幅原語 [code:C8] | [Q6] 把本輪上限收在「超支期間每次進入都看到橫幅」，避免做成訊息中心 |
| 入口 | 側欄只有架構與 Admin；沒有成本路徑 [code:C6] [code:C7] | Sidebar 加 C 柱與產圖後 CTA 為產品已決項 [intent:Q13]，屬導覽擴充，可行性無疑慮 |
| 權限 | 今日只有 FinOps 能改 C1；架構師與工程主管只能看 [code:C4] [code:C5] | [Q5] 要求三種不同變更權；現有 view／edit／review 是否夠用留設計階段（R2） |

**官方價目 ≠ 客戶帳單**（AWS 平台視角）：本輪數字是公開 list price／on-demand 價目，不是 Cost Explorer、不是承諾折扣、也不是實際發票。這與「不得使用 production credentials」一致 [memory:M2]。C2（pricing models）本輪不交付 [intent:Q9]，故本輪不承諾 Spot／RI／Savings Plan 比較。

**價目新鮮度**：公開價目可能落後；C1 驗收已要求顯示定價假設與來源時間戳 [stories:C1]。快取或重試手段屬設計階段，本階段不預選（raid-log R5）。

## 合規掃描

- **適用框架**：未指認 PCI-DSS、HIPAA、SOC 2、GDPR 等外部框架。估價資料為公開價目、架構圖資源清單，以及使用者設定的時數／預算／單價覆寫；平台為內部 staging [memory:M2]。此「不適用」屬假設，見 A2。
- **資料分類**：公開價目為公開資訊；覆寫後的單價與預算上限為內部營運數字，不是持卡人或健康資料。
- **security baseline 四面向**見 `constraint-register.md` 法規與政策表；不得僅以「已有 ADR-0006」帶過 [memory:M8]。單價覆寫與預算變更必須留下誰改了什麼的稽核紀錄。

## 驗證方式

- 成功指標可測：官方價路徑下，總額應等於已定價列之和，且未定價列不計入 [Q7]；來源時間戳可見 [stories:C1]。
- 缺價／API 失敗路徑：該列可覆寫並標記 Manual Override [intent:Q15]。
- 超支：總額超過該圖每月預算時，成本畫面有視覺標示，且超支期間每次進入產品都出現橫幅 [Q4] [Q6] [intent:Q16]。
- cost calculator 的性質測試（加總、時數重算、覆寫標記、未定價列排除）屬 Construction 必做，不是本 stage 的設計。

## 風險分析

完整風險、假設、議題與依賴見同目錄 `raid-log.md`；關鍵四項：

- **R1 公開免帳號價目的雲別覆蓋未知** — 部分雲可能幾乎全走 Manual Override，削弱「報價對到圖上資源」[Q1a] [Q2]
- **R2 三種變更權 vs 既有三旗權限模型** — 切過頭或切不夠都會讓 [Q5] 的產品語意失真
- **R5 公開價目端點的可用性、節流與過期** — 緩解留設計階段
- **R8 競爭優先事項造成中斷** [Q8]

## Assumptions & Open Questions

- [assumption] 本輪不要求三雲都打得到官方 API；只要公開免帳號價目覆蓋得到的雲走官方價、其餘走 Manual Override，C1 畫面仍算交付 [Q1a] [Q2]
- [assumption] 內部平台的估價資料不受 PCI／HIPAA／SOC 2／GDPR 等外部框架約束；此判斷未經法務或合規方獨立確認
- [assumption] 「進入產品」指使用者已登入後進入受保護畫面；橫幅出現在哪些頁面留待設計，本階段只鎖定「超支期間每次進入都看到、不能永遠關閉」[Q6]
- [assumption] C1 故事驗收中的 egress 本輪不交付，不視為刪除 baseline 故事，而是本 intent 的驗收切片；不回改 `stories.md` [Q3] [intent:Q9] [stories:C1]
- [assumption] （開放問題）現有 view／edit／review 能否表達 [Q5] 的三種變更，或需要更細的動作，本階段不定案，列為設計階段必答 [Q5]

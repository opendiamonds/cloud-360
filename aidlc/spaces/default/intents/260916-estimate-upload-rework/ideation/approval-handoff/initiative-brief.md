# 專案提案書：C1 成本估算改版（上傳估價表）

> Ideation 四站的彙整。給沒有參與前面討論、要決定這件事該不該做的人看。

## 建議：**GO**

技術上沒有任何一段超出本專案能力。四項已識別的風險中三項由使用者明確接受，第四項（解析靜默錯誤）加上了額外的設計義務。阻擋 construction 的規則衝突已由 ADR-0017 解除，`deploy/render-env.sh` 的 repo contract 違規已於 2026-09-16 清除，兩支 contract 腳本現為綠燈。**沒有未解除的阻塞項。**

## 這件事在解決什麼

現行 C1 讓系統自己去取價：讀架構圖、對 SKU、打公開價目端點，或用 Playwright 自動操作官方 Calculator。**這條路太慢或太常失敗**——逾時、產品對不到、需要重試，使用者等不到結果。

改版把**產生估價**這件事交還給使用者：自行上傳 AWS／Azure／GCP 的官方估價表，系統解析後由 agent 給建議。同時把成本 agent 從 `claude-agent-sdk` 換成 LangGraph。

系統不再自己產生估價，但 agent 在寫建議時仍可查官網現價來支撐具體主張（「換成 X 規格可省 Y」）。這條查價路徑有嚴格界線——只有 agent 能用、按需不逐列、只准公開免帳號端點、查到的價格只寫進建議文字不回寫明細。

## 要交付什麼

| 能力 | 等級 |
|---|---|
| 上傳估價表（AWS CSV／Azure XLSX／GCP CSV，至少一朵雲） | Must |
| 解析並呈現逐項明細（品項、規格、數量、金額）＋ 總額 | Must |
| 省錢建議 | Must |
| 解析結果的**確定性機械檢查**（總額對帳、幣別一致、數量範圍） | Must |
| 成本 agent 遷移至 LangGraph（經 OpenRouter） | Must |
| 既有自動估價路徑退場（9 端點、4 張表、兩支 Playwright runner） | Must |
| 跨雲比較建議 | Should |
| 估價品質檢查建議（agent 用自然語言指出可疑數字） | Should |
| agent 按需查官網現價（公開免帳號端點） | Should |

**明確不做**：定期重新估價／排程重跑。

**未承諾**（不在範圍、不在排除清單、不推定未來去向）：建議結果匯出、歷史版本比較、依建議回寫架構圖。

## 成功怎麼衡量

從上傳到看到建議的時間。目標 3 分鐘，實測 5 分鐘內可接受。

這是唯一的指標。**它不衡量正確性**——這一點在風險段落有對應處置。

## 可行性摘要

不需要雲端帳號憑證（估價由使用者提供，agent 查價只用公開免帳號端點）、不需要物件儲存（原始檔不留存）、不需要新的基礎設施層（沿用現有 FastAPI ＋ PostgreSQL ＋ Cloudflare Tunnel）。

需要三樣新東西：本 repo 的第一個檔案上傳面、一個試算表解析套件（供 Azure XLSX）、一條走 OpenRouter OpenAI 相容端點的 LangGraph 模型存取路徑。

`pricing_client` 從既有程式碼留用並改造為 agent 的查價工具，其餘計價模組的去留由 code-generation 依實際需要判定。走 IAM 的 `pricing_sdk.py` 確定刪除。

## 風險與處置

| 風險 | 處置 |
|---|---|
| **解析靜默錯誤**（欄位對錯不報錯，agent 照著錯數字給有自信的建議） | **接受並加碼**：除了 agent 的品質檢查建議，另須設計一套不依賴 LLM 的機械檢查（總額對帳、幣別一致性、數量合理範圍），已升為 Must 能力。這是本案唯一被要求補強的風險 |
| **agent 查價把 SKU 對應的脆弱處帶回來**（新增）| 接受。衝擊低於舊架構——查不到只是該筆「無法查證」，不阻斷明細與建議；舊架構下對不到就估不出價 |
| **目錄價與估價表的價格本不該相等**（新增；估價表可能含 CUD／RI／Savings Plan 折扣）| 部分緩解。已禁止以查得價格回寫明細，擋掉最壞後果；但 agent 建議文字仍可能誤述，設計階段須要求引用現價時標明那是未折扣定價 |
| **3 分鐘可能不可達**（瓶頸全在 LLM 推論） | 接受。上限放寬到 5 分鐘，需進度指示；實測在 nfr-requirements |
| **完整估價內容送第三方**（本地不留原始檔，但解析結果完整送進 OpenRouter） | 接受。使用者已知情並選擇此配置 |
| **兩套 agent 框架並存**（本案只遷成本 agent，其餘五個另開 intent） | 接受。刻意的分階段決定 |

## 交付形狀

十二個 proto-unit。第一梯次三項依賴為空、可平行起跑：估價表解析器、舊路徑退場、LangGraph 骨架。之後是上傳端點與機械檢查 → 明細頁面 → 省錢建議 → 建議呈現。查價工具與另兩類建議排在最後一梯次。

**兩條不能違反的約束**：

1. 舊路徑退場與新明細頁面**不得分批部署**。本專案是 deploy-on-merge，分兩批會讓中間有一次部署使 `/cost` 是死的。
2. 建議功能落地之前，產品處於「有明細沒建議」的狀態，能力低於改版前。有兩人以上可平行後，這段窗口期有機會壓到接近零，但它不會自動消失，delivery-planning 要主動壓縮。

## 團隊與驗收

兩人以上可平行作業。驗收由 Danniel 一人代表三種使用者角色（架構師、FinOps／分析、管理層）——意即 inception 的使用者故事沒有獨立的角色代表可訪談，三個 persona 的需求都由同一人轉述。

關鍵關係人只有「維運這個 repo 的人」，關注舊程式碼退場後的維護負擔與部署風險。

## 進 Inception 之前要完成的事

| 項目 | 狀態 |
|---|---|
| M2 規則衝突的 ADR | **已完成** — ADR-0017（同日經 §8 修訂）|
| `deploy/render-env.sh` 的 repo contract 違規 | **已完成** — AWS 帳號憑證傳遞整條移除，兩支 contract 腳本綠燈 |

## 帶進 Inception 的義務

| 義務 | 指派對象 | 來源 |
|---|---|---|
| 設計不依賴 LLM 的解析機械檢查（CAP-9）| functional-design | approval-handoff Q1 |
| 守住 CAP-8 的四條界線，特別是「不得在明細加現價欄位」 | functional-design | ADR-0017 §8 |
| 要求 agent 引用現價時標明那是未折扣定價 | functional-design | RISK-08 |
| 定義查價失敗時 agent 的行為（明說查不到，不得推測）| functional-design | RISK-07 |
| 3 分鐘目標值的真實端到端實測 | nfr-requirements | feasibility ASSUM-01 |
| 「可選綁定架構圖」的綁定語意定義（標籤 vs 一致性檢查） | domain-design | scope-document |
| 新稽核記錄的粒度（原始檔不留存使事後回溯無據） | domain-design | constraint-register |
| 解析器須為純函式，PBT hard constraint 由 `cost_calculator` 移轉至此 | functional-design／code-generation | ADR-0017 §2 |

## Assumptions & Open Questions

- [assumption] 三朵雲官方匯出格式在可見期間內穩定。實際上都可能無預警改版，解析器會在格式變動當天無聲失效。是否做格式版本偵測未定。
- [assumption] 估價表不含個人資料，故 PCI／HIPAA／GDPR 均不觸發。若實際檔案含客戶聯絡人資訊需重新判定，且第三方傳輸風險等級上升。
- [assumption] 退場範圍以 feasibility 的盤點為準（9 端點、4 表、runner 清單）。若發現隱性依賴需重新確認。
- [open] value-first 的第一批究竟包含哪些能力（是否含省錢建議）尚未切分，留給 delivery-planning。窗口期長度取決於此。
- [assumption] CAP-8 的四條界線沒有機械強制手段，全靠實作者遵守。最容易被跨越的是「不得在明細加現價欄位」——那在 UI 上是很自然的想法。
- [open] `scope-definition` 在引擎的完整性檢查中標記為 drifted，`feasibility` 等四站標記為 untracked。兩者都不影響決策內容，處置與理由見 `decision-log.md`。
- [open] ADR-0017 在建立後 25 分鐘內即被自我修訂（§8），顯示產品邊界到 ideation 最後一站仍在移動。若 inception 再出現同類反轉，應認真考慮回頭重跑 intent-capture，而不是繼續就地修補。

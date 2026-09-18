# Intent Statement — Admin 使用者最後登入時間

<!-- Stage: intent-capture（Ideation 1.1）· 來源標籤定義見 intent-capture-questions.md 的 ## Sources。
     每個實質主張都掛有來源標籤；未掛標籤的內容不得存在。 -->

## Problem Statement

- 管理者無法得知帳號的最後活動時間，因而無法滿足存取稽核對「帳號是否仍在使用」的查驗需求 [Q1]
- 具體的原始請求為：在 Admin 頁加上使用者最後登入時間欄位 [desc]
- 此稽核能力為自發建立，並非回應外部合規要求或既有事故 [Q4]

## Target Customer

| 受益者 | 獲得什麼 | Source |
| --- | --- | --- |
| `Platform_Admin` | 在使用者管理介面直接看到帳號最後活動時間，不需另行查詢 | [Q5] |
| `Security_Reviewer` | 取得存取稽核所需的帳號活動證據 | [Q1] [Q13] |

本表僅列**利益已被確認**的受益者。可見角色的範圍見 `## Initial Scope Signal`，其涵蓋面大於本表 —— 但「可見」未經確認等同「受益」，故不將僅具可見性的角色列為受益者 [Q11] [Q12]。

## Success Metrics

- Admin 使用者介面能顯示每個帳號的最後登入時間，且該值可與後端紀錄對照驗證 [Q3]
- 未登入超過設定門檻的帳號帶有視覺標示 [Q3]（門檻值的狀態見 `## Assumptions & Open Questions`）

## Initiative Trigger

- 無特定觸發事件；屬機會性改善，無外部期限 [Q4]

## Initial Scope Signal

### Workflow-selected scope

<!-- 僅證明 workflow 起跑時選定的 scope，不代表使用者確認的產品邊界。 -->

- `feature`（workflow-selected）[scope]

### User-confirmed product boundary

- 使用者確認 `feature` 即為其意圖的產品邊界 [Q8]
- 稽核只需最後一次登入時間，不需保留完整登入歷史；資料模型須預留未來擴充至歷史紀錄的路徑 [Q9]
- 稽核資訊對所有可進入使用者管理介面的管理類角色一律可見，不做更細的角色區隔 [Q11] [Q12]
- 功能範圍包含為 `Security_Reviewer` 開通使用者管理介面的檢視權限 [Q10]

### 適用的既有約束

- 資料庫結構或部署必知的 schema／seed 行為變更，須同步更新部署資產，未完成不得標示相關 Construction／部署階段為完成 [memory:M1]
- 雲端供應商 production 環境、production credentials 等項目不在本 repository 範圍內，除非經新 ADR 核可 [memory:M2]
- security baseline 為常設 hard constraint，涵蓋 IAM 等面向 [memory:M4]

## Assumptions & Open Questions

- [assumption] 「超過 N 天未登入」的 N 尚未定義，本階段不假設任何數值；成功指標在 N 決定前不可完整驗證 [Q3] [Q14]
- [assumption] 業務問題被指認為稽核需求，同時又無外部觸發或期限；本文件據此理解為「自發建立稽核能力」，而非回應既有稽核缺失 [Q1] [Q4]
- [assumption] 本工作被描述為機會性改善，卻採用 `feature` scope 的完整階段集；成本與驅動力的比例關係未在本階段檢驗 [Q4] [Q8]
- [assumption] 為 `Security_Reviewer` 開通的是使用者管理介面的檢視權限，其接觸面大於稽核欄位本身；此擴張與 security baseline 的最小權限面向存在張力，本階段未取得針對該副作用的獨立確認 [Q10] [memory:M4]
- [assumption] （開放問題）未來若需保留登入歷史，擴充路徑的具體形式尚未探討；本階段僅確認需預留，不定義做法 [Q9]

## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-08-02T15:23:07Z
**Iteration:** 4（最終驗證關卡）

### 感測器結果

實際執行結果（非採信 builder 主張），三個 sensor × 兩份 artifact，全數 `findings_count: 0`：

| Sensor | intent-statement.md | stakeholder-map.md |
| --- | --- | --- |
| `claim-sources` | `{"pass":true,"findings":[],"findings_count":0}` | `{"pass":true,"findings":[],"findings_count":0}` |
| `required-sections` | `{"pass":true,"h2_count":6,"findings_count":0}` | `{"pass":true,"h2_count":4,"findings_count":0}` |
| `upstream-coverage` | `{"pass":true,"reason":"no upstream","findings_count":0}` | `{"pass":true,"reason":"no upstream","findings_count":0}` |

Builder 主張的「兩份 artifact 皆 0 findings」屬實。

### 6 項變更逐項核對

| # | 變更 | 核對方式 | 結果 |
| --- | --- | --- | --- |
| 1 | 第 2 輪確認標題改為精確 `## Assumption Confirmation`；第 1 輪保留帶後綴標題；確認內文重建為 10 條逐字複製的 assumption 條目；`[Answer]: A. Accept assumptions` 精確 | 逐字比對 questions 檔第 236/207 行標題、第 243–247／251–255 行（共 10 條）與兩份 artifact 的 `## Assumptions & Open Questions`（各 5 條）、第 260 行 `[Answer]:` | 通過。10 條逐字相符（含粗體反引號、方括號來源標籤順序），標題精確無後綴，`[Answer]:` 無多餘文字 |
| 2 | Sources register M1–M4 內的引用文字去除開頭 `- ` 列表標記 | 對照 `project.md#Mandated`／`#Scope Overrides`／`#Decided`、`team.md#Mandated` 的實際條文（經 dispatch rule bundle 取得原文） | 通過。M1–M4 四筆引文與來源條文逐字相符（僅去除開頭 `- `） |
| 3 | 兩份 artifact 開頭 blockquote 與一句說明文字改為 HTML comment | grep 兩份 artifact 是否殘留 `^>` 開頭行 | 通過。無殘留 blockquote；intent-statement.md 第 3–4 行、第 34 行，stakeholder-map.md 第 3–4 行皆為 `<!-- ... -->` |
| 4 | intent-statement A3 拿掉 `[scope]`，只留 `[Q4] [Q8]` | 比對 artifact 第 55 行與 questions 檔第 2 輪確認第 245 行 | 通過。兩處皆為 `[Q4] [Q8]`，無 `[scope]`；`[scope]` 僅出現於 `## Initial Scope Signal`（第 36 行），用法合規 |
| 5 | 兩個 `[open question]` 條目改標 `[assumption]`、內文加 `（開放問題）`前綴 | grep 兩份 artifact 全部 `[assumption]` 出現位置 | 通過。intent-statement.md 第 57 行、stakeholder-map.md 第 38 行皆為 `[assumption] （開放問題）...`；全部 `[assumption]` 標籤（10 處）皆落在各自的 `## Assumptions & Open Questions` 區內，無區外殘留 |
| 6 | stakeholder-map 表格列 `Unknown (open question) [assumption]` 改寫為 `Unknown（開放問題，見 Assumptions A5/A6）` | 檢查表格第 18、27 行是否含字面 `[assumption]`；並回頭核對 A5/A6 指向內容是否與表格列語意相符 | 機制面通過（表格區無字面 `[assumption]`）。但發現追溯性問題，見下方 Finding #1 |

### Findings

| # | Severity | Location | Finding | Recommendation |
| --- | --- | --- | --- | --- |
| 1 | Minor | `stakeholder-map.md` 第 18、27 行 | 表格寫「見 Assumptions A5」「見 Assumptions A6」，但 A5/A6 這組字母編號只存在於 `intent-capture-questions.md` 第 207 行起、已被明示取代（「已被下方第 2 輪取代」）的第 1 輪確認表格中；兩份 artifact 現行的 `## Assumptions & Open Questions` 皆為無編號的純條列，本身找不到「A5」「A6」這個標籤。內容核對後語意相符（A5 對應「影響者非決策者」、A6 對應「回報節奏」條目），並非誤指，但讀者若只讀現行 artifact 與現行（第 2 輪）確認區，無法就地解析這兩個標籤，需回頭挖已標示為取代的舊區塊才找得到 | 在兩份 artifact 現行 `## Assumptions & Open Questions` 條列前補上穩定編號（如 A1.–A5. / A1.–A5.），或把表格文字改為直接複述該條 assumption 的關鍵詞而非引用一個已被取代區塊裡的字母，讓 artifact 自身可解析、不依賴讀者去查已取代的歷史區塊 |

### Summary

三個 sensor（`claim-sources`／`required-sections`／`upstream-coverage`）在兩份 artifact 上皆為 0 findings，builder 的第 4 輪機械性修正（標題精確化、來源引文去標記、meta-prose 轉 HTML comment、`[scope]` 標籤收斂、`[open question]`→`[assumption]` 統一、表格欄位改寫避開字面標籤）逐項核對屬實，且未引入語意內容變動；round 3 已完成的語意驗證未見回歸。唯一發現是 Finding #1（Minor）：stakeholder-map 的兩個表格列指向一組僅存在於已取代區塊的字母編號，屬追溯性瑕疵而非結構或來源錯誤，不影響工程可據以開發、QA 可據以測試的判斷，故不構成 READY 的阻擋條件。


# A3 Amendment — AWS Well-Architected Tool API Integration

> 將 A3 評核對齊 AWS Well-Architected **語意／問卷結構**；是否呼叫官方 API 見下方決策。  
> 狀態：**POC DONE**（離線 Lens；無 AWS API）— 決策已鎖定；實作見 `aidlc-docs/construction/a3/code/offline-lens-poc-summary.md`  
> 參考：
> - [WA Tool API PDF](https://docs.aws.amazon.com/pdfs/wellarchitected/latest/APIReference/wellarchitected-api.pdf)
> - [aws-samples/sample-well-architected-custom-lens](https://github.com/aws-samples/sample-well-architected-custom-lens)


### 重要前情（務必讀）

#### 1) 「不登入 AWS」vs「用 AWS Tool」

| 做法 | 要不要 AWS 帳號／登入 | 說明 |
|---|---|---|
| 呼叫 **WA Tool API**（`CreateWorkload`、`UpdateAnswer`、`GetLensReview`…） | **要** | 官方服務在你的 AWS 帳戶內；無憑證無法評分 |
| 使用 [sample-well-architected-custom-lens](https://github.com/aws-samples/sample-well-architected-custom-lens) 的 **Lens JSON 內容** | **不要** | 該 repo 是各產業／技術 **Custom Lens 定義檔**（問題、支柱、指引）。官方用法是匯入 Console；我們可改為 **離線載入 JSON**，由 Cloud-360 本地規則／Agent 依問卷評圖 |
| 僅把 repo 當文件閱讀 | 不要 | 不自動產生分數 |

**結論**：**不登入 AWS 就不能用「AWS WA Tool 這項雲端服務」打分**；但 **可以** 參考該 sample 的 Lens JSON，在 Cloud-360 **離線**做「同結構的問卷式評核」（語意對齊 WA，執行不經過 AWS）。

該 repo README 也寫明匯入前提是 *Access to AWS Well-Architected Tool* 與 *AWS account*——那是走 Console／API 路徑時的前提，不是離線引用 JSON 的前提。

#### 2) 官方 API 本質（若選線上）

| 能做 | 不能做 |
|---|---|
| Workload／Lens／Answers／RiskCounts | 直接吃 draw.io XML 自動出分 |
| Trusted Advisor checks（另需帳號整合） | 無 IAM 離線呼叫 |

#### 3) 鎖定決策摘要

| Q | 答案 | 備註 |
|---|---|---|
| 0 | **A** | 完全離線 |
| 1 | **D** | 離線 Lens 為準；啟發式雙軌 UI |
| 2 | **B** | Agent／規則填答 → 本機 answers |
| 3 | **A** | 不做 Trusted Advisor |
| 4 | **D** | 本期無 AWS 憑證 |
| 5 | **C** | RiskCounts＋啟發式 |
| 6 | **A** | Lens 失敗仍完成啟發式 |
| 7 | **B** | 薄 POC |
| 8 | **B** | 自製精簡 lens JSON |

### Checklist

- [x] 問題全部作答（含新增 Q0）  
- [ ] 更新 requirements／FD／NFR（POC 後可補）  
- [x] Code Gen POC（離線 lens pack；**未**接 boto3）  

---

## Questions

### Question 0（新增 — 對齊「不登入 AWS」）
本期評核執行環境要哪一種？

A) **完全離線**：不呼叫任何 AWS API；以 Custom Lens **JSON**（可來自 [sample-well-architected-custom-lens](https://github.com/aws-samples/sample-well-architected-custom-lens) 或官方框架問題摘要）＋圖面摘要／Agent 填答，在 Cloud-360 內計分

B) **可選線上**：有 AWS 憑證時走 WA Tool API；無憑證時自動降級為 A

C) **必須線上**：一定要 AWS 憑證；無憑證則評核失敗（與「不登入」衝突，勿與該目標同選）

X) Other (please describe after [Answer]: tag below)

[Answer]: Ａ

---

### Question 1
與現有 **本地規則引擎**（`WaRuleEngine`）的關係？

A) **混合**：現有啟發式＋Lens 問卷式評核（離線或線上）並陳

B) **以 Lens／WA 問卷為準**：分數來自問卷答案風險模型；啟發式降級或關閉

C) **僅啟發式**（維持現況）；Lens JSON 只當 Agent 建議參考，不改計分權威

D) **離線 Lens 為準**（建議配 Q0=A）：載入選定 lens JSON；Agent 依 draw.io 摘要對每題產出答案；本機彙總風險／分數（**不**呼叫 AWS API）

X) Other (please describe after [Answer]: tag below)

[Answer]: Ｄ

---

### Question 2
draw.io 圖面如何對到「評核結構」？

A) **一圖一 Workload（線上）**：`CreateWorkload`＋官方／自訂 lens

B) **Agent／規則對問題產出答案** →（線上）`UpdateAnswer` 或（離線）寫入本機 `answers_json` → 再彙總風險／分數

C) **只建空結構**，答案全手動

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 3
是否啟用 **Trusted Advisor／Discovery**？

A) **本期不做**

B) **做**（需要 AWS 帳號）

C) **預留**，下期再做

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 4
**AWS 憑證**？（若 Q0=A 可選 D）

A) 平台共用 IAM／env credential chain

B) 每租戶自己的 assume-role

C) mock／開關後再接真 AWS

D) **本期不需要 AWS 憑證**（離線 Lens）

X) Other (please describe after [Answer]: tag below)

[Answer]: Ｄ

---

### Question 5
分數／發現 UI？

A) 維持 0–100 加權；由風險等級換算

B) 顯示 WA 風格 **RiskCounts／逐題狀態**（HIGH／MEDIUM／NONE…）

C) 雙軌：風險計數＋本地啟發式分

X) Other (please describe after [Answer]: tag below)

[Answer]: Ｃ

---

### Question 6
失敗時行為（無 lens 檔、Agent 失敗、或線上 API 失敗）？

A) 本地啟發式仍完成；Lens／WA 區塊 error＋可重試

B) 整次評核失敗

C) 部分成功狀態（例 `lens_partial`／`aws_unavailable`）＋已有結果可讀

X) Other (please describe after [Answer]: tag below)

[Answer]: Ａ

---

### Question 7
實作節奏？

A) 先修 requirements＋FD／NFR，再 Code Gen

B) 薄 POC（先載入一個 sample lens JSON＋Agent 答 3～5 題）

C) 只更新設計文件

X) Other (please describe after [Answer]: tag below)

[Answer]: Ｂ

---

### Question 8（新增 — Lens 來源）
若走離線／半離線，第一個 Lens 包選哪個？

A) 使用 [sample-well-architected-custom-lens](https://github.com/aws-samples/sample-well-architected-custom-lens) 中 **一個** 領域（請在 Answer 後寫資料夾名，例 `generative-ai-lens`／`iot-lens`）

B) 先做 **精簡自製 lens JSON**（對齊五／六支柱常見題，結構相容 custom lens），sample repo 當格式參考

C) 打包 **多個** sample lenses，UI 可選

X) Other (please describe after [Answer]: tag below)

[Answer]: Ｂ

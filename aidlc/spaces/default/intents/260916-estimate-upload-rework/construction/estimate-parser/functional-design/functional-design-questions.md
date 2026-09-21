# Functional Design 問答：U1 `estimate-parser`

本 Unit 是 **library**：三雲估價表解析＋機械檢查，純函式、零 I/O。契約 C1（`ParseResult`／`LineItem`／`MechanicalCheckResult`）已定欄位形狀；本站釘**行為規則與工作流**，不寫實作碼。

## Sources

- **[S1]** U1：`backend/cost/estimate_parser.py`＋三格式讀取器；`EstimateValidator` 路徑未定（domain 審閱次要）
- **[S2]** FR1.2／1.5、FR2.*、FR4.*；contract C1 shared-schema
- **[S3]** 無法辨識＝金額或數量無法解析為數值；有無法辨識列則跳過總額對帳（FR4.4）

---

## Q1 對外入口形狀

- **A.** 兩個純函式：`parse(bytes, filename?) → ParseResult` 與 `validate(ParseResult) → MechanicalCheckResult`（協調層 U2 各呼一次）
- **B.** 單一 `parse_and_validate(...) → { result, checks }`，內部仍可拆模組
- **C.** `parse` 回傳結果內嵌可選 `checks` 欄，由參數 `with_checks=True` 控制
- **X.** Other (please specify)

[Answer]: A — `parse(bytes, filename?) → ParseResult` 與 `validate(ParseResult) → MechanicalCheckResult` 兩個純函式

---

## Q2 `EstimateValidator` 模組路徑（CI 邊界）

- **A.** 與解析器同檔 `estimate_parser.py` 內的函式／區塊；CI 腳本只守這一檔
- **B.** 同套件獨立檔 `estimate_validator.py`；CI 腳本同時守兩檔（擴充 FR9.6）
- **C.** 子模組 `parsing/validator.py`（多一層目錄）
- **X.** Other (please specify)

[Answer]: B — 獨立 `estimate_validator.py`；CI 邊界腳本同時守兩檔

---

## Q3 檔案完全無法當成表開啟時（壞魔數已由 U2 擋；此指內容毀損／無標頭）

- **A.** 回傳 `detection.status=ambiguous` 且 `lines=[]`，由 U2 轉 400
- **B.** 解析器拋出領域錯誤型別（非 HTTP）；U2 映射為 400
- **C.** 回傳 `detection.status=resolved` 但 cloud 為呼叫端 override 值、`lines=[]`（僅在有 override 時）——無 override 則同 A
- **X.** Other (please specify)

[Answer]: A — 回傳 `detection.status=ambiguous` 且 `lines=[]`，由 U2 轉 400

---

## Q4 表上沒有「宣告總額」欄／列時

- **A.** `totals.statedTotal=null`；總額對帳 `attempted=false`，`skippedReason` 說明無宣告總額（與「有無法辨識列」分開）
- **B.** 用可解析列金額加總當作 `statedTotal`，對帳永遠 withinTolerance（失去檢查意義）
- **C.** 視為解析失敗（ambiguous／錯誤）
- **X.** Other (please specify)

[Answer]: A — `statedTotal=null`；對帳 `attempted=false`，skippedReason 說明無宣告總額

---

## Q5 幣別「多數」怎麼算（FR4.1）

- **A.** 以**可解析列**中出現次數最多的幣別為準；並列最高票時取字典序第一並在 checks 附註 `currencyTie=true`
- **B.** 以表頭／totals.currency 為準；列上不同者一律 offender
- **C.** 任一列與其他列不同即整體 `currencyConsistent=false`，不計算「多數」（所有少數與第一個非空幣別比）
- **X.** Other (please specify)

[Answer]: A — 可解析列多數決；平手取字典序第一並 `currencyTie=true`

---

## Q6 數量「正值」邊界（FR4.2）

- **A.** 必須 `quantity > 0`；0 與負數皆 offender
- **B.** 允許 `quantity >= 0`；僅負數 offender
- **C.** 依雲別：AWS／GCP 須 `>0`；Azure 允許 0（保留列）
- **X.** Other (please specify)

[Answer]: B — 允許 `quantity >= 0`；僅負數為 offender

---

## Consolidated Summary Confirmation

**U1 `estimate-parser` 行為定案**

| 項 | 定案 |
|---|---|
| 入口 | `parse` 與 `validate` 分離（Q1=A） |
| 模組 | `estimate_parser.py` + `estimate_validator.py`；CI 守兩檔（Q2=B） |
| 毀損／無標頭 | `ambiguous` + 空 lines（Q3=A） |
| 無宣告總額 | statedTotal=null；對帳不 attempted（Q4=A） |
| 幣別 | 可解析列多數決；平手字典序 + currencyTie（Q5=A） |
| 數量 | `>= 0` 合法；僅負數 offender（Q6=B） |

**將產出**：entities.md、rules.md、functional-spec.md、traceability.json（library，無 frontend-components）。

**後果**：Q6=B 讓數量為 0 的列可參與總額對帳（若已 parsed）；與「無法辨識」定義（金額或數量無法解析）不衝突——0 是合法數值。

[Answer]: Looks correct

含 Major 修正後確認。

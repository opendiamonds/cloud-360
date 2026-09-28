# NFR Requirements — 釐清問題（estimate-parser）

> Unit: `estimate-parser`（U1）· kind: **library**  
> Stage: nfr-requirements · 適用產物：security-requirements、tech-stack-decisions、traceability  
> （performance／scalability／reliability／observability 對 library **N/A**）  
> 作答：在每題 `[Answer]:` 後填選項字母（例如 `A`）。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 純函式 `parse`／`validate`；模組路徑 `estimate_parser.py`／`estimate_validator.py` | FD Q1=A、Q2=B |
| 禁 import `httpx`／`requests`／`sqlalchemy`／`fastapi`；CI 邊界腳本改指向新模組 | FR2.3、FR9.6 |
| 須有 property-based tests | FR2.4、NFR4、ADR-0006 |
| 檔案大小 5 MB、魔數／副檔名驗證屬 **U2** 上傳面；本 unit 收 `bytes` | FR1.3、FR1.4、U2 邊界 |
| 原始檔不落地屬 U2；本 unit 不持久化 | FR1.6 |
| 進度 UI（NFR2）、HTTP 延遲（NFR1）、事件稽核（NFR5）非本 unit | unit-of-work |
| 三層形狀由 U2 維持；本 unit 即純函式層錨點 | NFR6 |
| 無新語言／執行期框架 | technology-stack／brownfield |

---

## Questions

### Question 1
**NFR3 — 解析資源界限（本 unit 內）怎麼釘？**  
U2 已擋 5 MB；惡意／異常檔仍可能在記憶體內膨脹（超大 CSV 列數、XLSX zip bomb）。

A. **雙上限**：列數 ≤ 50_000；且 CSV／解壓後字元或 cell 總量有硬上限（建議：解壓後 ≤ 32 MiB 等價）。超出 → 回傳 ambiguous／空 lines，**不** raise。**（建議）**

B. **只限列數**（例如 50_000）；不另限解壓／字元量。

C. **本 unit 不設限**——完全信任 U2 的 5 MB；資源攻擊留到 U2／運維。

X) Other（請說明）

[Answer]: A. 雙上限：列數 ≤ 50_000；解壓後／字元等價 ≤ 32 MiB；超出回傳 ambiguous／空 lines，不 raise。 <!-- 2026-09-18T17:32Z -->

---

### Question 2
**NFR3 — 解析失敗時錯誤／例外訊息形狀？**  
純函式多半不拋 HTTP；若內部例外被上層轉譯，仍可能洩漏路徑。

A. **契約**：本 unit 公開 API **不**拋含本機絕對路徑或 traceback 字串的例外訊息；可拋 `ValueError`／自訂錯誤，訊息僅語意代碼或短中文說明。堆疊不得進回傳結構。**（建議）**

B. **允許**標準例外訊息（含可能的檔名片段）；由 U2 負責遮罩。

C. **永不拋例外**：所有失敗都進 `ParseResult.detection=ambiguous`／空 lines。

X) Other

[Answer]: A. 公開 API 不拋含本機絕對路徑或 traceback 的訊息；可短語意說明；堆疊不進回傳結構。 <!-- 2026-09-18T17:32Z -->

---

### Question 3
**NFR4／FR2.4 — PBT 最低性質集合？**

A. **至少三條 Hypothesis 性質**：(1) 同輸入同輸出；(2) 合法 fixture 不產生禁 import 路徑副作用；(3) 對帳容差／無法辨識列與 BR4 一致（或等價的 deterministic 性質）。細節可在 code-gen 展開。**（建議）**

B. **至少五條** 性質（含 fuzz 格式嗅探、雲別判定等），否則 NFR 不通過。

C. **example-based 為主**；PBT 僅 1 條 smoke（弱於 ADR-0006，不建議）。

X) Other

[Answer]: A. 至少三條 Hypothesis 性質（同入同出；禁 import 副作用；BR4／對帳或等價 deterministic）。 <!-- 2026-09-18T17:32Z -->

---

### Question 4
**FR9.6 — 邊界腳本要掃哪些路徑？**

A. **`estimate_parser.py` 與 `estimate_validator.py` 兩者**（及同套件下被 parser 直接 import 的讀取器模組，若拆檔）。命中禁 import 即失敗。**（建議）**

B. **只掃 `estimate_parser.py`**；validator 免掃。

C. **掃整個 `backend/cost/` 套件**（含既有 pricing／calculator 殘件）。

X) Other

[Answer]: A. 掃 estimate_parser.py、estimate_validator.py 及 parser 直接 import 的讀取器模組。 <!-- 2026-09-18T17:32Z -->

---

### Question 5
**Tech stack — Azure XLSX 用什麼讀？**

A. **沿用 repo 既有選擇**（若已有 openpyxl／類似依賴則不新增；查 `backend/requirements.txt` 後釘名）。無既有則加 **openpyxl** 並記 tech-stack。**（建議）**

B. **強制新增 openpyxl**，不論是否已有其他 xlsx 庫。

C. **只用標準庫**（zipfile+xml）自幹 XLSX 讀取，零新依賴。

X) Other

[Answer]: A. 沿用既有依賴；若無則加 openpyxl（目前 requirements 無 xlsx 庫，tech-stack 將釘 openpyxl）。 <!-- 2026-09-18T17:32Z -->

---

### Question 6
**NFR7／可測試性 — 本 unit 對 TCMS 的義務邊界？**

A. **本 NFR 只要求**：code-gen 產出的自動化測試須能被 `unittest discover` 撿到，且之後 `tcms-test-cases` stage 會覆蓋；本 stage **不**手寫 TCMS markdown。**（建議）**

B. **本 stage 就要**產出 TCMS 手動案例草稿（與 tcms stage 重複，不建議）。

X) Other

[Answer]: A. 本 stage 不手寫 TCMS；自動化進 unittest discover，tcms-test-cases stage 再覆蓋。 <!-- 2026-09-18T17:32Z -->

---

## Consolidated Summary Confirmation

- **Q1=A**：解析資源雙上限——列數 ≤ 50_000，且 CSV／解壓後字元或 cell 總量等價 ≤ 32 MiB；超出回傳 ambiguous／空 lines，不 raise。
- **Q2=A**：公開 API 例外訊息不得含本機絕對路徑或 traceback；回傳結構不含堆疊。
- **Q3=A**：PBT 至少三條 Hypothesis 性質（同入同出、禁 import 副作用、BR4／對帳 deterministic）；細節 code-gen 展開。
- **Q4=A**：`validate_cost_calculator_boundary.py` 掃 `estimate_parser.py`、`estimate_validator.py` 及 parser 直接 import 的讀取器。
- **Q5=A**：XLSX 沿用既有依賴；目前無則新增 **openpyxl** 並記入 tech-stack。
- **Q6=A**：本 NFR 不產 TCMS 手寫案；自動化進 discover，義務歸 `tcms-test-cases`。

若正確請回覆 **Looks correct**（或指出要改之處）。

[Answer]: Looks correct <!-- 2026-09-18T17:38Z -->

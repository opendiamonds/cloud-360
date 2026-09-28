# NFR Requirements — 釐清問題（credential-pipeline）

> Unit: `credential-pipeline`（U4／B3）· kind: **packaging**  
> Stage: nfr-requirements · 適用產物：security-requirements、tech-stack-decisions、traceability  
> 作答：在每題 `[Answer]:` 後填選項字母（例如 `A`）。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 平台統一一組憑證；GitHub Secrets → `render-env.sh` → `deploy/.env`；不採每使用者自帶 | FR5.8、FR11.1 |
| 變數名沿用既有：`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_DEFAULT_REGION`、`GCP_BILLING_API_KEY` | `backend/.env.example`、`deploy/.env.example` |
| Azure Retail 不需憑證 | FR5.6 |
| 憑證缺席須可啟動；查價降級屬 U5（FR5.10） | FR11.4 |
| 憑證不得進版控／日誌／錯誤訊息；IAM 最小權限（`pricing:GetProducts` 等） | NFR9、FR5.9、ADR-0006 |
| 帳單／用量類 API 仍禁 | FR5.7、ADR-0018 預期範圍 |
| **ADR-0018 未成文前不得實作** FR11／FR5.6 IAM 路徑 | FR11 阻擋前提、OQ6 |
| 無新執行期語言／框架；本 unit 只動 deploy／CI／文件 | unit-of-work U4、technology-stack |

---

## Questions

### Question 1
**FR11.2／OQ7 — `FORBIDDEN_CONTENT_PATTERNS` 怎麼改？**  
現況：任一受版控檔出現字串 `AWS_SECRET_ACCESS_KEY`（變數名也算）即失敗，會擋住 FR11.1 在範本／腳本裡寫變數名。

A. **值樣式偵測**：拿掉對變數名的字串禁令；改攔「像真金鑰」的賦值（例如 `AWS_SECRET_ACCESS_KEY=` 後面接非空白的疑似密鑰；`BEGIN PRIVATE KEY` 維持）。範本可寫空值或註解變數名。**（建議）**

B. **路徑白名單**：維持字串禁令，但對 `backend/.env.example`、`deploy/.env.example`、`deploy/render-env.sh`、`DEPLOY.md`、`LOCAL-DEV.md` 等明確清單放行變數名；其餘檔仍全攔。

C. **混合**：變數名在白名單路徑放行；其餘路徑改用值樣式偵測。

X) Other（請在 `[Answer]:` 後說明）

[Answer]: A

---

### Question 2
**CI／test compose 的憑證姿態？**（FR11.4：無憑證可啟動）

A. **永遠空白**：`docker-compose.test.yml` 與 CI 不注入 AWS／GCP 密鑰；查價路徑在測試中靠 stub／略過（U5）。**（建議）**

B. **可選假值**：test compose 允許寫入明顯假值（如 `test-not-a-real-key`），僅供「有變數但非真憑證」的分支測試；仍禁止真金鑰。

X) Other

[Answer]: A

---

### Question 3
**日誌與錯誤訊息的紅線（NFR9 落地）？**

A. **機械禁令**：本 unit 的文件與 contract 測試須載明——任何 log／HTTP detail／traceback 不得出現 secret 值；變數名可出現。執行期遮罩屬 U5，本 unit 只訂契約與文件。**（建議）**

B. **本 unit 另加 CI grep**：除 repo contract 外，新增對 `deploy/`／workflow 變更的掃描，禁止在腳本 echo／`set -x` 打印密鑰變數。

X) Other

[Answer]: A

---

### Question 4
**Tech stack — 本 packaging unit 的工具邊界？**

A. **零新依賴**：只改 GitHub Actions secrets 對應、`render-env.sh`、compose、兩支 validate 腳本、`DEPLOY.md`／`LOCAL-DEV.md`；不引入 Vault／外部 secret manager。**（建議）**

B. **引入外部 secret manager**（需另開 ADR；超出現行 FR11）。

X) Other

[Answer]: A

---

### Question 5
**ADR-0018 與本 unit code-generation 的順序？**（FR11 阻擋前提）

A. **本 unit 的 code-generation 開頭先寫 ADR-0018**（取代 `project.md`／`team.md`／ADR-0017 §8 相關句），通過後才改 deploy／contract。**（建議）**

B. **另開 docs／chore 先合併 ADR-0018**，本 unit 假定 ADR 已在 `ut` 上才開始改檔。

X) Other

[Answer]: A

---

## Consolidated Summary Confirmation

**U4 `credential-pipeline` NFR 定案**

| 項 | 定案 |
|---|---|
| FR11.2 contract | 值樣式偵測：放行變數名，攔疑似真金鑰賦值；`BEGIN PRIVATE KEY` 維持（Q1=A） |
| CI／test | 永不注入 AWS／GCP 密鑰；查價靠 stub／略過（Q2=A） |
| 日誌紅線 | 文件＋contract 訂「secret 值禁現」；執行期遮罩歸 U5（Q3=A） |
| Tech stack | 零新依賴：Secrets → `render-env.sh` → compose；無 Vault（Q4=A） |
| ADR-0018 | 本 unit code-gen **開頭先寫** ADR-0018，再改 deploy／contract（Q5=A） |

**將產出**（packaging）：`security-requirements.md`、`tech-stack-decisions.md`、`traceability.json`。

**後果**：實作前仍受 FR11 阻擋前提約束——ADR-0018 未成文不得改 IAM／憑證傳遞；本站只鎖定 NFR 與落地策略。

[Answer]: Looks correct

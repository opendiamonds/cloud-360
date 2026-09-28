# NFR Requirements — 釐清問題（legacy-cost-retirement）

> Unit: `legacy-cost-retirement`（U3）· kind: **service**（退場）  
> Stage: nfr-requirements · 適用產物：security-requirements、reliability-requirements、tech-stack-decisions、traceability  
> （performance／scalability／observability 對「純刪除＋rename」多為 N/A 或薄記載）  
> 作答：在每題 `[Answer]:` 後填選項字母（例如 `A`）。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 舊 HTTP 整包移除；不新增 `/api/cost/v1` stub | FD Q2=A、BR9.1 |
| 四表改名 `archive_*`，保留 ≥90 天再 DROP | FD Q3=C、BR9.2 |
| 刪 Calculator＋Python `playwright`；前端 e2e Playwright 保留 | FD Q4=A、BR9.3 |
| U5 最小存活集不得刪 | FD Q5=A、BR9.4 |
| 合併／部署須與 U8 同批 | FD Q1=A、BR9.5 |
| 舊 cost e2e 刪／改；U8 補新 | FD Q6=A、BR9.6 |
| FR9.6 邊界腳本屬 U1，不得回退 | BR9.8 |
| NFR1 端到端時窗、NFR2 進度 UI、NFR5 稽核非本 unit 獨責 | requirements／U2／U7／U8 |

---

## Questions

### Question 1
**archive_* 表在保留期的存取控制？**（安全）

A. **應用程式碼零讀寫**；僅 DBA／維運經受控連線查詢。API／ORM 不得再映射 `archive_*`。**（建議）**

B. 提供唯讀內部 admin API 查 archive（需 Platform_Admin）。

C. 與 live 表相同的應用權限（不建議）。

X) Other

[Answer]: A — 應用零讀寫 archive_*；僅維運受控查詢
---

### Question 2
**schema 遷移技術怎麼釘？**（tech-stack）

A. **沿用現有雙軌**：`database.py::_ensure_cost_schema` 啟動補丁＋`schema_rbac.sql` 更新；rename 用 `ALTER TABLE ... RENAME TO archive_*`（或等價）。**不**新引入 Alembic。**（建議；brownfield）**

B. 本 unit 引入 Alembic 專管這次 rename／後續 DROP。

C. 只改 `schema_rbac.sql`，啟動補丁不管 rename（依賴人工跑 SQL）。

X) Other

[Answer]: A — 雙軌 database.py＋schema_rbac.sql；不引入 Alembic
---

### Question 3
**與 U8 同批部署的可靠性閘門怎麼驗？**（reliability）

A. **程序閘門**：code-gen／PR 檢查清單＋人工確認同 squash；CI 不強制機械偵測 U8 檔案。**（建議）**

B. **機械閘門**：CI 檢查同一 PR 必須同時變更 U3 退場路徑與 U8 UI 路徑（路徑清單寫死），否則失敗。

C. 不設閘門，只靠文件提醒。

X) Other

[Answer]: A — 程序閘門（檢查清單＋人工同 squash）；CI 不機械偵測 U8
---

### Question 4
**退場後舊環境變數（如 `COST_PRICING_STUB`）怎麼處理？**（與 FR9.8「減」側／U4 協調）

A. **本 unit 刪除讀取點與範本中的舊 C1 stub／calculator 相關變數**；目錄價憑證變數（U4 已加）保留。`validate_env_contract` 必須仍綠。**（建議）**

B. 變數留在範本但程式忽略（避免 env contract 大改）。

C. 全部交給 U4／U8，本 unit 不動 env 檔。

X) Other

[Answer]: A — 刪舊 stub／calculator 變數讀取與範本；保留 U4 目錄價憑證
---

### Question 5
**保留期到期後的 DROP 誰做？**（operation 邊界）

A. **本 unit 只做到 rename＋`DEPLOY.md` 記到期日**；90 天後另開 chore／operation 任務 DROP。**（建議）**

B. 本 unit code-gen 就寫好「到期自動 DROP」的啟動補丁（到日即刪）。

C. 本 unit 合併後立刻 DROP archive（否定 Q3=C）。

X) Other

[Answer]: A — 本 unit 只 rename＋記到期；DROP 另開 chore／operation
---

### Question 6
**本 stage 是否產出 TCMS 手寫測案？**（NFR7）

A. **否**——歸後續 `tcms-test-cases`；本 unit 以 unittest／contract／（必要時）e2e 刪改滿足可測試性。**（建議；與 U1／U6 Q6=A 一致）**

B. **是**——本 stage 另寫 TCMS 草稿（退場回歸）。

X) Other

[Answer]: A — 本 stage 不寫 TCMS；歸 tcms-test-cases
---

## Consolidated Summary Confirmation

**U3 `legacy-cost-retirement` NFR 定案**

| 項 | 定案 |
|---|---|
| archive 存取 | 應用零讀寫；僅維運（Q1=A） |
| 遷移技術 | 雙軌 database.py＋schema_rbac.sql；無 Alembic（Q2=A） |
| U8 同批 | 程序閘門＋人工確認（Q3=A） |
| 舊 env | 刪 stub／calculator 變數；留 U4 憑證（Q4=A） |
| DROP | 另開 chore；本 unit 只 rename＋到期日（Q5=A） |
| TCMS | 本 stage 不手寫（Q6=A） |

**將產出**：security-requirements.md、reliability-requirements.md、tech-stack-decisions.md、traceability.json（performance／scalability／observability 標 N/A）。

**後果**：code-gen 不得映射 archive_*；DEPLOY 記 90 天到期；PR 檢查清單含 U8 同批。

[Answer]: Looks correct
請回覆 **Looks correct**（或指出要改的地方）。

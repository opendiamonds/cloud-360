# Code Generation 問題檔 — `U6 embedding-port`

> Stage：`code-generation`（3.5）　Unit：`U6 embedding-port`（`library`，M）
> 建立時間：2026-10-05
>
> 本站只有一個關卡：**Plan Approval**。它涵蓋三份內容——
> `code-generation-plan.md`、其中逐字貼入的 Testing Contract、
> 以及 `unit-test-instructions.md`。

---

## Plan Approval

**核可範圍**：

| 檔 | 內容 |
|---|---|
| `code-generation-plan.md` | 11 個實作步驟、四個刻意省略的 `plan_profile` 層及其理由、故事↔步驟追溯、ADR-0006 四面向落點、**9 項突變驗證** |
| 其中的 Testing Contract | methodology `test-after`、strategy `standard`、`contract_sha256: sha256:1f0b6822601f52ff3e71a9bd20a949c9e106f87999f78c986398d5e1963f2f77` |
| `unit-test-instructions.md` | 一支新測試檔、**16 個測試**、精確的 unit-scoped 指令、覆蓋範圍的誠實說明 |

**實際會改動的十個檔**（計畫 §〇）：

1. `backend/services/embedding_port.py` — **新**
2. `backend/tests/test_embedding_port.py` — **新**
3. `backend/main.py` — startup hook 加一行
4. `backend/.env.example` — `EMBEDDING_TIMEOUT_SEC`
5. `deploy/.env.example` — 同上
6. `deploy/render-env.sh` — 寫出該變數
7. `deploy/docker-compose.deploy.yml` — 無 fallback 形式傳入
8. `scripts/validate_embedding_provider_value.py` — **新**（`H-I3`）
9. `.github/workflows/ci.yml` — `repo-contract` job 加一個 step
10. `LOCAL-DEV.md` — **兩項**

**核可時請一併知道這四件事**：

- **測試數 16 高於 `standard` 的「每元件 5–8」。** 這是刻意的，且 Testing Contract
  的 `combination_rule` 明文允許。六個是 ADR-0006 **PBT hard constraint** 的已核可
  性質（`P1`–`P6`，`functional-design` 定的，不是本站選的），其餘十個是
  `SEC-*`／`NFR7.1`／`D-4`／`D-7` 各自明文要求的可驗證方式。**壓到 8 個就得砍掉
  已核可的驗證要求——那是放寬門檻。**

- **第 7、8、9 項是 `infrastructure-design` 審查後才長出來的。** 原本 `[Q2]`=A
  只改一個設定檔；審查 `R-01`（Critical）查出它與已核可的 `NFR8.1` 逐字矛盾，
  反轉後變四個設定檔。第 8、9 項則來自審查 `R-04`：原本「接受」的那個部署期
  安全缺口改為**關閉**，做法是 CI **import 本單元的驗證函式**（不複製允許值清單）。

- **`backend/requirements.txt` 淨變更為零**，這是 `tech-stack-decisions.md` 已核可的
  約束，不是巧合——`[Q4]`=A（`fastembed` 選用、lazy import）與 `BR6.2`（`ollama`
  只用既有 `httpx`）兩個決定都指向它。

- **CI 只跑得到三個實作中的 `stub`。** `docker-compose.test.yml:18` 逐字「NO ollama」，
  `fastembed` 不在 `requirements.txt`。真正測不到的只有「`ollama`／`fastembed`
  實際回傳的向量是否真為 1024 維」，它在首次真實呼叫時由執行期斷言攔下。
  **這是具名缺口，不是豁免**（`OQ-E2`、`cicd-pipeline.md §三`）。

**跨單元的未決項**（不在本計畫範圍，核可後仍然存在）：
`H-N1`（`embed` 延遲的自動化斷言 → `build-and-test`）、
`H-N2`（telemetry 基礎設施 → `observability-setup`，**CONDITIONAL**）、
`H-I2`（ollama 容器配額的實測 → `U1`／operation）、
`RR-1`–`RR-4`（四項具名殘餘風險）。

[Approval Fingerprint]: sha256:v3:8eac99db7e4fd01954da6b2c245a1d6ebfe4ee56b35c668b6b5eea9ed2f7189d
[Planned Source]: 464fbc0e7b51a30d29a210cdb8d1d689fa50029c1ad9d9b774aaa59ce6586652

- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan

[Answer]: Approve Plan

# 安全需求 — `U7 hierarchy-service`

> **本檔刻意精簡，且不重述已核可的內容。** 本單元的安全需求**已在
> `functional-design` 落地**，落點比本站更正確——授權是**行為規則**，寫在規則層
> 才會被實作與測試引用。本檔的作用是把那些規則對應回 NFR 的分類，
> 並指出本站**沒有**新增任何需求。
>
> 依 `project.md`「CONDITIONAL stage 的適用性判定必須逐項對照 condition 條款並把
> 判定理由記入 stage diary」，逐項判定已記於
> `construction/functional-design/memory.md` 的 `## Interpretations`。

## 一、本單元的安全需求落在哪裡（不在本檔）

| 安全面 | 承載處 | 條數 |
|---|---|---|
| 授權判定的唯一入口與禁繞過 | `rules.md` `BR1.1`–`BR1.5` | 5 |
| 讀取的列可見範圍 | `rules.md` `BR6.1`／`BR6.2`／`BR6.3` | 3 |
| 判定支援型查詢的三道替代約束 | `rules.md` `BR6.4` | 1 |
| 寫入面的擁有者檢查 | `rules.md` `BR6.5` | 1 |
| 衝突型拒絕的承載（含 409 顯式宣告） | `rules.md` `BR6.6` | 1 |
| 變更紀錄的行為者溯源 | `rules.md` `BR5.6` | 1 |
| ADR-0006 四面向逐項判定 | `functional-spec.md` §七之三 | 4 面向 |

合計 **12 條**安全相關規則 ＋ 一張四面向判定表。**本站不新增、不改寫、不複寫**
——複寫會製造第二份真實來源，而 `team.md` 的「單一真實來源」規則禁止在無鎖住
一致性的測試時新增副本。

## 二、ADR-0006 四面向：本站的增量為零

四面向的逐項判定在 `functional-spec.md` §七之三，本站複查後**無新增**：

- **IAM**：適用且已查出兩處實質缺口（`BR6.1` 的列層範圍、`BR6.5` 的寫入面），
  兩者皆已成為規則。
- **Encryption**：本單元不適用（無新儲存體、無新機敏欄位、無新傳輸通道、
  無憑證／token／金鑰）。上游 `unit-of-work.md:248` 判「適用」，其落點為
  `U5 memory-data`（`OQ-3`）與 `U1 brain-infra`（連線憑證）——**差異來自範圍**。
- **Network exposure**：適用但**不新增任何進程邊界或監聽埠**；五個 HTTP path
  全走既有 FastAPI router 與既有認證層。`unit-of-work.md:249` 逐字把
  `U13 brain-gateway` 的新 WebSocket 稱為「本 intent **唯一**新增的對外網路面」。
- **Audit logging**：適用，且已查出三項減損（級聯刪除、90 天保存期且清除機制
  不在本 repo、來源欄位只容納大腦編排一條路徑）。

## 三、本站唯一的新增內容：測試義務的彙整

安全規則若沒有可執行的驗證就只是文字。下列義務為 `team.md` 的 A＋B 規則與
`project.md` 的交叉要求，**驗證落點全部在本單元的 `code-generation`**：

1. **allow/deny 雙向 `TestClient`**：具 `K2` → 2xx、無 `K2` → 403，缺一不可。
2. **列範圍斷言**（`BR6.1`）：他人的列不得出現在任何列舉回應中。
3. **寫入面斷言**（`BR6.5`）：以他人的專案為目標建立系統／刪除，必須被拒。
4. **`BR6.4` 的最小欄位斷言**：判定支援型查詢不得回傳名稱或可列舉的集合。
5. **409 顯式宣告**（`BR6.6`）：`responses={409: {...}}` ＋ 重 dump
   `openapi.json`，否則 CI 保持綠燈而契約不進 spec。

## 四、本單元真正存在的 NFR（可驗證，給 id 以便被測試引用）

**上一版把本站寫成「增量為零」，那句話太快了。** 授權的*行為*確實已在
`functional-design` 落地（12 條規則），但下列四項是**非功能性**的、
有二元判準的、且目前沒有任何規則承載的義務。給它們 id 才能被測試引用。

| id | 專精的 intent NFR | 需求 | 二元判準 |
|---|---|---|---|
| **`NFR5.1`** | `NFR5`（契約閘門） | 第五個 path（`/api/hierarchy/diagram-changes`）落地後，`openapi.json` 必須含該 path | `backend/scripts/dump_openapi.py --check` 綠燈，且 `openapi.json` 的 paths 含該字串 |
| **`NFR5.2`** | `NFR5`（契約閘門） | 四條衝突型規則要求的 409 必須**顯式**宣告 `responses={409: {...}}` | `openapi.json` 中該 operation 的 responses 含 `409`。**沒有這一項則契約不進 spec、前端產不出型別，而 CI 保持綠燈**——`unit-of-work.md:447` 逐字「非 2xx/422 的宣告數為 0」 |
| **`NFR7.1`** | `NFR7`（保存與刪除稽核） | 變更紀錄的查詢回應不得被呈現為完整變更歷史 | 回應（或其 schema 描述）須表達涵蓋範圍由 `source` 宣告。`U4` 註解逐字（`schema_rbac.sql:416`／`:418`）「read source before presenting anything」、「rows here are **NOT** a complete change history」 |
| **`NFR8.1`** | `NFR8`（部署設定完整性） | 本單元不得新增任何部署設定 | `python3 scripts/validate_env_contract.py` 綠燈，且本單元的 diff 不含 `deploy/`、`render-env.sh`、任一 `.env.example` 的改動 |

四項的**驗證落點全部在本單元的 `code-generation`**，與 §三 的五項測試義務同一批。

## 五、未決項（不在本站關閉）

`OPEN-H10`（`BR6.4` 三道約束有兩項本單元無法自驗）、`OPEN-H12`（`OQ-H1`
擁有者被刪／停用時專案的去向，明寫退回並指派 `U19`）。
兩者皆登錄於 `functional-design/traceability.json`，本站不重複登錄。

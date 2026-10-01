# ADR 0018: 解禁需帳號憑證的**目錄價**端點，維持帳單與用量類 API 的全面禁令

- Status: Accepted
- Date: 2026-09-16（建立於 2026-09-16T11:00:40Z，讀自 `date -u`）
- 節數：**7**
- Amends: **ADR-0017** 的 §3 與 §8（憑證子句）；**`aidlc/spaces/default/memory/project.md`** 第 81 行與第 85 行；**`aidlc/spaces/default/memory/team.md`** 第 198 行。原文皆保留，本 ADR 只限定其適用範圍並指向本檔。
- Invokes: **ADR-0001** `## Guardrails` 的明示出口條款（見 §3）。ADR-0001 本身**不需修訂**。
- 觸發來源：intent `260916-estimate-upload-rework` 的 requirements-analysis 階段，使用者於摘要確認環節提出「我想改成要呼叫三朵雲各自的 api，可以是需要帳號的」（問答檔 F4）。
- 下游依據：`requirements.md` 的 FR5.6、FR5.7、FR5.9、FR9.4、FR11 全節、NFR9、C3、OQ6、OQ7。

## Context

ADR-0017 於 2026-09-16 同日經兩次修訂後，停在這個位置：估價一律來自使用者上傳的官方估價表；agent 得呼叫**公開免帳號**的價目端點確認現價，所得價格只寫入建議文字；需要雲端帳號憑證的端點——含走 IAM 的 boto3 Pricing Query API——全面禁止。

約 3.5 小時後，requirements-analysis 的摘要確認環節推翻了最後那一句。

**使用者的原始表述涵蓋面比最終定案大。**「呼叫三朵雲各自的 api，可以是需要帳號的」字面上包含 AWS Cost Explorer、Azure Cost Management、GCP Billing Export——這些回傳的是真實帳戶的消費與已談定折扣，準確度確實遠高於目錄價。若照字面實作，本 repo 將持有可讀取真實帳單的憑證，ADR-0001 的範圍邊界會被實質推翻。

因此在裁決前先把「需帳號的 API」拆成兩類請使用者選擇，結果收斂到只解禁第一類：

| 類別 | 代表端點 | 回傳內容 | 憑證能讀到什麼 | 本 ADR 處置 |
|---|---|---|---|---|
| **目錄價類** | AWS Price List Query API、GCP Cloud Billing Catalog API | 公開牌價，與免帳號的 Bulk／Retail 端點**同一份資料** | 什麼都讀不到；`pricing:GetProducts` 不觸及任何帳戶資源 | **解禁**（§1） |
| **帳單與用量類** | AWS Cost Explorer、Azure Cost Management、GCP Billing Export | 真實消費、用量、已談定折扣 | 整個帳戶的財務狀況 | **維持全面禁止**（§2） |

這個區分是本 ADR 全部論證的基礎。沒有它，就只剩下「想要更準的價格」這種無法劃界的理由。

## Decision

### 1. 目錄價類端點：解禁，允許使用帳號憑證

`pricing_client` 得對接下列端點：

| 雲 | 端點 | 憑證 | 備註 |
|---|---|---|---|
| AWS | Price List **Query** API（boto3 `pricing` client） | IAM | 既有的公開 Bulk Price List 亦繼續可用，兩者並存 |
| GCP | Cloud Billing **Catalog** API | API key（`GCP_BILLING_API_KEY`） | ADR-0017 §8 原已判定 API key 不觸犯「免帳號」要求，本節將其升格為明文允許 |
| Azure | Retail Prices API | **不需憑證** | 本即公開。Azure 在本次解禁中**沒有變化**——這點常被誤讀為三雲一致解禁 |

**`pricing_sdk.py` 與 `boto3` 相依由「確定刪除」改為「保留」。** ADR-0017 §8 明文寫「可確定刪除的是 `pricing_sdk.py`：它是 boto3 IAM 路徑，本節明文仍禁」——該句**撤回**。連帶保留 `pricing_query_parser.py`（`pricing_sdk` 的解析相依）、`tests/test_pricing_sdk.py`，以及 `pricing_client.py:20` 與 `:280-283` 的 `use_sdk_enabled()` 分支。

### 2. 帳單與用量類端點：維持全面禁止

AWS Cost Explorer、AWS Cost and Usage Report、Azure Cost Management、GCP Billing Export 及同類 API **一律禁止**，本 ADR 不解除此禁令。

這條不是順帶保留的殘留條款，而是 §1 能夠成立的**對價**。§1 的論證是「該憑證讀不到帳戶內任何東西」；一旦允許帳單類端點，該論證立即失效，§1 必須連同重審。

### 3. 與 ADR-0001 的關係：援引其明示出口，不修訂

ADR-0001 的 `## Guardrails` 原文為：

> The repository must not introduce the following without a future explicit ADR and approval:
> - Plaintext cloud credentials or secrets.
> - ...
> - Unreviewed IAM/RBAC, firewall, KMS, storage policy or production-impacting changes.

**ADR-0001 預留了這個出口。** 它禁止的是「未經明示 ADR 與核可」就引入憑證，不是無條件禁止。本 ADR 即為該出口所要求的 explicit ADR，使用者的核可構成 approval，§4 的最小權限設計構成 IAM 變更的 review。

因此 **ADR-0001 不需修訂**。requirements-analysis 的 OQ6 曾提出「若唯讀 IAM 使用者落入 production credentials 範圍，ADR-0001 亦須修訂」——該疑慮**經查證不成立**，本節結案。

需注意 ADR-0001 禁止的是 **plaintext** credentials；§5 的管線把憑證存於 GitHub Secrets 並在部署時 render 到未受版控的 `deploy/.env`，不落入版控，符合此限定。

### 4. 最小權限

- **AWS**：IAM 主體僅授與 Price List Query API 所需動作（`pricing:GetProducts`、`pricing:DescribeServices`、`pricing:GetAttributeValues`）。**不得**包含任何帳戶資源讀取權、`ce:*`、`cur:*` 或 `budgets:*`。
- **GCP**：API key 須以 API 限制綁定 Cloud Billing API，不得為無限制金鑰。
- 憑證不得出現於版控、日誌或錯誤訊息（`requirements.md` NFR9）。
- 憑證缺漏或呼叫失敗時，查價降級回公開端點或略過，不得使建議產生流程失敗（FR5.10）。本 repo 的本機開發**不得**被迫持有雲端憑證（FR11.4）。

### 5. 憑證管線：重建本 session 稍早移除的部分

commit `aa2daec`（2026-09-16）移除了整條 AWS 憑證傳遞管線，理由是它在當時違反 `project.md` 與 ADR-0001。**該 commit 在其時點是正確的**，本 ADR 不否定它；本節是在新依據成立後重建，且範圍更窄。

| 面向 | `aa2daec` 移除前 | 本 ADR 重建後 |
|---|---|---|
| IAM 權限範圍 | 未限定 | 僅 §4 列舉的三個 pricing 動作 |
| 用途 | `COST_PRICING_USE_SDK` 控制的取價主路徑之一 | 僅供 agent 按需查價（ADR-0017 §8 的四條界線不變） |
| 可否產生估價 | 可 | **不可**。估價仍只來自上傳的估價表 |

重建涉及 `.github/workflows/deploy.yml`、`deploy/render-env.sh`、`deploy/docker-compose.deploy.yml`，以及 `DEPLOY.md`、`LOCAL-DEV.md` 的同步說明（`project.md` 的 schema↔deploy 同步為 blocking 規則）。

### 6. `validate_repo_contract.py` 的禁用字串比對須調整

`scripts/validate_repo_contract.py` 先前以字串比對攔截 `AWS_SECRET_ACCESS_KEY`，**不分變數名引用與實際金鑰值**。§5 的重建會讓 `deploy/render-env.sh` 再次出現該變數名，CI 立刻紅燈。

**定案手法（NFR Q1=A／credential-pipeline code-gen；關閉 OQ7）**：自 `FORBIDDEN_CONTENT_PATTERNS` **移除**對變數名的裸字串攔截；改以賦值右端值樣式掃描所有受版控文字檔：

| 標籤 | Regex |
|---|---|
| AWS secret | `AWS_SECRET_ACCESS_KEY\s*=\s*([A-Za-z0-9/+=]{40})` |
| GCP Catalog key | `GCP_BILLING_API_KEY\s*=\s*(AIza[0-9A-Za-z\-_]{35})` |

`BEGIN PRIVATE KEY` 字串禁令維持。空值、註解變數名、shell `${AWS_SECRET_ACCESS_KEY:-}` **通過**。驗證見 `backend/tests/test_repo_contract_secret_patterns.py`。

**放寬一道安全閘門本身是高風險動作。** 調整後必須以實際金鑰樣式的測試資料驗證它仍會攔下真正的外洩，不得只驗證「CI 變綠」。

### 7. ADR-0017 受影響條文的逐條處置

| ADR-0017 位置 | 原文要旨 | 本 ADR 處置 |
|---|---|---|
| §3（首版） | 不得新增任何自動取價路徑 | 已由 §8 改述，本 ADR 不再變動 |
| §8 憑證子句 | 「只准公開免帳號端點。走 IAM 的 boto3 Pricing Query API 仍然禁止」 | **撤回**，改為 §1 |
| §8 退場清單 | 「可確定刪除的是 `pricing_sdk.py`」 | **撤回**，改為保留 |
| §8 假設段 | GCP API key 不觸犯「免帳號」要求，惟未經審查 | **升格為明文允許**（§1），疑慮消解 |
| §8 四條界線 | agent 專用、按需非逐列、只寫建議文字、不回寫明細 | **原樣有效**，本 ADR 只改「端點可否用憑證」，不改使用方式 |
| §2 三層形狀與 PBT 落點 | 純函式解析器 | **不受影響** |
| §1 `pricing_client` 恢復效力 | — | **不受影響**，本 ADR 只擴大其可對接的端點集合 |

## Consequences

**正面**：AWS 與 GCP 的查價實作可直接沿用既有的 `pricing_sdk` 與 `GCP_BILLING_API_KEY` 路徑，不需重寫；`requirements.md` 的 FR5.6／FR9.4／FR11 解除阻擋前提，domain-design 可以開始。

**負面**：本 repo 自此持有雲端憑證，這是 2026-08-19 以來刻意避免的狀態。即使權限窄到讀不到帳戶資源，憑證管理、輪替與外洩應變都成為必須維護的事項，而本專案沒有既有的憑證輪替機制。

**負面**：`aa2daec` 移除、本 ADR 重建，同一條管線在同一天內來回一次。git 歷史上會呈現反覆。兩者的範圍確實不同（§5 的表），但這個差異只存在於文件，不存在於 diff 的形狀——未來讀 git log 的人需要讀到本節才能理解。

**殘餘風險**：§6 放寬安全閘門是本 ADR 風險最高的一步。`FORBIDDEN_CONTENT_PATTERNS` 的字串比對雖然粗糙，但它是**零漏報**的——任何寫法都攔得住。改成樣式偵測後會出現漏報空間。這個交換是為了讓 §5 可行，但它保護的範圍（整個 repo 的金鑰外洩）遠大於它服務的目的（一條查價管線）。

**殘餘風險**：§1 與 §2 的界線靠人維持。boto3 的 `pricing` client 與 `ce` client 在程式碼形狀上只差一個字串，IAM policy 是唯一的機械防線——這也是 §4 要求明確列舉動作而非用萬用字元的原因。

## Alternatives Considered

**A. 照使用者字面全面解禁，含 Cost Explorer。** 否決：那會讓 repo 持有可讀真實帳單的憑證，ADR-0001 的範圍邊界被實質推翻，且「取得實際帳單」會反過來削弱本 intent「請使用者上傳估價表」的前提——若系統讀得到帳單，上傳就是多餘的。這個矛盾在裁決前已向使用者提出。

**B. 維持公開免帳號端點不變（ADR-0017 §8 原狀）。** 否決：使用者明確要求變更。且 GCP Cloud Billing Catalog 本就需要 API key，ADR-0017 §8 是靠「API key 不算帳號憑證」這個未經審查的判定勉強容納它——該判定在本 ADR 被正式化，不再是灰色地帶。

**C. 保留禁令，改以「需要時再請使用者貼上價格」繞過。** 否決：把機器可以自動完成的事推給使用者，與本 intent「縮短從上傳到建議的時間」的成功指標（3 分鐘目標）直接衝突。

**D. 不改 `validate_repo_contract.py`，改用不含 `AWS_SECRET_ACCESS_KEY` 字樣的變數名。** 否決：boto3 讀取的環境變數名是固定的，改名需在應用層轉譯，為了繞過檢查而增加一層間接是壞的交換。且這會讓掃描器產生虛假的安全感——它以為 repo 裡沒有 AWS 憑證，實際上有。

## 對應的規則層編輯

本 ADR 生效時，下列三處就地加註限定，**原文保留不刪**：

1. `project.md:81` — 追加「**ADR-0018 §1 解禁**：目錄價類端點（AWS Price List Query API、GCP Cloud Billing Catalog API）得使用帳號憑證；帳單與用量類（Cost Explorer、Cost Management、Billing Export）**維持全面禁止**（§2）」
2. `project.md:85` — 追加「`pricing_client` 可對接的端點集合由 ADR-0018 §1 擴大，`httpx` 不得直打的規定不變」
3. `team.md:198` — 同第 1、2 項

## Assumptions & Open Questions

- [assumption] 假設 AWS Price List Query API 回傳的目錄價與公開 Bulk Price List 一致。兩者同為 AWS 官方牌價來源，但本 ADR 未實測比對。若不一致，需決定以何者為準。
- [assumption] 假設 `pricing:GetProducts` 等動作確實無法觸及帳戶資源。此判定依 AWS IAM 文件，未經實際的權限邊界測試。§4 的動作列舉是防線，但若 AWS 日後擴大該動作的語意，防線會失效而無人察覺。
- [assumption] 假設平台統一一組憑證足夠。若日後需要按使用者或按租戶區分查價來源，本 ADR 的 §5 管線設計需重做。
- [closed] §6 的 `FORBIDDEN_CONTENT_PATTERNS` 具體調整手法已定（原 `requirements.md` OQ7）：值樣式 regex 見 §6；NFR Q1=A；實作於 credential-pipeline code-generation。
- [open] 憑證輪替機制不存在。本 ADR 引入憑證但未規定輪替週期與流程，這是新增的運維義務，歸屬階段未指派。
- [open] `requirements.md` OQ8：§5 與 §6 的工作量是與上傳解析主線平行的一批，其在 value-first 排序中的插入位置留給 delivery-planning。

## 後補：規格描述查詢（FR13，2026-09-26）

§1 解禁的目錄價端點，除供 `pricing_client.fetch_hourly` 給建議文字取價外，亦允許 `cost/sku_catalog.py` 只取 SKU 的人類可讀描述並寫入 `spec_description`。**價格仍不得回寫明細金額欄**（AH-6）。intake 寫入路徑不得 import `pricing_client`／`pricing_sdk`。帳單與用量類 API 的全面禁令（§2）不變。

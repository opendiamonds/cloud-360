## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `inception/contract-design/contract-summary.md` § K-16 `existing_endpoint_extension.preserved_existing_protections.guards` | 上一輪指出兩道既有守門的行號皆錯（`:651`／`:668-671`，實為 `:645`／`:667`）。本輪以 `grep -n 'target_user.id == admin_user.id and not request.is_active:\|if admin_edit_count <= 1'` 直接對 `backend/services/user_router.py` 取值，實得 **645**（條件判斷）與 **667**（條件判斷）；契約現文正確改為 `:645-646`（`:645` 條件、`:646` raise）與 `:667-671`（`:667` 條件、`:668-670` raise 本體、`:671` 收尾括號），逐行核對相符。`line_number_correction_history` 區塊誠實記載第一版「切片序號回推多算 6 行」與「只引到 raise 本體排除條件判斷」兩個錯因，且明寫「重新核對也會錯」本身是可信度依據，未美化 | （已修正，無待辦） | Resolved |
| R-02 | Major | `inception/contract-design/contract-summary.md`：`## 修訂 1 的 ADR-0006 四面向逐項判定` 小節開頭、X-04 `process_boundary.exposure` 引用處 | 上一輪指出兩處 `requirements.md` 行號皆錯（`:617`／`:614`，應為 `:622`／`:619`）。逐行核對 `requirements.md`：第 622 行逐字為「**四面向皆適用，無不適用項。**」（修訂 1 四面向表之後、獨立成段），第 619 行逐字為「…它**不得對外暴露**，僅供同主機的大腦進程連接…」（Network exposure 列）。契約現文兩處均已改為 `:622`／`:619`，與原文逐字相符。檔內仍殘留的 `requirements.md:617`／`:614` 字串僅出現在自檢 3 敘述句與處置表（「`requirements.md:617` → **`:622`**」）裡，用於描述舊錯誤本身，是歷史敘事而非存活引用，已逐一確認無第三處活引用 | （已修正，無待辦） | Resolved |
| R-03 | Major | `inception/contract-design/contract-summary.md` K-16 `authorization_model.two_facade_layers` | 上一輪指出第二層 facade 的鍵誤寫為 `U17_layer`（`U17` 在全檔其他每一處皆指 `a11y-gate`，與需求欄位授權無關）。現文已改為 `U20_layer`，與 `U19_layer` 對稱；對全檔所有 `U17` 出現處逐一核對（契約表 K-13／K-14／K-19／K-20 及其規格區塊），全部正確指向 `a11y-gate`，未發現同型誤植殘留 | （已修正，無待辦） | Resolved |
| R-04 | Minor | `inception/contract-design/contract-summary.md` § `## 契約表` 開頭「機制欄的值」清單 | 上一輪指出該清單仍只列 10 個值，未納入修訂 1 新增的 `mcp`。現文已補上「`mcp`（MCP 協定的工具宣告；修訂 1 新增第 11 個值，見 `X-04`。傳輸形式與認證機制為未定項 `OQ-16`／`OQ-15`）」，與下方契約表、X-04 規格（`U21 mcp-bridge`）及其他 `mcp` 提及處一致 | （已修正，無待辦） | Resolved |

### Summary

**量測結果**（均重新實測，非沿用上一輪）：
- `backend/services/user_router.py`：自我停用守門條件在 `:645`、最後一位可編輯角色守門條件在 `:667`（`grep -n` 直接取值）——與契約現文的 `:645-646`／`:667-671` 相符。
- `aidlc/.../requirements-analysis/requirements.md`：「四面向皆適用，無不適用項。」在 `:622`，「不得對外暴露，僅供同主機」在 `:619`——與契約現文相符；殘留的 `:617`／`:614` 字串僅見於自檢 3 敘述句與處置表，屬描述舊錯誤的歷史敘事，非活引用。
- `U17` 在全檔（契約表與規格區塊）共 11 處出現，全部指向 `a11y-gate`，`two_facade_layers` 區塊內已無 `U17_layer`，只有對稱的 `U19_layer`／`U20_layer`。
- 機制欄值清單現列 11 個（含新增 `mcp`），與契約表、X-04（`mcp`，`U21 mcp-bridge`）一致。
- 作者自查新增的 `playwright.config.ts:17` → `frontend/playwright.config.ts:17` 修正：路徑確認存在於 `frontend/` 下，該行內容確為 `retries: process.env.CI ? 1 : 0`，與契約引用相符。
- `git diff` 顯示本檔唯一的「刪除後取代」是機制值清單那一行（R-04 的修法），其餘「修訂 1」整節為新增（尚未提交過），故不存在腳本化全域取代波及他處的痕跡；逐一核對未發現任何被誤改的表格列或 YAML 區塊。
- 重跑機械檢查：26 個 fenced YAML 區塊（21 `yaml shared-schema` ＋ 4 `yaml OpenAPI` ＋ 1 `yaml AsyncAPI`）全部可解析為合法 YAML；21 個 `shared-schema` 區塊的 `behaviour_semantics` 子結構均含三個 `[C7]` 要求鍵（`authorization_responsibility`／`observable_side_effects`／`retry_and_idempotency`）；契約標題計數 `K-01`–`K-20`＝20、`X-01`–`X-04`＝4，合計 24，與處置表宣稱一致。
- `required-sections` sensor 對 `contract-summary.md` 執行結果 `pass: true`（19 個 H2，含修訂 1 全部必要小節）。`upstream-coverage` sensor（`--stage-slug contract-design`）執行結果 `pass: true, unreferenced: []`。

**findings 統計**：4 項（R-01～R-04），全部 `Resolved`；本輪未發現新缺陷，無新增 ID。

**建議**：四項發現的修正皆經逐字核對為真實且完整，且未發現修正動作波及其他內容（無新的行號錯誤、無表格或 YAML 結構損壞、無契約計數或邊數偏移）。本輪範圍之外的實質內容（21 條新邊對映、契約結構、兩層 facade 概念、授權模型、`X-04` 的部分契約取捨）依任務指示不重新審查，上一輪已確認的結論維持有效。判定 **READY**。

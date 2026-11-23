# 安全測試說明（261116-brain-create-diagram）

> ADR-0006 security baseline 四面向逐項對照（`project.md` `## Mandated`）。

| 面向 | 本 intent 的影響 | 承載測試／檢查 | 判定 |
|---|---|---|---|
| IAM（權限） | 大腦以**使用者自己的 token** 經既有建圖端點建圖（FR4.3），不取得使用者沒有的權限；無架構編輯權不建（FR4.1）；候選點選時伺服器重新驗證（FR3.5） | `test_brain_diagram_creation_flow.py`：`test_without_arch_edit_nothing_is_created`（deny）、建圖成功案（allow）、`test_forbidden_403_text_depends_on_its_source`；`test_diagram_drafts_api.py` 的 `require_arch_action("edit")` 雙向 | 適用，已測 |
| Encryption | 無新傳輸路徑或儲存加密變更；建圖走同進程 ASGI | — | 不適用：沒有新增對外連線或敏感欄位 |
| Network exposure | 無新埠、無新對外端點；只在既有端點加參數（`as_draft`、`finalize`） | `dump_openapi.py --check` 確認端點集合只有預期的形狀變化 | 不適用：未新增暴露面 |
| Audit logging | 經大腦建立寫入 `diagram_change_records`（FR7.1）；觀測日誌只記判定類別、不記原文與圖名（NFR4） | `test_brain_diagram_creation.py` 的變更紀錄案；`test_decision_is_logged_by_category_without_utterance_or_title`（本站新增，含兩項突變驗證） | 適用，已測 |

## 已知限制

- 建圖逾時後，若 INSERT 晚到落地，該草稿**不會**有「經大腦建立」的變更紀錄（稽核缺一筆）。見 `test-results.md` 的已知限制。
- 草稿對外一律 409：評核、WA 共編、估價綁圖、分享四個入口各有 TestClient 案例（`test_diagram_drafts_api.py`）。

## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Iteration:** 1

| ID | Severity | Location | Finding | Suggested fix | Status |
|---|---|---|---|---|---|

### Summary

本輪實測結果（以實際量測，非讀作者敘述）：

1. **`FR12.0`**：`grep -rn project_members backend/ schema_rbac.sql` 全樹 0 命中，確認「無成員關係表」為真。`schema_rbac.sql:327-334` 的 `projects` 表僅有 `id`／`name`／`owner_user_id`／`is_default`／`created_at`，無任何成員關聯欄位。讀 `backend/services/hierarchy_migration.py` 全文，確認它對每位持圖使用者各建一個預設 `projects` 列並設其為 `owner_user_id`（第 204、365、398-418 行的邏輯），故在沒有成員表的情況下「某專案的唯一成員」在資料上等於「每一位使用者」——FR12.5a 字面實作會對每個停用請求命中 409。這條推論成立。
2. **`FR12.4c`**：讀 `requirements.md` 的 `FR1.8` 與其註記，確認 `DefaultRedirect` 會把使用者送到他自己的落地頁；`stories.md:835` 的 `AC12.4.3` 已同步改為「我的落地頁（不限入口頁）」，與 `FR12.4c` 更正後的文字一致，無矛盾。
3. **`FR12.5b`**：以 Python 解析 `openapi.json`（repo 根目錄，55 個 operation），得到狀態碼分佈 `{200:53, 422:45, 201:1, 204:1}`，非 2xx/422 的宣告數確實為 0，與文件逐字宣稱的數字完全吻合。「加 409 不會觸發 CI 的 OpenAPI 漂移閘門」這個結論成立，改為 DoD 要求顯式宣告 `responses={409: ...}` 是正確的補強。
4. **`FR12.5c`**：讀 `backend/services/user_router.py:660-676`，確認停用端點做的是 `target_user.is_active = request.is_active` 後 `db.commit()`，是一個 UPDATE，外鍵約束對 UPDATE 確實無效力；`schema_rbac.sql:344-347` 的 `owner_user_id` 欄位 COMMENT 逐字為「deliberately NOT decided (OQ-H1, landing U7) — no ON DELETE clause」，證實原文「資料庫會擋下」的理由確實是錯的、且方向相反（是刻意留白而非既有保護）。更正後的結論（FR12.5a 無資料庫層 backstop、須完整實作於應用層）正確。

**分類核對**：四處在 `scope-document.md`（能力 12，§S16/S17 已核可）與 `domain-design`（`ProjectMembership`／`ProjectMember` 元件、`OQ-14` 已核可、`DG-9` 已記載三張新表觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步）中逐一核對，確認四處皆為「填補原稿缺漏或糾正原稿錯誤理由」，沒有一處引入 `scope-document.md` 未核可的新能力或新範圍。`FR12.0` 觸發的 blocking 同步規則已在 domain-design 的 `DG-9` 記載並指派 `code-generation`（ALWAYS，游標之後），後果完整。

**內部一致性**：四處與 `requirements.md` 其餘內容（`FR1.8`、`FR12.1`-`FR12.6`）、`stories.md`（`AC12.4.3`）、`domain-design` 的 `decisions.md`／`components.md`（`ADR-009`-`ADR-011`、`DG-9`）互相一致，無矛盾。問題檔「隔離單站補核」一節的四處逐項清單與 `requirements.md` 正文的更正內容逐字對應。

**建議**：四項更正皆通過事實查證、皆為對齊修正而非新範圍擴張、後果已完整記載並有下游承接站。本輪 READY,無待處置發現。

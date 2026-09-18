# NFR Requirements — 釐清問題 · U2 `user-object-serialization`

> Stage: nfr-requirements（Construction 3.2）· Unit: `user-object-serialization`（kind: service）
> **本站已開始但未完成** —— Q1 的定案觸發 scope 擴充，依 `project.md` 規則必須先回跳上游修訂，本站的 artifact 待修訂完成後才產出。

## Sources（唯讀查證）

| # | 查證 | 結果 |
|---|---|---|
| S1 | 清單端點的查詢 | `db.query(User).order_by(User.id).all()` —— **無分頁、無上限**，回傳全部使用者 |
| S2 | 迴圈內的既有查詢 | 對每個待授權使用者呼叫一次待授權申請查詢（**既有 N+1**，非本 intent 引入） |
| S3 | 本單元的增量 | 每列新增：一次時區正規化 + 一次逾期判定，**皆為純記憶體計算、零新增查詢** |
| S4 | 三個端點的回應模型 | 皆宣告 `response_model`，回應 key 集合由模型欄位宣告決定 |

---

## Q1. 清單端點無分頁 —— 本站要訂什麼效能需求

A. 不訂分頁，如實記載增量性質
B. **訂分頁需求**
C. 訂帳號數上限

[Answer]: B

> **後續處置（2026-08-10）**：本題定案為 B，經二次確認後選定**回跳上游修訂、本 intent 實作分頁**。
>
> 依 `project.md ## Corrections` 的既有規則：「下游 stage 的答案觸發 scope 擴充時，**回跳上游 stage 以 Modify 模式疊加修訂**（歸檔舊 artifact、既有答案與清單不動、修訂來源記入問題檔 Revision 段）並重走 approval gate；**不得在下游 stage 擅自擴大已核可的範圍**」。
>
> **因此本站的 artifact 暫不產出** —— 在上游修訂完成前產出，等於以即將失效的範圍為基礎作業。

## Q2. ADR-0006 audit logging：「誰查看了活動資料」是否需記錄

A. **不要求，但寫明判定理由**
B. 要求記錄查看行為

[Answer]: A

> 本題定案不受 Q1 的 scope 擴充影響，待本站重啟時直接沿用。

---

# 重啟（2026-08-11）— 上游修訂完成，本站產出

> Q1 觸發的 scope 擴充已完整走完回跳流程：`scope-document` Revision 2（新增 Must 能力 (f)／PU-6）→ requirements Revision 1（FR-6.1〜6.7、NFR-8〜10）→ stories Revision 1（US-5，11 條 AC）→ refined-mockups Revision 1（定案 5〜9、`PaginationControl`）→ application-design Revision 1（AD-10／11／12、C-9）→ units-generation Revision 1（C-9 後端併入本單元）→ delivery-planning Revision 1（U2 移入 B3）→ functional-design Revision 1（BR-P1〜P5、`UserListPage`）。**八站全數經 approval gate 核可。**
>
> **本站無新問題**：Q1 的定案（實作分頁）已由上游落實，Q2 的定案（不記錄查看行為）不受影響、直接沿用並寫入 `security-requirements.md` 的 S-3。分頁的所有設計參數（每頁筆數、上限、非法值處置、回應形狀）皆已由 application-design 定案，本站只做 NFR 層的展開。
>
> 依 `project.md` 的既有 correction（上游已定案的事項不重問，省題並記明清單），本站不新增問題。

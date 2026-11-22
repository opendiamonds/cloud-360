# Security Design — u1-iac-api

> 對齊 security-requirements ADR-0006／NFR3／NFR4。

## 授權

- 每路由先 `require_story_action`（對齊 BR1.1）；download＝D1 edit。
- 403 不改 404；US6.1／NFR4.1 成對 TestClient。

## 輸入驗證

- Pydantic 對齊 contract-summary；`diagram_id` 必填路徑依 BR1.2 三碼。
- Zip／草稿體積在進 Store 前檢查（≤16 MiB／槽）。

## 密文處理（NFR3）

- Redactor 純函式核心；改寫後 zip／JSON／log **抽樣禁止**再現明文樣式。
- Log 欄位白名單：request_id、user、diagram、route、status、error.code、duration；**黑名單**：HCL 全文、prompt、JWT。

## 網路與高風險

- 僅 `/api/iac` 能力動詞；**無** apply／SM Put 客戶端。
- Checkov／LLM 皆為出站呼叫：逾時＋輸出截斷；不把雲端憑證寫進 IaC 執行路徑。

## 審計

- 結構化 `cloud360.iac.*`；與 request_id 關聯（Q4=A）。

<!-- confirmed: Looks correct -->

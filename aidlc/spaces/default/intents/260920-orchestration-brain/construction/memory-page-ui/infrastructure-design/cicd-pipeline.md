# CI/CD Pipeline — `U15 memory-page-ui`

> 本單元的前端改動對管線是 **0 行**；後端「已核准」檢查會連帶觸及 OpenAPI 漂移閘門。
> 本檔把兩者寫成下游可複驗的形式。
>
> **本站未派審查員**（依 2026-10-06 核可的精簡做法），故每一條都附可複驗指令。
> 此事於核可關卡一併揭露。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `construction/memory-page-ui/nfr-design/performance-design.md` | `UIP-*` 的驗證方式（e2e） |
| `construction/memory-page-ui/nfr-design/security-design.md` | `SEC-U15-*` 的驗證落點；§四 後端缺口 |
| `construction/memory-page-ui/nfr-design/logical-components.md` | 共用檔清單 |
| `construction/memory-page-ui/functional-design/functional-spec.md` | 兩個 API 消費點 |
| `inception/contract-design/contract-summary.md` | `K-08` 的 OpenAPI 半邊 |

## 一、新 e2e spec 不需管線改動（本站重新實測）

| 查證 | 結果 |
|---|---|
| `ui-regression` 怎麼挑測試 | `.github/workflows/ui-regression.lock.yml:558` 逐字 `run: timeout 15m npx playwright test`——裸指令 |
| Playwright 收集範圍 | `frontend/playwright.config.ts:10` 逐字 `testDir: './tests/e2e',` |
| 既有 spec | `frontend/tests/e2e/` 下三支：`estimate-workspace.spec.ts`、`member-pages.spec.ts`、`regression.spec.ts` |
| 結論 | 新 spec（建議 `memory-page.spec.ts`）丟進該目錄即被撿到，零管線改動 |

## 二、`ui-regression` 是本單元唯一碰得到畫面的閘門

- `post-steps` 讀 `.stats.unexpected`，非 0 即 `exit 1`；容忍 flaky，`retries: 1`（`team.md`）。
- **名稱穩定性是硬約束**：Kiwi 案例以 `<describe> › <test>` 為鍵，新 e2e 的字串一旦
  落地即不可再改，否則產生孤兒案例。名稱在 `code-generation` 定下。
- **穩定性要求**：nfr-design 審查 `R-04` 建議以 `page.route` 模擬 offset 位移的伺服器
  驗證補償重抓。凡以延遲回應構造的競態測試，須以確定性的路由攔截而非 `waitForTimeout`
  實作，避免 flaky 被 `retries: 1` 掩蓋。

## 三、後端「已核准」檢查的管線後果

使用者已裁決把該修補併入本單元 code-generation。其管線面：

| 閘門 | 影響 | 處置 |
|---|---|---|
| backend `unittest` | 需新增雙向 `TestClient`（pending → 拒、approved → 2xx） | `team.md` 規則 A＋B |
| OpenAPI drift（`backend/scripts/dump_openapi.py --check`） | 若在 router 宣告新增的 403 回應，`openapi.json` 必須重 dump；`DELETE` 現刻意不宣告 403（`[D1]`=A） | 重 dump 並同步 `frontend/src/types/api.d.ts`；落點選 facade 時視其是否改變回應宣告而定 |
| 既有測試 `tests/test_memory_contract.py` 的 `C3` | 宣告 router 不做授權判定；若落點選 router 會與之衝突 | 依 nfr-design 審查 `R-05`，落點優先考慮 facade |
| `repo-contract`、frontend lint、`tsc -b`、docker-build | 無影響 | — |

## 四、部署與回滾

- deploy-on-merge 至 staging（`org.md`），本單元無特殊部署步驟。
- 回滾：前端與後端改動皆為程式碼層，`git revert` 該 PR 即可；無 schema、無設定、
  無資料遷移，故回滾不需資料面處理。
- **同批次約束**：「已核准」檢查與記憶頁可分開上線（無破壞性契約變更），但若檢查
  改變 `DELETE` 的回應宣告，`openapi.json` 與 `api.d.ts` 必須與後端改動同一 PR。

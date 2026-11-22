# Tech Stack Decisions — u1-iac-api

> Unit: `u1-iac-api`（service）· Q3=A · 對齊 codekb／`project.md`／NFR2／NFR6。

## 選定

| 層 | 選擇 | 理由 |
|---|---|---|
| 語言／框架 | Python 3.12＋FastAPI | 既有 backend；掛載 `/api/iac` |
| 套件落點 | `backend/iac/`（session／generator／scanner／redactor／router） | NFR6；FD Q1=A |
| D1 LLM | 既有 LangGraph＋OpenRouter 路徑（可 stub） | codekb；演示可測 |
| D2 掃描 | **Checkov CLI**（執行期呼叫） | Q3=A；不自研引擎；本 intent **不**加 CI scan job |
| D3／純函式測試 | Hypothesis（PBT） | NFR2／ADR-0006 |
| Session | 行程 in-memory dict／可注入 store | FD Q5=A |
| 驗證 | Pydantic 模型對齊 contract-summary | 契約單一來源 |

## 版本釘選（實作時寫入）

| 工具 | 政策 |
|---|---|
| Checkov | code-gen 時釘**具體版本**於文件／Dockerfile 或 `.tool-versions`；執行前探测；缺失 → 明確失敗 |
| Python deps | 沿用 `backend/requirements.txt`；新增 IaC 相關套件須列明用途；**避免**引入需雲端憑證的 apply SDK 作為執行路徑 |

## 明確不選（本輪）

| 候選 | 原因 |
|---|---|
| tfsec／雙工具合併 | Q3≠B／C |
| 自研掃描引擎 | requirements 約束 |
| Redis／DB session | Q5=A；FD 已定 memory |
| 商業 IaC 平台嵌入 | 範圍外 |

## NFR2 測試邊界

- generator／scanner 適配器／redactor 的**純函式核心**必須有 `@given`；純函式層無 httpx／DB／HTTPException。
- CLI 包裝層可用 example-based＋失敗路徑測；PBT 焦點在解析／映射／改寫規則。

<!-- confirmed: Looks correct -->

# 查證證據（Evidence）

> practices-discovery 產物｜intent `261105-d-iac-generation`｜HEAD `0bffc82`（`0bffc82d01cfe01edb1f3f5a8931290d5f885501`）｜2026-11-05T15:48:45Z
>
> **Final Integration（Step 5）**：記錄查閱來源、spoke 異議處置、以及訪談 Q1–Q8 定案。Summary Confirmation = Looks correct。本檔於確認授權後由 orchestrator 重存（recovery）。

---

## 查閱來源清單

| 來源 | 路徑 | 用途 |
|---|---|---|
| 團隊／專案／組織規則 | `memory/{team,project,org}.md` | 基線與 hard constraints |
| codekb | `codekb/cloud/*`（Focused STALE） | Story D 現況；Q3-for-D 誤述已打叉 |
| Lead 草稿 | 同目錄四檔 | Step 2 基線 |
| Spoke 盲評 | `contributions/aidlc-{quality,developer,devsecops}-agent.md` | 測試檔數 41、PBT 擴張須 Affirm、secret 雙軌、`backend/iac/` 套件、產品級禁 apply |
| 問題檔 | `practices-discovery-questions.md` | Q1–Q8 權威答案 |
| 工作區抽樣 | `backend/tests/test_*.py`＝41；workflows 無 IaC scan | 計量校正 |

---

## 訪談定案紀錄（Final Integration）

| 問題 | 答案 | 定案內容 | 寫入位置 |
|---|---|---|---|
| Q1 Walking skeleton | A | 本 intent 維持 `skeleton: off` | `team-practices.md ## Walking Skeleton` |
| Q2 第一個 D HTTP 授權 | A | D1／D2／D3 任一第一個 HTTP 消費者 → allow／deny TestClient（即使 seed 未改） | `discovered-rules.md` Mandated；`team-practices.md ## Testing Posture` |
| Q3 D2 掃描自動化 | A | unittest 編排＋報告形狀 only；不新增 CI scan job | `team-practices.md` Deployment／Testing；不進 Mandated 為 CI job |
| Q4 D3 Secret 測試 | A | 負向＋redaction 突變；contract 擴大另排 | `discovered-rules.md` Mandated |
| Q5 套件／PBT | B | `backend/iac/`；PBT＝generator 及 scanner／redactor（新 Affirm） | `discovered-rules.md` Mandated；`team-practices.md ## Code Style` |
| Q6 Agent／分桶 | A | 決定性核心先於 LLM；一律 `langgraph_runtime`＋OpenRouter | `discovered-rules.md` Mandated；Code Style |
| Q7 產品禁 apply | A | Forbidden：D API／agent 不得代 apply／destroy | `discovered-rules.md` Forbidden |
| Q8 Methodology | A | `custom`＋同 PR Ordering；還原 commit fence | `team-practices.md` Testing／Way of Working |

---

## Spoke 異議已採納／已回應

| Spoke 異議 | 處置 |
|---|---|
| Quality：測試檔數「約 43」應為 41 | 已改為 41 個 `test_*.py` |
| Quality：Methodology custom 不得 silently promote | Q8=A 已 Affirm |
| Quality：I5 不得假裝 ADR-0006 已含 scanner／redactor | Q5=B 明示本輪 Affirm 擴大；建議後續 ADR |
| Quality：codekb「D 已比照 team.md Q3」錯誤 | 見下節打叉；Q2 才定案 D 交叉義務 |
| Quality：I2 勿保留「僅 D1」中間項 | 問題檔已採 A＝任一故事；定案 A |
| Dev：漏 `backend/cost/` 套件先例／禁 `d1_*` 前綴 | Q5=B 採領域套件 `backend/iac/`＋領域語彙檔名 |
| DevSecOps：secret 掃描已部分全域（值形 regex） | Deployment 改寫為雙軌敘述 |
| DevSecOps：產品級禁 apply 與人工閘並列 | Q7=A 寫入 Forbidden |

---

## codekb 錯誤聲明（必須打叉）

`code-quality-assessment.md`（或等同段落）若寫「首個 D 端點的測試義務：allow／deny 雙向 TestClient（team.md Q3 定案）」——**錯誤**。`team.md` 該 Q3 原文鎖定 **C1／`/api/cost*`**，不適用 D 柱。D 柱對等義務由**本輪訪談 Q2=A** 才 Affirm。下游不得再引用 codekb 該句為已定案。

---

## Story D 現況（仍成立）

1. Workspace「生成 IaC 代碼」＝Coming Soon；不查 D1、不打 API。
2. 矩陣領先實作：有 D1／D2／D3 種子與標籤；無 router／OpenAPI／頁／agent／測試。
3. CI 無 IaC／secret 掃描工具 job（與 Q3=A 一致：本輪不新增）。
4. ADR-0006 generator PBT：模組 ABSENT ⇒ N/A；落地即 blocking；本輪另 Affirm scanner／redactor。

---

## 不構成新規則的觀察

- CTA 與 D1 權限脫鉤：產品／設計待修。
- Backend 無 Ruff／Black、無 coverage gate、無 Dependabot：待補承載，本輪不夾帶。
- C1 計價 Forbidden 全文仍在 memory，本檔不重複。

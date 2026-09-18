# Cloud-360 Baseline Record

> AI-DLC intent record。由 AI-DLC 各階段產生與維護。

此目錄是 [awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows) **v2** 的 artifacts 輸出位置：作用中 intent 的 record 目錄（`aidlc/spaces/<space>/intents/<record>/`，簡寫 `<record>/`）。

本 record 是 Cloud-360 的 **baseline record** — v2 之前累積在扁平 `aidlc-docs/` 目錄的所有 artifacts，由引擎的 flat-layout migration 整棵搬入（見 ADR-0011）。repo contract 的 `REQUIRED_RECORD_FILES` 就是對著這裡驗證。

### 結構

- `aidlc-state.md` — 專案 phase / constraint 狀態追蹤
- `audit/<host>-<clone>.md` — per-clone 稽核 shard，由引擎 append，**不要手動編輯**（v2 之前為單一 `audit.md`）
- `decisions-log.md` — 專案決議紀錄（僅在使用者明確要求時追加）
- `inception/` — 🔵 Inception phase artifacts
  - `requirements/cloud-360-srs.md` — 需求分析輸出（SRS）
  - `user-stories/stories.md`、`user-stories/personas.md` — user stories 與 personas
  - `application-design/system-architecture.md` — 應用層設計
  - `decisions/NNNN-*.md` — 架構決策（ADRs）
  - `plans/` — workflow planning 輸出
  - `reverse-engineering/` — brownfield 掃描結果
- `construction/` — 🟢 Construction phase artifacts（NFR、functional design、build-and-test、code generation 結果）
- `operations/` — 🟡 Operations phase artifacts（部署、監控、incident playbooks）

### 文件語言

本 record 內每份 `*.md` 一律繁體中文（見 ADR-0009），由 `scripts/validate_repo_contract.py` 擋下殘留的 `## English Version` 段落。

### 常設約束

見 `aidlc-state.md` 的 **Extension Configuration** 區塊，以及 `aidlc/spaces/default/memory/project.md` 的 `## Testing Posture` 與 `## Decided`。

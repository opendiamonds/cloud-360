## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-11-05T17:08:15Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/261105-d-iac-generation/inception/refined-mockups/interaction-spec.md > CopyCurrentFile › States › success；同見 mockups.md M2a | `interaction-spec.md` CopyCurrentFile 的 success 狀態寫「剪貼簿＝預覽全文（或凍結截斷規則）」；stories.md AC5.1.2 也保留同一個括弧「（或設計凍結之截斷規則）」。refined-mockups 是設計決策的凍結點，但本 stage 產出全程未作出「有無截斷規則、門檻為何」的決定。Playwright 測 AC5.1.2 時需斷言剪貼簿內容：不知規則，測試只能用「有文字」寬斷言，無法驗證「等於全文」——使 AC5.1.2 在自動化層事實上不可測。 | 在 interaction-spec.md CopyCurrentFile success state 或 design-system-mapping 加一行明確決定：例「本輪不設截斷上限；全檔複製；若 HCL 超過 N KB 由 Construction 補確認」，或「截斷 N 行並在複製文案後附「（已截至第 N 行）」」——任一方案皆可，但必須是可讓 Playwright 寫斷言的決定。若刻意留給 application-design 決，須在這兩處明寫「截斷規則待 application-design 凍結」，讓 Construction 知道 AC5.1.2 有一條 open item。 | New |
| R-02 | Minor | aidlc/spaces/default/intents/261105-d-iac-generation/inception/refined-mockups/mockups.md > M2 固定殼 › footer 說明 | footer 標注「[上一步] [下一步：…] ※僅導覽，不觸發執行」，但未定義邊界行為：第 1 步（生成步）「上一步」動作為何（隱藏？disabled？返回 Workspace？）；第 3 步（Secrets 步）「下一步」動作為何（隱藏？disabled？指向下載？）。Playwright 測 StepNav 邊界時無依據可寫，Construction 需自行發明。 | 在 M2 footer 說明或 interaction-spec.md FooterStepControls 補上邊界規格：建議「第 1 步：上一步隱藏（或 disabled+說明「已是第一步」）；第 3 步：下一步隱藏（或改為「完成並返回 Workspace」）」。若已有故事 AC 覆蓋此路徑請引用；若無，補進 mockups.md 即可。 | New |
| R-03 | Minor | aidlc/spaces/default/intents/261105-d-iac-generation/inception/refined-mockups/mockups.md > 全篇（無對應 screen）；同見 stories.md US2.2 AC2.2.1 | US2.2 AC2.2.1 寫「產出中可見對應內容或明確『實驗性』區塊」——mockups.md 沒有任何 screen 或 state 示範「實驗性標記」的視覺形式（例如 HCL 注解、badge、或 UI 旗標）。如果 Construction 決定以 HCL 內 comment（如 `# EXPERIMENTAL: GCP resource`）表達，則沒有 UI 決策需要；但如果有獨立的 UI 視覺提示，這個設計從未被畫出或描述。 | 在 mockups.md 補充一條說明：「AC2.2.1 的『實驗性』標記以 D1 generator 在 HCL 內嵌入 comment 表達（如 `# EXPERIMENTAL: GCP resource`），不需要額外 UI 元件」，或「多雲實驗性資源在 file-tree 或 HCL 預覽以 X 方式標示」。前者無需新增 screen；後者需補至少一個 state 示例。明確說明哪個方案，消除 Construction 的設計自由度。 | New |
| R-04 | Minor | aidlc/spaces/default/intents/261105-d-iac-generation/inception/refined-mockups/mockups.md > 全篇（無 ADR-0006 核查段） | project.md 明文：「涉及 IAM／權限矩陣／網路暴露／稽核記錄的變更，須在該 stage 產出中明列 ADR-0006 security baseline 四面向的影響與處置，不得僅以『已有 ADR-0006』帶過」。refined-mockups 產出（mockups.md、interaction-spec.md、design-system-mapping.md、accessibility-checklist.md）均無四面向逐項判定段。UI 層可判定的影響實際存在：IAM→disabled entry／execute 鈕已覆蓋；encryption→Secrets 步不展示明文（M2c「不出現」明文賦值）；network exposure→新 `/api/iac/` 端點不在本 stage 決定，但此為 N/A 需明記；audit logging→本 stage 無決策，屬 nfr-requirements 範圍，N/A 需明記。 | 在 mockups.md 或 accessibility-checklist.md 末尾補「ADR-0006 UI 層核查」四格表（IAM / encryption / network exposure / audit logging，各自 Covered／N/A＋理由）。IAM 與 encryption 在本 stage 有可查的設計決策，需寫 Covered；network exposure 與 audit logging 屬 N/A（contract-design／nfr-requirements 負責），仍需明記。 | New |

### Summary

refined-mockups 四份產出（mockups.md、interaction-spec.md、design-system-mapping.md、accessibility-checklist.md）整體品質高：Q1–Q6=A 全數忠實落地；free-view 與 execute 邊界清楚（StepNav 無 disabled、footer 契約明文「永不觸發執行 API」）；下載 modal focus trap 與 Esc 取消路徑被 interaction-spec 與 accessibility-checklist 雙重覆蓋；全部空狀態（無圖、無草稿、無 D2 報告）與失敗重試態均有對應 component state；design-system-mapping 明確阻止複製 ShareModal 的 a11y 債；test-id 表完整。唯一 Major 是 copy 截斷規則空缺（R-01），使 AC5.1.2 自動化斷言目前無依據——加一行決定即可解決，不需回頭改故事。Minor 三項（footer 邊界行為、多雲實驗性視覺、ADR-0006 四面向記錄）是 Construction 落地時的自由度缺口，人工核准前值得確認。

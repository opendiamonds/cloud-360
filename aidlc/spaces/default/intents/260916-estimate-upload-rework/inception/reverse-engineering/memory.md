# Stage Memory: reverse-engineering

## Interpretations

- 2026-09-16T08:05Z — CONDITIONAL stage 適用性：`aidlc-state.md` 第 6 行 `Project Type: Brownfield`，條件成立，執行本 stage。
- 2026-09-16T08:05Z — repo 集合解析：`intents.json` 的 `260916-estimate-upload-rework` 列**沒有** `repos` 欄位，依 stage 檔 Step 1 第 2 款屬「unrecorded project-root repo」，對 workspace root 執行一次，handoff 與兩張 link 收據皆**不加** `--repo` 限定。`codekb-path` 解析為 `aidlc/spaces/default/codekb/cloud/`。注意 `codekb/` 下另有一個 `cloud-360/` 目錄，非本 intent 的解析結果，不觸碰。
- 2026-09-16T08:05Z — 重掃守門回 `UNKNOWN_SCOPE (absent)`：store 沒有 fenced yaml scope_version 區塊，早於 scope 追蹤機制。依 stage 檔規則，**不提供 reuse 選項**，只問全掃 vs 焦點掃描。使用者選全掃。
- 2026-09-16T08:05Z — 全掃的依據以事實呈現給使用者再由其裁決，非逕自決定：舊 store 建於 2026-08-19 commit `c3de2c8`，其後應用碼變動 99 檔／+12,545 行（Azure／GCP Playwright calculator 子系統在舊 store 中完全不存在）；repo 規模小（backend＋frontend 共 184 追蹤檔）；本 intent 的退場範圍需完整盤點以消除 ASSUM-04 的隱性依賴風險。

## Deviations

- 2026-09-16T08:05Z — stage 檔規定 conductor 在派工前「不得檢視應用原始碼、列舉 repo 或預先計算檔案清單」。本次為了讓守門問題有事實依據，執行了 `git diff --stat`（僅統計數字）與 `ls backend/cost | wc -l`（僅計數），未讀取任何原始碼內容、未產生檔案清單。判定為守門決策所需的最小事實蒐集，不構成對 developer link 的重複。
- 2026-09-16T08:12Z — 第一次 developer 派工於約 7 分鐘後被使用者中斷，`developer-scan.md` 未產出。codekb store 未受影響（發布走 compare-and-swap，只有 architect 的最後一步會寫入）。掃描前快照（`store_generation` `sha256:9e2ee9ad…`、`source_fingerprint` `git:37b327b8…`、`paths ["./"]`）仍然有效，期間未改動任何原始碼，故未重取快照。
- 2026-09-16T08:20Z — 第二次派工改為背景執行，並在 brief 中加入明確指示：寧可在 Standard 深度下寫出完整可用的 handoff，也不要追求窮盡而never 落地；時間不足時須據實記為 skimmed 而非宣稱 deep。此為對前次中斷的直接回應。

- 2026-09-16T09:45Z — developer 於回報中指出「source fingerprint 不符會擋 publish」（指派單 `git:37b327b8…` vs HEAD `cd2754d`）。查證後判定為誤讀，未據以重取快照：`codekb-snapshot` 的 `source_fingerprint` 是對來源樹計算的內容指紋，不是 HEAD commit hash。掃描後重跑 `codekb-snapshot` 得到同一值，反而證明掃描期間來源未變動。architect 獨立重跑 `--mint` 亦得同值，publish 的 compare-and-swap 也未拒絕。此判定已寫入 artifact 9 以免下次再被重新提出。

## Tradeoffs

- 2026-09-16T08:05Z — **全掃 vs 焦點掃描**。全掃成本較高（前次嘗試 7 分鐘未完），但焦點掃描在 `UNKNOWN_SCOPE` 下的合併規則會讓 store 停在 `kind: partial`，且舊 prose 的深度覆蓋一律降級為 shallow——等於這個共用 store 會長期處於部分可信狀態。考量 repo 規模小且退場盤點需要完整依賴圖，選擇付出掃描時間。
- 2026-09-16T09:45Z — **全掃的廣度 vs 深度的誠實**。`kind: full`、`analyzed.paths` 含 `./`，但深度並非均勻：`backend/services/` 大檔、`frontend/src/pages/` 實作細節、43 支測試的個別內容只做盤點未逐行讀，已列入 `shallow.paths`。選擇不把它們升格為 deep，代價是 store 的 `full` 標記可能被下游誤讀為「處處都讀過了」；artifact 9 另加「深度分佈」段落作為防誤讀措施。architect 在 developer 的深度切分跨越元件邊界時（如 `frontend-cost-support` 深讀、`frontend-cost-page` 僅盤點）選擇拆分元件而非放寬宣稱。

## Open questions

- [open] 覆蓋度 backstop 回傳 `UNKNOWN_SCOPE (absent)` 而非 COVERS／NARROWER——舊 store 沒有機器可讀的 scope 區塊，無從比對。意即「本次覆蓋是否比上次窄」這個問題在本 intent **無法回答**，不是答案為否。下次重掃時新 store 已有 scope 區塊，backstop 才會真正發揮作用。
- [open] developer 發現 `backend/Dockerfile` 未安裝 Playwright Chromium，Azure／GCP Calculator runner 在部署容器內結構性不可用。這使 intent-capture Q1（現行路徑太慢／太常失敗）的立論僅由本機觀察支撐，「線上表現」從不存在。立論未被推翻，但下游若引用「現有 Calculator 的線上表現」作為依據，該依據無效。
- [open] 退場盤點漏掉的 8 類套件外掛鉤中，`scripts/validate_cost_calculator_boundary.py` 硬編碼指向 `backend/cost/cost_calculator.py` 且為 CI `repo-contract` job 第三步。ADR-0017 §2 決定把純函式層改錨至估價表解析器，因此這支腳本必須同步改寫而非刪除——由哪個 unit 承接尚未指派。

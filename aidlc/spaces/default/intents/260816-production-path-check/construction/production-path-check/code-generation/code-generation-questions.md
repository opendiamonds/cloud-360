# Code Generation — 問題

- Intent：`260816-production-path-check`
- Scope：bugfix

## Plan Approval

計畫全文見同目錄的 `code-generation-plan.md`。五個步驟：

1. 改 `validate_no_production_config_added()` 為 `git ls-files` 全域掃描（保留 path-part 精確比對）
2. 在 `backend/tests/` 新增回歸測試（隔離暫存 git repo，不污染真實 repo）
3. 突變驗證（還原修正 → 測試必須紅燈）
4. 同步 `project.md` `## Forbidden` 與 `team.md` 的落差記載
5. 驗證（兩支 contract 驗證器、`unittest discover`、`ci.yml` 未被改、NFR-3 計時）

**A. Approve Plan** — 依此計畫產生程式碼

**B. Request Changes** — 修改計畫後重新提出

`[Answer]: A —— Approve Plan（2026-08-18）`

---

## Q2（追加）：`CLAUDE.md` 第 4 章的措辭是否一併更新？

實作階段發現 `CLAUDE.md:66` 仍寫著這條規則的舊語意（「path parts 含 `prod`、`production`、`secrets` **不得新增**」），與 FR-6 剛改好的 `project.md` 直接矛盾。FR-6 的字面只點名 `project.md`，故此題單獨提出，不由實作者逕行決定。

**A. 一併改**
`CLAUDE.md` 第 4 章自述「本章為摘要，衝突時以 memory 層為準」，是 `project.md` 的**衍生落點**而非獨立規則，所以這是 FR-6 漏了一個落點，不是範圍擴張。且「改上游、漏衍生落點」正是本 intent 反覆在修的失敗形狀。實測 contract 的 `REQUIRED_TEXT` 未鎖該句（必要字串為 `AIDLC`、`.claude/skills/aidlc/SKILL.md`、`aidlc/spaces/<active-space>/memory/`、`Standing Constraints`、`validate_repo_contract.py`），改動不影響 CI。

**B. 不改，另開 follow-up**
嚴格遵守 `project.md` corrections 的「不得在下游 stage 擅自擴大已核可範圍」。代價是每個 agent 都讀的 `CLAUDE.md` 會有一段時間寫著已不成立的語意。

**C. 回跳 requirements-analysis 以 Modify 模式正式修訂**
最合規，但為一行字要多跑一輪 stage 與 reviewer。

`[Answer]: A —— 一併改（2026-08-18）`

> **可複驗落點**：此題以 structured question 於對話中提出並取得回答，對應 audit shard 的 `HUMAN_TURN 2026-08-17T23:40:58Z`；`CLAUDE.md` 的實際寫入時間為 `23:41:16Z`（以 `TZ=UTC date -r $(stat -f %m CLAUDE.md)` 換算），晚於該回合 18 秒。
>
> 本題補記於 reviewer 第二輪之後。原因值得記下：audit shard 的 SUBAGENT_COMPLETED 訊息被 `aidlc-log-subagent.ts` 硬截斷至 200 字元，所以「實作者把此決定留給人」這件事**物理上不在持久化紀錄裡**；而 `HUMAN_TURN` 事件只有時間戳、沒有內容欄位，它能證明「此刻有一次人類回合」，不能證明「這個回合在核准什麼」。把問答寫成正式的 Q&A 產出（比照 `requirements-analysis-questions.md` 的 Q3）才是這個專案裡可獨立複驗的形式。

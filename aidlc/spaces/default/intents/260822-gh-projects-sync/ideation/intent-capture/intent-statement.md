# Intent Statement — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: intent-capture（Ideation 1.1）· Record: 260822-gh-projects-sync
     來源標籤定義見 intent-capture-questions.md 的 ## Sources。
     每個實質主張都掛有來源標籤；未掛標籤的內容不得存在。 -->

## Problem Statement

- 具體的原始請求為：讓 AI-DLC 各 stage 的進展定時同步更新 opendiamonds 組織 Project #16「Cloud-360 開發計劃」中 item 的 Status 欄位（Backlog / Nice to have / Ready / In progress / In review / Done）[desc]
- 原始請求另指定以 repo 根目錄的 README.md 作為所有 intent 的需求來源 [desc]；此框架已由後續作答改為需求清單正本置於 Project #16、README 維持現有敘述 [Q7]
- 看板狀態靠人工維護，實際進度與板上顯示對不起來，看板因此失去可信度 [Q1]
- 同一件事的進度要在 AI-DLC 的 record 與看板各記一次，雙份維護必有一份悄悄過期 [Q1]
- 要做什麼散落在對話、issue、README 與各 intent record，沒有單一入口 [Q1]
- 不看 repo 的人無法從看板看到 AI-DLC 內部的實際進度 [Q1]
- 狀態失真已是既成事實而非預測：看板上有 item 標記為 In review，但對應的 issue 其實已經關閉 [Q4]

## Target Customer

| 受益者 | 目前的痛點 | Source |
| --- | --- | --- |
| 唯一開發者（本人） | 每跑完一個 stage 還要記得回去手動改看板狀態，經常忘記 | [Q2] |
| 其他 repo 協作者 | 看板狀態不準，看不出別人正在做什麼 | [Q2] |
| 不參與開發的觀看者 | 只看看板，看不到 AI-DLC 內部的 stage 進度 | [Q10] |
| 未來的自己 | 事後回溯某個功能走過哪些 stage、卡在哪裡時無跡可循 | [Q2] |

- 「不參與開發的觀看者」是本次要正式服務的對象；此項在第一輪答案中與受益者清單不一致，經追問後確認觀看者確實是受益者 [Q10]

## Success Metrics

| 指標 | 判定方式 | Source |
| --- | --- | --- |
| 零人工更新 | 任何 intent 跑完一個 stage 後，對應 item 的 Status 不需要人去改就已經正確 | [Q3] |
| 一致率 | 綁定到 AI-DLC intent 的 item 中，看板狀態與 record 實際狀態不一致者為 0 | [Q3] [Q12] |
| 可追溯 | 每次 Status 變更都能說出是哪個 intent、哪個 stage、什麼時間觸發的 | [Q3] |

- 一致率的分母只涵蓋已綁定到 AI-DLC intent 的 item；沒有對應 record 的既有 item 不進分母 [Q12]

## Initiative Trigger

- 已經被咬到：看板狀態已與現實脫節，再不處理會繼續累積 [Q4]
- 流程剛穩定：AI-DLC v2 已落地、intent 記錄格式穩定，現在才有東西可以拿來同步 [Q4]
- 準備擴大協作：接下來會有更多人／更多 intent 並行，人工維護撐不住 [Q4]

## Initial Scope Signal

### Workflow-selected scope

<!-- 僅證明 workflow 起跑時選定的 scope，不代表使用者確認的產品邊界。 -->

- `aidlc-github-projects-sync`（workflow-selected）[scope]

### User-confirmed product boundary

- 使用者確認工作流選定的範圍即為其意圖的產品邊界 [Q8]
- 需求清單的正本放在 Project #16；README 維持現有的總覽敘述，不改結構 [Q7]
- README 只增加一段指向 Project #16 的指路文字，說明它是需求清單的正本；本次實質的交付物是同步機制一項 [Q11]
- 同步採事件驅動即時更新，另加低頻排程對帳補掉漏掉的 [Q6]
- 同步失敗時要 workflow 紅燈並自動開 issue；排程對帳發現不一致也算一種需要通知的失敗 [Q9]

### 邊界上的既有約束

- 規則的落點必須是專案自有的規則層，不得寫進會被框架升級整批覆蓋的檔案 [memory:M3]
- AI-DLC 的產出一律位於作用中 intent 的 record 目錄下 [memory:M4]
- 雲端供應商 production 環境、production credentials 與 environment-specific secrets 不在專案範圍內，除非另開 ADR 核可 [memory:M2]

## Assumptions & Open Questions

- Project #16 的寫入權限問題將由作用中的 GitHub 帳號補上授權解決，不需要改變同步機制的設計；此項在問題檔建立前的對話中定案，未登錄為本 stage 的來源 [assumption]
- 看板上既有的 item 數量與狀態分布是出題當下的唯讀觀察值，會隨時間變動；下游若需要精確數字應重新查證 [assumption]
- 「其他 repo 協作者」的具體成員以問題檔選項中列出的名字為例，未經逐一確認其對本功能的實際需求 [assumption]
- 一個 AI-DLC intent 與一個 Project item 之間如何綁定尚未定義，屬於後續階段要解的問題 [assumption]
- AI-DLC 的 stage 進展如何對應到 6 個 Status 選項尚未定義，屬於後續階段要解的問題 [assumption]


## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-08-23T03:07:46Z
**Iteration:** 2

### Machine-checked (sensors, re-fired fresh this iteration)

```
bun .claude/tools/aidlc-sensor.ts fire claim-sources     --output-path intent-statement.md   → exit 0, no new failure file
bun .claude/tools/aidlc-sensor.ts fire claim-sources     --output-path stakeholder-map.md     → exit 0, no new failure file
bun .claude/tools/aidlc-sensor.ts fire required-sections --output-path intent-statement.md   → exit 0, no new failure file
bun .claude/tools/aidlc-sensor.ts fire required-sections --output-path stakeholder-map.md     → exit 0, no new failure file
bun .claude/tools/aidlc-sensor.ts fire upstream-coverage --output-path intent-statement.md   → exit 0, no new failure file
bun .claude/tools/aidlc-sensor.ts fire upstream-coverage --output-path stakeholder-map.md     → exit 0, no new failure file
```

All six pass clean. `.aidlc-sensors/intent-capture/` still holds only the two
pre-existing stale FAIL records from a much earlier draft (`b6e703bf`,
`c10dad1d`, both `02:4xZ`); no new file was written by this iteration's runs,
confirming nothing regressed.

I also read `.claude/tools/aidlc-sensor-claim-sources.ts` directly (not just
its output) to check the lead's claim about a stage-prose/sensor conflict for
Finding 4's fix. Confirmed real: any claim block outside
`## Assumptions & Open Questions` with zero tags fails
("claim block has no source tag"), and any such block tagged `[assumption]`
independently fails ("[assumption] is outside ## Assumptions & Open
Questions") — lines ~848–866. So the stage prose's own prescribed form for an
unresolved required field, `Unknown (open question) [assumption]`, cannot be
placed in a table row outside the Assumptions section without tripping the
sensor either way. The lead's workaround (omit the row, explain in an
HTML comment, which the sensor's comment-stripping logic — confirmed present
at line 114 — never sees) is a genuine resolution of a real tooling
contradiction, not an evasion.

### Verification of the four prior findings

| # | Original severity | Resolution | Assessment |
|---|---|---|---|
| 1 | Critical | Problem Statement bullet split in two: bullet 1 (`[desc]` only) now carries just the Status-field-sync request; bullet 2 states the README clause `[desc]` also contains, and that `[Q7]` superseded it. | Verified against the literal `[desc]` text in the Sources register — both bullets now say only what their tags support. Resolved. |
| 2 | Major (`[memory:M1]` bullet) | Bullet deleted outright rather than moved to Assumptions. | Independently agree with the deletion, not just accepting the lead's rationale: `## Scope Overrides` in `project.md` is a negative/exclusion list (M2) for this kind of intent — nothing in this project's memory layer affirmatively enumerates "GitHub integration tooling" as in-scope, so there was no true fact to relocate, only an unsupported inference to remove. Formal scope determination is scope-definition's job, not intent-capture's; M2 alone (this intent touches none of the excluded items) is sufficient signal at this stage. Resolved, and the "avoid an Assumptions-list churn for no operative gain" reasoning is sound. |
| 3 | Major (`[memory:M4]` bullet) | Trimmed to the literal ADR-0011 fact. | Verified against `project.md ## Decided` — the surviving sentence is now a direct, unembellished restatement. Resolved. |
| 4 | Major (stakeholder-map viewer authority row) | Row removed; reasoning captured in an HTML comment beneath the table rather than the stage's `Unknown (open question) [assumption]` form. | Verified the underlying stage/sensor conflict myself (see above) — the chosen form was the only one available that neither invents an authority classification nor breaks the sensor. Also checked whether omission "hides" something downstream needs: the stakeholder-map's own `## Assumptions & Open Questions` already carries "「不參與開發的觀看者」的具體身分未被指名；其人數、身分與查看頻率均未定義", so the open question is not lost, only not force-fit into a table cell it doesn't belong in. Note for the record: "未來的自己" was *already* absent from this same Decision-Makers table pre-fix, with no comment at all — so a Key-Stakeholder row not appearing in Decision-Makers is precedented document convention, not a new pattern introduced by this fix. Resolved. |

None of the four repairs introduced a new unsourced claim or misattribution
on the point they were fixing.

### New findings this iteration (judgment calls, both Minor — non-blocking)

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Minor | `intent-statement.md` line 9 (Problem Statement, new bullet 1) | Tagged `[desc]` only, but writes "...中 **item** 的 Status 欄位" where `[desc]`'s literal text says "...中 **issue** 的 Status 欄位" (see Sources register). This word substitution existed in the original combined bullet too, but was diluted there by a second `[Q7]` tag; splitting the bullet (Finding 1's fix) now makes it single-sourced to a tag whose literal text uses a different word. Substantively defensible — GitHub Projects v2 items are the superset GitHub concept (an item may wrap an issue, PR, or be a draft) and "item" is used consistently everywhere else in this record (background verification note, Q3, Q7) — but it is not what the sole cited source literally says. | Either swap back to "issue" for byte-for-byte fidelity, or add a one-clause note that "item" here normalizes `[desc]`'s "issue" to the Project's own vocabulary. Cosmetic; does not block. |
| 2 | Minor | `stakeholder-map.md`, "本專案的決策模型是單一決策者，沒有需要取得同意的第三方否決權 `[Q5]`" sitting immediately above the new HTML comment about viewer authority being unresolved | The two statements are not contradictory (Q5's own question scope never included viewers, so "no third party has veto" is accurate *within the parties Q5 asked about*), but placed back-to-back a reader could momentarily read "single decision-maker, no veto-holder" as covering the viewer role the very next comment says is undetermined. | Optional: qualify the bullet as "...在 Q5 涵蓋的關係人範圍內" or reorder so the comment isn't immediately adjacent. Not blocking — the bullet's own citation is unchanged from iteration 1 and remains valid. |

### Summary

Both Major/Critical-clearing repairs hold up under independent re-verification
(including reading the sensor's source, not just trusting its exit code), and
the two structural deletions (M1 bullet, viewer row) were checked for information
loss rather than accepted at face value — neither hides anything the rest of
the document doesn't already carry in `## Assumptions & Open Questions`. The
two new findings are cosmetic terminology/adjacency issues, not grounding
violations, and don't warrant another round. READY to proceed.

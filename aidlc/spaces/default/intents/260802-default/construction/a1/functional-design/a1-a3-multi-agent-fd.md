# A1 ↔ A3 Multi-Agent — Functional Design（精簡）

> Requirements: `a1-a3-multi-agent-requirements.md`  
> Branch: `luojingting/feat/a1-ux-optimize`


### 1. 狀態機

```
START
  → DESIGN_R1（產圖／改圖）
  → SCORE_R1（lens）
  → [score >= 80] → DONE_PASS（待套用）
  → [else] REVIEW_SPEAK（Review 發言）
  → DESIGN_R2（依對話改圖）
  → SCORE_R2
  → [score >= 80] → DONE_PASS
  → [else] → DONE_FAIL（待套用最佳圖／人工）
```

常數：`WA_COLLAB_TARGET_SCORE=80`、`WA_COLLAB_MAX_ROUNDS=2`。

### 2. SSE 契約

| type | 欄位 | 說明 |
|---|---|---|
| `message` | `content`, `speaker`∈{design,review} | 對話可見 |
| `progress` | `content` | 進度文字 |
| `xml_preview` | `content`, `round` | 預覽 XML，不寫畫布 |
| `score` | `overall_score`, `pillar_scores`, `findings`, `round`, `passed` | lens 分數 |
| `complete` | `status`∈{passed,failed}, `overall_score`, `xml`, `findings`, `review_id?` | 結束 |
| `error` | `content`／`message` | 致命錯誤 |

### 3. 模組

| 模組 | 職責 |
|---|---|
| `wa_score_service.score_xml` | evaluate＋Active Lens＋score_answers |
| `wa_collab_orchestrator.run_wa_collab` | FSM＋雙 agent |
| `agent_router` | `POST /generate-wa-collab` |
| FE Preview bar | 顯示分數／套用／放棄 |

### 4. Review 發言提示

Review 不以工具改圖；僅根據 lens findings 用繁中說明缺點與具體改圖方向，供 Design 下一輪使用。Design 第 2 輪 system／user 附上 Review 全文＋findings JSON＋current_xml。

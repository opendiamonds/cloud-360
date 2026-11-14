# 審查有效、收據缺失 — `U8 memory-service` / `code-generation` iteration 1

> **本檔的存在理由**：審查**確實執行過且結論有效**（全文見同目錄的
> `review-01.md`，14138 bytes、`VERDICT: READY`、兩項發現），
> 但 `REVIEW_COMPLETED` **記不進 audit**。本檔如實記載該落差與其根因，
> 而不是讓 audit 看起來像審查沒跑過。

## 一、引擎的拒絕（逐字）

```
Refusing REVIEW_COMPLETED for "code-generation": workspace source changed
after REVIEW_REQUESTED iteration 1. Restore the requested source state and
re-dispatch the reviewer.
```

## 二、實際改變的是什麼：**只有 Hypothesis 的測試快取**

| 查證 | 結果 |
|---|---|
| `REVIEW_REQUESTED` 之後最新的檔案 | `backend/.hypothesis/unicode_data/15.1.0/codec-v2-utf-8.json.gz` @ **19:01:40** |
| 最新的**受版控原始碼** | `backend/models.py` @ **18:44:23**——**早於** `REVIEW_REQUESTED` |
| `backend/.hypothesis/` 是否被 git 忽略 | **是**（`backend/.hypothesis/.gitignore:9` 的 `*`） |
| 為什麼它仍進入指紋 | `aidlc-lib.ts` 的 `filesystemSourceIdentity` **完全不看 gitignore** |

**因果鏈**：本單元新增了 5 個 `@given`（`test_memory_ranking.py`，`NFR3.24` 的
PBT）。審查者**必須**跑那些測試才能獨立查證——而**跑 Hypothesis 這個動作本身**
就會寫入 `.hypothesis` 的 unicode 與 constants 快取。於是：

> 審查者越認真查證，就越確定記不進收據。

這是 `project.md` 已逐字記載過的死結
（`code-generation:source-fingerprint-includes-caches`），本輪是它的第二次實例，
且這次的觸發源更單純——**只有** `.hypothesis`，連 `.pyc` 都在請求之前就已編譯。

## 三、為什麼不採用那兩條看似可行的出路

| 出路 | 為什麼不採用 |
|---|---|
| 重跑 `REVIEW_REQUESTED` 再記收據 | 那會把**請求時間記在審查實際執行之後**，等於偽造事件順序。審查已經跑完了 |
| `--retry-pending` | `aidlc-log.ts:2254` 逐字「cannot rebaseline changed content」，且該路徑只處理**沒有**指紋的舊請求 |
| 刪掉 `.hypothesis` 讓指紋復原 | 指紋比對的是**請求當時**的狀態，刪除同樣是改變；且刪掉之後 PBT 的 example database 消失，下次跑的覆蓋面不同 |
| 改 `.claude/` 下的指紋走訪邏輯 | `project.md ## Forbidden` 逐字禁止——升級時會被整批覆蓋 |

## 四、audit 的現況（如實記載）

| 事件 | 狀態 |
|---|---|
| `UNIT_STARTED`（`code-generation`／`memory-service`） | ✅ 已記錄 `2026-10-09T10:00:48Z` |
| `PLAN_APPROVAL_RECORDED` | ✅ 已記錄（使用者作答 `Approve Plan`） |
| `REVIEW_REQUESTED` iteration 1 | ✅ 已記錄（`review:b4b00f78e58b7b786d6a476e1a77a5c2`） |
| **`REVIEW_COMPLETED`** | ❌ **缺**——本檔即為其替代紀錄 |
| `UNIT_COMPLETED` | 見下方 |

## 五、審查結論（摘要；全文見 `review-01.md`）

**`VERDICT: READY`**，兩項發現，**兩項皆為本站新引入的測試缺口、非設計缺陷**：

| id | 嚴重度 | 內容 | 承接 |
|---|---|---|---|
| `R-01` | **Major** | `C6` 只解析 `SEARCH_SQL` **字串常數**，從未斷言 `search_records` 真的執行那個常數。審查已查證今日 `memory_service.py:337-338` 確實傳 `text(SEARCH_SQL)` 未經修改，**故目前鎖是成立的**；但一個讓常數逐位元不變（`C6` 綠）而 `search_records` 另組一條 SQL 的改寫，會**同時通過 `C6` 與 `S15`** | `build-and-test`（3.6，**ALWAYS**） |
| `R-02` | Minor | `CG8-1` 的大聲失敗路徑（`fulltext` 預設下 `write` 回 503）**零端到端測試**；`test_memory_authz.py` 全檔 `fulltext` 零命中。而 `construction.md` 的階段護欄要求整合邊界須覆蓋 happy path ＋ 至少兩個錯誤／邊界案例 | `build-and-test`（3.6，**ALWAYS**） |

**兩項的承接站都是 `build-and-test`，而那不是推託**：stage 檔逐字說該站
「verifies and extends, not creates from scratch」——補測試正是它的職責，
且它是 `ALWAYS`、在游標之後。

### 5.1 `R-01` 是對我設計的有效反駁

`infrastructure-design` 設計 `S15` 時我以為它能擋「先查再過濾」；
實作查出 `S15` 是純 psql、看不到 Python，於是加了 `C6` 補那一層。
**而 `R-01` 指出 `C6` 自己也只到一半**——它鎖「常數的形狀」，
沒鎖「函式真的用那個常數」。

這正是我在派工 brief 裡請它回答的問題（逐字「whether a rewrite exists that
passes both」），答案是**有**。具體修法已由審查寫出：
斷言 `search_records` 以**同一性**（而非文字相等）把 `SEARCH_SQL` 交給
`db.execute`。

## 六、真正的修法在上游，不在本 intent

指紋走訪應當尊重 gitignore（或至少排除 `.hypothesis/` 與 `__pycache__/`）。
**不得**以直接編輯 `.claude/` 下的 upstream 檔承載——
須以 issue 或升級記錄承載。本輪為第二次實例，建議在下一次 AIDLC 升級的
對照清單中列為已知問題。

# 審查有效、收據缺失 — `U10 session-store` / `code-generation` iteration 1

> **本檔的存在理由**：審查**確實執行過且結論有效**（全文見同目錄的
> `review-01.md`，10495 bytes、`VERDICT: READY`、兩項發現），
> 但 `REVIEW_COMPLETED` **記不進 audit**。本檔如實記載該落差與其根因，
> 而不是讓 audit 看起來像審查沒跑過。

## 一、引擎的拒絕（逐字）

```
Refusing REVIEW_COMPLETED for "code-generation": workspace source changed
after REVIEW_REQUESTED iteration 1. Restore the requested source state and
re-dispatch the reviewer.
```

## 二、實際改變的是什麼：**只有 Hypothesis 的測試快取**

以 `find … | xargs stat -f '%Sm %N' -t '%Y-%m-%dT%H:%M:%S' | sort -r` 實測
（排除 `aidlc/` 與 `.git/`），`REVIEW_REQUESTED` 之後唯二變動的檔案是：

| 檔案 | 時間 | 是否受版控 |
|---|---|---|
| `backend/.hypothesis/unicode_data/15.1.0/codec-v2-utf-8.json.gz` | `2026-10-10T00:12:14` | **否** |
| `backend/.hypothesis/constants/91360571e2d23f3e` | `2026-10-10T00:06:35` | **否** |

兩者皆由 `backend/.hypothesis/.gitignore:9` 的 `*` 忽略——以
`git check-ignore -v` 逐檔確認，不是推測。

**次新的檔案是 `backend/services/redis_gateway.py` @ `2026-10-09T23:58:24`，
早於 `REVIEW_REQUESTED`。** 亦即：**沒有任何一個受版控的原始檔在請求之後變動。**

## 三、根因：指紋走訪不看 gitignore

`aidlc-lib.ts` 的 `filesystemSourceIdentity` **完全不查 gitignore**，所以
`.hypothesis/**` 進入 workspace source 指紋。而本單元有 3 個 `@given`
property 測試——**審查者必須跑它們才能獨立查證**，而跑 Hypothesis 這個動作
本身就會寫入 `constants/` 與 `unicode_data/` 快取。

> 審查者越認真查證，就越確定記不進收據。

這是 `project.md` 已逐字記載的死結
（`code-generation:source-fingerprint-includes-caches`），**本輪是它的第三次實例**
（前兩次：`260920-orchestration-brain` 的 `U8 memory-service`，以及本 intent 更早一輪）。

### 本輪多做了一件事，而它仍然不夠

派工前 conductor **已先跑過**完整測試兩次（`653 tests OK`），用意正是把
`.hypothesis` 與 `.pyc` 的快取預熱，讓審查者的重跑成為位元中性的動作。
**預熱不足以避免它**：Hypothesis 在本輪仍新增了一個 `constants/` 條目並更新了
unicode 快取。故「先跑一次暖身」**不是**這個死結的解法，記在這裡以免下一個人再試一次。

## 四、為什麼不採用那幾條看似可行的出路

| 出路 | 為什麼不採用 |
|---|---|
| 重跑 `REVIEW_REQUESTED` 再記收據 | 會把**請求時間記在審查實際執行之後**，等於偽造事件順序。審查已經跑完了 |
| `--retry-pending` | `aidlc-log.ts:2254` 逐字「cannot rebaseline changed content」，且該路徑只處理**沒有**指紋的舊請求 |
| 刪掉 `.hypothesis` 讓指紋復原 | 指紋比對的是**請求當時**的狀態；刪除同樣是改變 |
| 改 `.claude/` 下的指紋走訪邏輯 | `project.md ## Forbidden` 逐字禁止——升級時會被整批覆蓋 |
| 叫審查者不要跑測試 | 那會讓審查失去獨立查證能力，而本輪審查的價值正來自它實跑 |

## 五、audit 的現況（如實記載）

| 事件 | 狀態 |
|---|---|
| `UNIT_STARTED`（`code-generation`／`session-store`） | ✅ 已記錄 `2026-10-09T15:14:55Z` |
| `PLAN_APPROVAL_RECORDED` | ✅ 已記錄（使用者作答 `Approve Plan`） |
| `REVIEW_REQUESTED` iteration 1 | ✅ 已記錄（`review:734903677c8750e7e1c15afada3dfac8`） |
| **`REVIEW_COMPLETED`** | ❌ **缺**——本檔即為其替代紀錄 |
| `UNIT_COMPLETED` | 見下方 |

## 六、審查結論（摘要；全文見 `review-01.md`）

**`VERDICT: READY`**，兩項發現。詳見該檔的 `### Findings` 表。

## 七、真正的修法在上游，不在本 intent

指紋走訪應當尊重 gitignore（或至少排除 `.hypothesis/` 與 `__pycache__/`）。
**不得**以直接編輯 `.claude/` 下的 upstream 檔承載——須以 issue 或升級記錄承載。
本輪為**第三次**實例；建議在下一次 AIDLC 升級的對照清單中列為已知問題，
並附本檔的實測：**預熱快取不足以規避它**。

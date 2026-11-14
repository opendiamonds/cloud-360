# NFR Design 問題檔 — `U22` `progress-channel`

> 單元：`U22` `progress-channel`（`library`，M）
> Stage：`nfr-design`（3.3）　Depth：`Minimal`　Review class：`advisory`（單輪、兩種結論皆終局）
> 建立時間：2026-10-03T16:28:59Z
> 產出：`security-design.md`、`logical-components.md`、`traceability.json`
> （`produces_kinds` 使 performance／scalability／reliability／observability-design 對 `library` 不適用；
> `logical-components` 的 kind 清單含 `library`，故適用）

---

## 前言：本站只有兩題

本單元的上游定案密度很高，`project.md` 的多條 correction 要求不重問已定案事項。
逐一盤點後，**不重問**的清單：

| 已定案 | 出處 |
|---|---|
| 隔離機制（per-request 鍵）與其設計 | `functional-design` `BR1.1`–`BR1.3`、`[Q1]`=A |
| 清除契約與異常清除的測試義務 | `BR2.1`–`BR2.3`、`[Q2]`=A、`U22-V2` |
| 讀取語意（破壞性 drain、不重播） | `[Q3]`=A、`BR1.3` |
| 容量上界的性質與丟棄優先序 | `[Q4]`=A、`BR4.1`／`BR4.2`；數值在 `code-generation`（`S-1`） |
| log 分級（容量 WARN、通道不存在 ERROR） | `nfr-requirements` `[Q2]`=A、`U22-D6` |
| 鍵的隨機來源要求與禁止清單 | `nfr-requirements` `[Q4]`=A、`SEC-1` |
| 不加鎖（不照抄 `threading.Lock`） | `K-18` `shape_precedent.do_not_follow`、`U22-D4` |
| 零新依賴、模組落點、logger 名稱、測試框架 | `U22-D1`／`D2`／`D3`／`D8` |
| 四面向 ADR-0006 判定與 PBT 不適用 | `functional-design §五`、`nfr-requirements §二` |
| `NFR4` 不適用（三層理由，審查已證實理由 ① 決定性） | `nfr-requirements §四`、`S-6` |

**剩下兩題，而兩題都是上一輪審查遞過來的——它們是設計決定，本站正是它們的落點。**

---

## Q1 — 臨界區段要不要抽成私有同步函式？

`nfr-requirements` 的 `U22-V4` 定案為「以需求規定 `publish` 的容量檢查與 buffer 變動
之間不得有 `await`，並寫進函式本體註解」，而我當時把它記成「靠人遵守、沒有自動化
會擋」（`S-4`）。**審查的 `R-05` 指出那句話說得太重**：把臨界區段抽成一個私有的
**同步 `def`**，`await` 在那裡就是 `SyntaxError`——零契約成本，因為 `K-18` 只規定
`publish` 的 `form: async`，沒規定它內部不能呼叫同步私有函式。

這是 `functional-design` 審查 `R-07` 建議的「註解**或結構**」裡我沒取的那一半，而
本 session 已經第二次出現「只取建議的一半」。本站是這個決定的正確落點。

- **A（建議）— 抽成私有同步函式。** `publish` 保持 `async def`（契約不動），內部把
  「容量檢查 ＋ 丟棄 ＋ 寫入」整段抽成 `def _admit(channel, event) -> None`。
  好處：`await` 在 `_admit` 內是 `SyntaxError`，**語言層面保證**而非靠人記得；成本為零
  （不新增依賴、不改契約、不改呼叫端）。代價：多一個函式；`U22-V4` 的驗證方式由
  「人工 code review」改為「結構即保證」，故 `S-4` 的風險等級可下調——但本站**不回改**
  已凍結的 `nfr-requirements`，而是在本站的設計與 `traceability` 中明記這個升級。
- **B — 維持註解。** 好處：與 `U22-V4` 的字面完全一致，不需解釋任何偏離。代價：
  審查已指出它靠人遵守而結構化方案零成本；維持 B 等於刻意選一個較弱的機制。
- **C — 抽成同步函式**並且**在 `publish` 內加 `assert`** 檢查呼叫期間沒有其他協程
  改動 buffer。代價：`assert` 在 `python -O` 下會被移除，且「其他協程有沒有改動」
  在單執行緒下需要額外的版本號欄位才驗得出來——為一個已由結構排除的問題再加機制。

`[Answer]`: A <!-- 人工作答 2026-10-04T01:36:08Z（`date -u` 實取）。選項文字與選單逐字一致。 -->

---

## Q2 — `design_agent.py:103` 的例外原文要怎麼處置？

審查的 `R-01`（Critical）查出我的 `SEC-2` 寫 `:216` 是「唯一」的洩漏點，而**實測有
兩行**（我已自行複驗）：

```
:101  await _progress_queue.put({"type": "error", "content": "產圖發生錯誤"})   ← 正確，固定字串
:103  return f"產圖失敗：{e}"                                                  ← 我漏掉的那一處
:216  yield {"type": "error", "content": f"發生未預期錯誤：{e}"}                ← SEC-2 點名的那一處
```

`SEC-2` 的需求本文已隨 `nfr-requirements` 的收據凍結，**但本站的設計可以涵蓋兩處
並明記這是對該需求範圍的更正**——這與我在 `nfr-requirements` 承接 `functional-design`
凍結 Critical 的手法相同，只是往下一層。

**兩處的性質不同，所以不一定該用同一個處置**：`:216` 是 `yield` 給 SSE，**直送
使用者**；`:103` 是**工具的回傳值**，會回到 LLM 的 context，由 LLM 決定要不要轉述。

- **A（建議）— 兩處都回固定字串，例外原文只進 log。** `:103` 改為固定字串（例如
  「產圖失敗，請稍後再試」），例外原文由既有的 `logger.exception`（`:100`，已存在）
  承載。好處：不依賴 LLM 的自制；`:101` 在同一個 `except` 區塊已經是這個形狀，
  所以 `:103` 改成一致是**消除同區塊內的不一致**而非新增限制。代價：LLM 失去除錯
  資訊，可能給出較籠統的說明——但它本來也不該把內部例外轉述給使用者。
- **B — `:103` 回固定字串＋一個關聯 id，`:216` 同樣。** 好處：使用者看到的訊息可
  對應到 log 裡的那一筆，排查時有抓手。代價：要引入關聯 id 的產生與傳遞，而本單元
  刻意不新增設定面與機制（`SEC-4`）；且 `ProgressEvent` 沒有這個欄位，加它會動到
  已凍結的 `entities.md` 形狀。
- **C — `:103` 保留例外原文（它只給 LLM，不直送使用者），只改 `:216`。** 好處：
  LLM 保有除錯資訊；改動面最小。代價：**「只給 LLM」不是一道邊界**——LLM 的輸出
  直接送給使用者，所以它等於「使用者可能看到，取決於模型當下的判斷」。
  `AC13.1.3` 逐字要求「回應**不含**內部例外的原文」，而這個選項讓那條 AC 的成立
  條件變成模型行為，不是程式行為。
- **D — 兩處都保留，另在 system prompt 要求 LLM 不得轉述例外原文。** 代價：同 C，
  且把一個可以用固定字串解決的問題變成 prompt 工程；`project.md` 把「所有 LLM 路徑」
  列為本 repo 三塊結構性自動化盲區之一，意即這條約束**沒有任何自動化測得出來**。

`[Answer]`: A <!-- 人工作答 2026-10-04T01:36:08Z（`date -u` 實取）。選項文字與選單逐字一致。 -->

---

## Assumptions & Open Questions

（本站產出時填寫）

# 揭露：review-02 的審查檔在記錄前由 conductor 做過一個字元的格式修補

**時間**：2026-10-03T13:24:18Z
**對象**：`.aidlc-engine/reviews/infrastructure-design/units/brain-infra/805ffc7417cd3263/2.review.md`
（其可讀複本為 `reviews/review-02.md`）

## 做了什麼

審查者（`aidlc-architecture-reviewer-agent`，iteration 2，`Recovery: stale-receipt`）
完成審查並判定 **READY**，但它在 `R-16` 那一列的 Finding 欄寫了一個**行內程式碼片段，
而該片段內含一個 `|`**：

```
`grep -c '^| \*\*S-'`
```

GFM 的表格不理會 backtick——cell 仍在該 `|` 處被切開，於是該列變成 **7 cells**
（header 宣告 6），`aidlc-log.ts review --verdict` 直接拒絕：
`row has 7 cells, header declares 6`。

**conductor 的修補**：把該片段內的 `|` 改為 `\|`（逐字：`'^| \*\*S-'` → `'^\| \*\*S-'`）。
**位元組差為 +1**（14677 → 14678），**沒有任何其他改動**：議決、嚴重度、Finding 文字、
Required action、Status 全部原樣。

## 為什麼是這樣處理，而不是重派

1. 這是本 attempt **唯一**的 recovery 審查。若它記不進去，依協定「recovery 已用盡」，
   本 stage 在人工 Request Changes 之前**無法再取得任何審查收據**。
2. iteration 1 的重派已經示範過風險：那次的 agent 以 0 次工具呼叫回應並虛構內容
   （見 `unreceipted-verification-02.md`）。
3. 若以「把正確位元組貼進 brief、請 agent 照寫」的方式重派，那次重派實質上只是把
   conductor 的貼上內容回寫一次，卻會在稽核上**看起來像一次獨立審查**。
   直接修一個字元並公開揭露，比那個更誠實，且可複驗——兩份檔案都留著。

## 可複驗

- 審查者原始輸出（未修補）：session scratchpad 的 `infra-recovery-review.md`（14677 bytes）
- 修補後（即記錄進 review record 的版本）：14678 bytes
- 差異：單一字元 `\`，位置在 `R-16` 列的行內程式碼片段內

## 審查結論本身（未受修補影響）

**READY**。`R-14`（conductor 刻意偏離建議、改為整條撤回順序約束）經審查者獨立覆驗
**成立**；`R-15`／`R-16`／`R-17`／`R-18` 逐一開檔核對後確認落地。
新增 `R-19`（Major，`deploy.yml`／`docker-compose.deploy.yml` 的行號引用漂移約
190–230 行）與 `R-20`（Minor，ADR-0006 Encryption 列未回指 `§7.2` 的剝除規則），
連同既有 `R-12`（Minor）一併帶進核可關卡。
**這三項本站不修**：recovery 已用盡，任何對 `produces` 的寫入都會使 READY 收據失效
而無審查可補。

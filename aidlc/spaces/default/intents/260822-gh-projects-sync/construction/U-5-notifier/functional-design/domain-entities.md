# Domain Entities — U-5 通報

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-5-notifier · kind: library -->

## `FailureIdentity`

```
FailureIdentity = { intent_id, reason_code }
```

逐字沿用 [ad:component-methods.md] §C-5（[ad:decisions.md] ADR-A8 的 [Q5=A] 定案）。**本檔不擴充它。**

`reason_code` 在此的值域**不等於** U-1 的 `ReasonCode`——通報只針對**紅燈級**與需人處理的情形。`suppressed`／`parked`／`unparseable`／`whitelisted`／`undecidable` 屬機制的正常判斷，**不通報也不紅燈**（[ad:component-methods.md] 逐字）。實際會成為 `FailureIdentity` 一部分的是 `ExternalError`、`Rejected`、`Aborted`（後者通報但不紅燈）、`CannotCreate`。

## 通報 issue 的可搜尋形狀（本站新增）

ADR-A8 說「以該鍵搜尋開啟中的通報 issue（label ＋ 標題慣例）」但**沒有定義那個慣例**。本檔補上。

| 元素 | 形式 | 用途 |
| --- | --- | --- |
| label | `aidlc-sync-alert` | **單一 label**，讓 [Q2=A] 的「一次列舉全部通報 issue」成為一次查詢 |
| 標題 | `[aidlc-sync] <intent_id> / <reason_code> (×N)` | 前兩者為搜尋鍵，`×N` 為 ADR-A8 要求的「標題計數」 |
| 內文首行 | `<!-- aidlc-alert: intent=<intent_id> reason=<reason_code> -->` | **機器可讀的鍵**，標題若被人編輯仍可還原 |

**內文首行的機器可讀標記是本站新增的**，理由：標題同時承擔「人看的摘要」與「機器搜尋的鍵」兩個角色，而人**會**編輯標題。把鍵複製一份到內文的 HTML 註解裡，讓比對不依賴標題的完整性。

> 這與 U-2 的受管區塊是**同一個手法**（`<!-- aidlc:managed -->`），但**不共用程式碼**——U-2 的區塊是 Status 綁定 issue 的，本單元的是通報 issue 的，兩者的內容與生命週期完全不同。共用只會製造一個假的抽象。

**計數 `×N` 的更新規則**：每次追加 comment 時 +1。它是給人看的（一眼看出這個失敗發生過幾次），**不是**判定依據——判定依據永遠是實際的 comment 數與 issue 開關狀態。

## 與上游的對應

`FailureIdentity` 與收斂演算法引自 [ad:component-methods.md] §C-5 與 [ad:decisions.md] ADR-A8；哪些 `reason_code` 不通報不紅燈引自同兩處與 [ad:services.md]；`ReasonCode` 的完整值域引自 U-1 的 `domain-entities.md`；FR-E3 的三要素引自 `requirements.md`；單元邊界與完成判準引自 [ug:unit-of-work.md] 的 U-5；AC 歸屬引自 [ug:unit-of-work-story-map.md]（S-8 AC 1–3、S-3 AC 4 的開 issue 那一半）；元件分層引自 [ad:components.md]。

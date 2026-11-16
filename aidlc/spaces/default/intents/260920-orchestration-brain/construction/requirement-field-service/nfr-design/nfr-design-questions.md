# NFR Design 問題檔 — `U20 requirement-field-service`

> Depth 為 `Minimal`。**本站出題數為 0。**
>
> 本站要設計的模式全部由上游決定或可由 repo 現況查證：沒有新進程、沒有外部呼叫
> （故無熔斷、無重試退避）、不加快取（`NFR20.6`）、不加鎖（`scalability-requirements.md`
> 第二節）。唯一一項需要人裁決的事——請求本體帶 `updated_by` 時要拒絕還是忽略
> （`nfr-requirements` 審查 `review-01` 的 R-06）——**使用者已於 2026-10-12 同意建議
> 「拒絕，回 422」**，本站照該裁決設計，不重問。

## 〇、本站承接的上一站審查殘留（設計層可落實者在本站落實）

`nfr-requirements` 的 `review-01`（READY，Major 1、Minor 7）在核可時已凍結產出，
使用者裁決殘留帶往後續處理。其中屬**設計**層級者，本站直接落實，避免帶到程式產生：

| 審查項 | 本站處置 | 落點 |
|---|---|---|
| R-01 Major：授權矩陣缺「非成員但有 `K4.edit` 寫入」 | 補成九列矩陣 | `security-design.md` 第二節 |
| R-02：upsert 的查詢計數判準不可達 | 改為「單一敘述＋`RETURNING`」 | `performance-design.md` 第二節 |
| R-03：依賴失敗測試需不重拋例外的 `TestClient` | 寫進測試形狀 | `reliability-design.md` 第四節 |
| R-04：CASCADE 與收斂需在真實 PostgreSQL 驗 | 指定 CI 的 `memory-schema` job 為落點並設計步驟 | `reliability-design.md` 第三節 |
| R-05：parent id 命名理由與回補 | 本站登錄回補開放項 | `logical-components.md` 第四節 |
| R-06：本體帶 `updated_by` | 已裁決：422（`extra="forbid"`） | `security-design.md` 第三節 |
| R-07：「不含 PII」對自由文字過度宣稱 | 改寫為「設計上不預期、無法保證」並加填寫提示 | `security-design.md` 第一節 |
| R-08：併發清空會兩者皆寫入 | 清空改為單一條件式 UPDATE | `reliability-design.md` 第二節 |

## 一、問題

（無）

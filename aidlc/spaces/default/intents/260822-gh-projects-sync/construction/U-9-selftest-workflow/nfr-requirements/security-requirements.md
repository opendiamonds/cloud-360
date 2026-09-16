# 安全需求 — U-9 自我測試 workflow

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-9-selftest-workflow · kind: service -->

## 缺口 Q-1：R-1.3 的 403 斷言與第二段的寫入需求，對憑證範圍的要求相反

本單元的完成判準有兩條同時涉及憑證，而它們把憑證往兩個方向拉：

| 需求 | 對憑證的要求 |
| --- | --- |
| 第二段：對**獨立測試 Project** 做端到端寫入讀回 | 憑證**必須能寫**該測試 Project |
| R-1.3：憑證做**範圍外寫入**時回 **403** | 憑證**必須有一個真實的範圍外**，且該範圍外可被安全地嘗試 |

**兩者本身不矛盾**——「能寫 A 但不能寫 B」是正常的權限設定。**矛盾在於上游沒有為此留位置**：`requirements.md` 的 NFR-S1（經 ADR-0014 更正）把權限集合定為三項，其中 Projects 那一項是「**組織層** Projects 讀寫」。**組織層讀寫涵蓋該組織下的所有 Project，包含測試 Project，也包含任何本應是「範圍外」的 Project。**

若憑證真的是組織層 Projects 讀寫，**R-1.3 的 403 永遠不會發生**——那條斷言會變成恆真的反面：它永遠失敗，或者被寫成一個不會失敗的假斷言。這正是 `project.md` 已記載過的形狀（「查出恆真（不可能失敗）的驗收標準時改寫而非刪除：防禦意圖通常是真的，錯的是落點層次」）。

**R-1.3 的防禦意圖是真的**——它要防的是「憑證權限開太大」。錯的是落點：在**組織層**授權下，沒有任何組織內的 Project 是範圍外的。

**處置（依 `project.md` 的既有教訓：改寫而非刪除，把它移到碰得到真實失敗面的層次）**：

| 選項 | 真實的範圍外是什麼 | 判定 |
| --- | --- | --- |
| 對**另一個組織**的 Project 寫入 | 真實存在 | 需要第二個組織，成本不成比例 |
| 對 **repo 內容的範圍外路徑**寫入（NFR-S1 第 2 項逐字「用途**限於** record 目錄下的……」） | **真實存在**——若該限制是以權限而非紀律實作 | **推薦落點** |
| 對**未安裝該 App 的 repo** 寫入 | 真實存在，且本 repo 所在組織必有其他 repo | **推薦落點**，成本最低 |

**本站標出缺口與落點，不逕自改寫已核可的完成判準**（[ug:unit-of-work.md] 的 U-9 完成判準已過 units-generation 的 gate）。指派：**units-generation 的 U-9 完成判準第 3 條**，確認人為 **Bolt 0 的 gate**——因為它同時決定憑證怎麼鑄，與缺口 P-1 落在同一個決定點上。

> **指派目標的 stage 執行性檢查**（依 `project.md` 的 `units-generation:260822-ug-L2`）：units-generation 是 **EXECUTE** 而非 CONDITIONAL，且本 intent 已完成過它兩輪（含 Revision 1），不存在「該 stage 可能被 skip」的無聲落空風險。

## 憑證在本單元的使用邊界

| 段 | 是否用憑證 | 說明 |
| --- | --- | --- |
| 第一段（fixture dry-run） | **否** | [ad:services.md] S-D 逐字「不發任何 API 寫入請求」。這也是它必須先跑的理由之一——**沒有憑證就沒有洩漏面** |
| 第二段（端到端） | 是 | 對獨立測試 Project；本次執行專屬的 item |

## A-1 的 fixture 不得成為新的洩漏面

A-1 斷言 U-1 的 output 不含憑證樣式，其 fixture 需要一個「看起來像憑證」的輸入。**該樣式必須是結構相同但不觸發掃描器的假值**——理由與實作註記見 `../functional-design/domain-entities.md`。

**這裡補一項該檔沒說的**：假樣式也不得是任何**曾經真實存在過**的憑證的變形。`project.md` 已記載過相關教訓——憑證若曾誤存為 Actions variable，「應該沒人看過」是沒有證據的假設，處置是重新產生金鑰。同理，fixture 裡的假樣式應該是**憑空構造**的，不是從任何真值改幾個字元來的。

## ADR-0006 四面向判定

| 面向 | 判定 |
| --- | --- |
| IAM | **適用**。見上方 Q-1 與憑證使用邊界 |
| Encryption | **不適用**。本單元不儲存任何資料；第二段的傳輸由 GitHub API 的 HTTPS 承擔（NFR-S4） |
| Network exposure | **不適用**。不新增服務或端點（NFR-S5） |
| Audit logging | **適用且已處置**：斷言失敗訊息必須含預期與實得（`business-rules.md` R-1.1）；清理失敗訊息必須含殘留 item 的識別資訊（`business-logic-model.md` 錯誤表） |

## 既有技術堆疊的承接

第二段的憑證接線沿用既有形狀：[ck:technology-stack.md] 記載本 repo 的 11 支 gh-aw workflow 已同時掛四個不同的 token secret（`COPILOT_GITHUB_TOKEN`、`GH_AW_GITHUB_MCP_SERVER_TOKEN`、`GH_AW_GITHUB_TOKEN`、`GITHUB_TOKEN`）——**多憑證併存在本 repo 是既成事實**，故 Q-1 若收斂成「第二個憑證」，接線本身不是新問題。

## 與上游的對應

NFR-S1（經 ADR-0014 更正的三項集合）、NFR-S4／S5 引自 `requirements.md`；U-9 的三條完成判準（含 R-1.3 的 403）引自 [ug:unit-of-work.md]；S-D 第一段「不發任何 API 寫入請求」引自 [ad:services.md]；「恆真 AC 應改寫而非刪除」與「憑證曾誤存即須重新產生」引自 `project.md ## Corrections`／`## Mandated`；ADR-0006 四面向的逐項判定形式依 `project.md ## Mandated`；R-1.1、R-4 與繼承斷言 A-1 見本單元的 `business-rules.md` 與 `../functional-design/domain-entities.md`；兩段式流程與錯誤表見本單元的 `../functional-design/business-logic-model.md`；本 repo 既有的多憑證接線引自 [ck:technology-stack.md]（`aidlc/spaces/default/codekb/cloud-360/technology-stack.md`）。


> **權限集合現為四項（ADR-0015 §8）**：ADR-0014 補入的是第三項 Issues 寫入，而 §8 進一步指出**開 PR 與推分支在 GitHub 權限模型中是兩個獨立權限**，第四項為 `Pull requests: write`（佐證：`deploy.yml:174-175` 在本 repo 上正在運行的設定即分列兩行）。本檔沿用的是 NFR-S1 當時的三項計數，更正指令與閘門（Bolt 0，須在憑證鑄造前）見 `../../../inception/decisions/0015-functional-design-upstream-amendments.md` §8。指標補於 2026-08-30T01:31:09Z。
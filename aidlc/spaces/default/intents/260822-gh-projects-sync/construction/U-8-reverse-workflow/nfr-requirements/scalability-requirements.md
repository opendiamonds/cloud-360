# 擴充性需求 — U-8 反向同步 workflow

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-8-reverse-workflow · kind: service -->

## 隨 intent 數成長的兩個量

| 量 | 成長 | 上限機制 |
| --- | --- | --- |
| `read_item` 次數 | O(N)，N ＝ 已綁定 intent 數 | **無**。對帳有 FR-D3 的單次處理量上限（NFR-P4），反向同步沒有等價規定 |
| 同時開啟的反向 PR 數 | O(改動數)，最壞 O(N) | **無** |

**第一列是上游的不對稱，不是本站的疏漏。** FR-D3 為對帳指定了批次上限，理由是 C-T5 的速率上限值未確認；反向同步做的是同量級的掃描，卻沒有對應規定。**本站不自行補一個數字**——那會是無依據的參數。記為觀察並指派：C-T5 上限值確認時（NFR-P4 的追蹤點），反向同步的批次上限須一併決定。

**第二列由 E-2 的裁定直接造成。** 「一個 intent 一則 PR」把一次大掃描的產出從一則 PR 變成最多 N 則。這是 `business-logic-model.md` 記載的取捨的另一面：換來 [US:S-6 AC 3] 的逐 intent 抑制**結構性成立**，代價是最壞情況下的 PR 數量。

## 為什麼最壞情況在實務上不會發生

反向 PR 只在**有人動了看板**時產生。要一次產生 N 則 PR，得有人在同一天內改動全部 N 個 intent 的卡片。這不是零機率（大批次整理看板），但——

- 它是**人的動作**，不是機制自發的；動的人知道自己動了多少。
- 每則 PR 只含一個檔的少數幾行，審閱成本低。
- U-10b 已負責讓這些 PR 不觸發高成本 workflow，所以 CI 成本不隨 PR 數線性放大。**這是 U-10b 與 U-8 被判定為真捆綁的原因之一**（見 `unit-of-work-dependency.md`）。

**但「不會發生」是判斷不是保證**，故仍記入本檔而非略過。

## 不隨規模成長的部分

- **狀態檔大小**：`pending_reverse` 是每個 intent 各自 `sync-state.json` 內的一個欄位，不是集中式清單。intent 增加不會讓任何單一檔案變大。
- **本單元的邏輯**：逐 intent 獨立處理，無跨 intent 狀態，無排序需求。

## 既有技術堆疊的承接

PR 數量的上界與 CI 成本的關係受既有 workflow 集合影響。[ck:technology-stack.md] 記載本 repo 現有 **11 組 gh-aw** ＋ `ci.yml`（4 job）＋ `deploy.yml`（3 job）——U-10b 要排除的「高成本 workflow」是從這個既有集合裡挑，不是抽象概念；N 則反向 PR 的實際成本 ＝ N ×（未被排除的 workflow 之和）。

## 與上游的對應

FR-D3、NFR-P4、C-T5 引自 `requirements.md`；E-2 的裁定與其取捨、U-10b 的捆綁關係引自本單元的 `business-logic-model.md`；R-4b 的 AC 分散對照與 R-5 的 U-10b 責任歸屬引自本單元的 `business-rules.md`；本 repo 既有的 gh-aw／CI 堆疊事實引自 [ck:technology-stack.md]（`aidlc/spaces/default/codekb/cloud-360/technology-stack.md`）。

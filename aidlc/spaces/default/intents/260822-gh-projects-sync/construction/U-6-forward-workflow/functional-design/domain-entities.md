# Domain Entities — U-6 正向同步 workflow

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-6-forward-workflow · kind: service -->

## 本單元不擁有型別，它擁有**編排**

U-1～U-5 各自擁有型別（`Decision`、`Block`、`ItemState`、`SyncState`、`FailureIdentity`）。本單元是 workflow 層——它把那些元件串起來，**不新增領域型別**。

唯一的例外是下面這個跨單元契約，它在本站才第一次被定義。

## 反向同步 PR 的識別標記（D-1，跨三單元契約）

| 元素 | 值 | 誰用 |
| --- | --- | --- |
| 分支名前綴 | `aidlc-sync/reverse/` | **人**：一眼分辨；`git branch` glob。**不是** U-10b 的排除依據——見下方更正 |
| label | `aidlc-sync-reverse` | **U-6**（本單元）：`gh pr list --label` 找出開啟中的反向 PR；**人**：一眼分辨 |

> **不要與 `sync-state.json` 的 `pending_reverse` 混淆。** 兩者只是詞序對調，但性質相反：本單元的 `Config.reverse_pending` 是**每輪即時算出、絕不落地**的執行期集合；`pending_reverse` 是 U-8 產生語意、U-4 持久化的**欄位**。本單元從不寫後者。
| 產生者 | **U-8** | 開 PR 時必須同時設定分支名與 label |

> **更正（2026-08-29T15:21:33Z，reviewer iteration 1 Major）：先前此表把「`branches-ignore` 讓 run 根本不被建立」列為分支名前綴的用途，該技術事實不成立。** 對 `pull_request` 事件，`branches`／`branches-ignore` 過濾的是 PR 的 **base** 分支而非 head；反向 PR 的 base 依 [req:FR-G1] 一律是 `ut`，與其他所有 PR 相同，因此該過濾器**不會排除任何 PR**。
>
> **U-10b 實際採用的是 `paths-ignore`**（見其 `nfr-requirements/tech-stack-decisions.md`），與 U-10a 同一條 glob。該單元早已獨立查證出這個落差並明文記載「不採用 `branches-ignore`……這與 D-1 的理由相左」，**但更正沒有回饋到 D-1 的原始敘述所在地（本單元）**——這正是 `project.md` 反覆記載的跨檔傳播失敗。
>
> **D-1 的裁定本身（分支前綴 ＋ label 並用）不改**，依 `project.md` 的 `functional-design:c22`（查證推翻的是理由而非決定時，只修理由）。但**理由降級**：分支前綴不再是「必要」，而是「代價可接受的附加」——人一眼分辨與 `git branch` glob 是它剩下的真實價值。

**三個單元依賴同一組標記**。改動任一個都必須三處同步——這條依賴不在依賴圖上（U-6 與 U-10b 之間沒有 DAG 邊），只存在於這份契約裡。

> **分支命名不符 `team.md` 的 `<uploader>/<type>/<slug>`**。該規則明文不適用於「自動產生的分支」（列舉 `dependabot/*`、`release/*`），本項屬同類，但**規則層應補一筆記明**，以免下次 practices-discovery 把它算成違規。

## `Config` 在本單元的組裝責任

U-1 的 `domain-entities.md` 定義了 `Config` 的**四個**欄位（`whitelist`、`reverse_pending`、`record_root`、`field_max_length`），**本單元不增不減**。**本單元是它的組裝點**：

| 欄位 | 來源 |
| --- | --- |
| `record_root`、`field_max_length`、`whitelist` | workflow 的 input／設定，靜態 |
| **`reverse_pending`** | **本單元每輪動態計算**（承接缺口 F-4）——見 `business-rules.md` R-2 群 |


> **`reverse_rejected` 已於 2026-08-30T00:57:28Z 移出 `Config`（reviewer iteration 3 m-2）。** 它由本單元的 R-6.2a 引入，先前被放進 `Config` 並補進本表，但那是錯的落點：U-1 `domain-entities.md:61` 明文把 `Config` 的擴充範圍限定為「`C-3`／`C-7` 所需的欄位由那些單元各自補充」，而 `reverse_rejected` 的消費者是**本單元的 workflow 層**與 `render` 的 `Context`，不屬 C-1／C-3／C-7 任一；同檔 `:72-80` 的「`Config` 的承載形式」也把 composite action 的 input 列舉為 2 純量 ＋ 2 集合，加第五欄就要動那份列舉。
>
> **現在的形狀**：`reverse_rejected` 是本單元 workflow 層的**本輪執行期集合**，與 `reverse_pending` 同源（同一次 label 查詢）但**不進 `Config`**——`reverse_pending` 必須進，因為 `map()` 的第 2 條判定要用它；`reverse_rejected` 從不進 `map()`，只餵給 R-5.6 的寫入理由判定與 R-6.2b 的 `Context`。
>
> **這段經歷仍值得留著，因為它示範了一個真實的機制缺口**：`Config` 是跨單元共用型別，各單元各自補自己需要的欄位，而**沒有任何機制保證補的欄位會被登錄、也沒有機制擋住同名不同義**。`reverse_rejected` 一度被放進 `Config` 並補進本表（2026-08-29T23:42:35Z），iteration 3 的 m-2 才指出落點錯誤而移出。
>
> **本輪更正（reviewer iteration 4 Group A M-3，2026-08-30T01:31:09Z）**：本段先前殘留「目前全 stage 的 `Config` 欄位共**五個**……本單元（`reverse_rejected`）」，與同檔已改的組裝表（四欄、明記不含 `reverse_rejected`）互斥。**現行事實**：`Config` 共**四個**欄位，全部由 U-1 定義，本單元不增不減。

## 與上游的對應

S-A 的生命週期、concurrency group 與自我排除兩道防線引自 [ad:services.md]；`Config` 的欄位定義引自 U-1 的 `domain-entities.md`（[Q2=A]）；反向 PR 的存在與其對 S-A 的影響引自 [ad:services.md] 的 S-C 與 [req:FR-G3]；分支命名規則的例外條款引自 `team.md`；單元邊界與完成判準引自 [ug:unit-of-work.md] 的 U-6；AC 歸屬引自 [ug:unit-of-work-story-map.md]（S-2 AC 11–13）；元件分層引自 [ad:components.md]；[US:S-6 AC 3] 的逐 intent 要求引自 `stories.md`。

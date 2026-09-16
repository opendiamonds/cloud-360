# Code Generation Questions — U-7 對帳 workflow 與編排器

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-7-reconcile-workflow · kind: service -->

## Q1（阻塞，開工前查證發現）— U-6 新增的 `last_written_status` 對 R-6 的影響

**Question**: U-7 的 R-6.1／R-6.5 逐字要求補平後回寫 `last_status`／`last_field_value`／`last_reason_code`，並明文說明其語意是「**記錄「機制上次寫進看板的值」**」。

但 U-6 的 code-generation（reviewer iteration 2 Critical 的修法）已把該語意**拆成兩欄**：`last_status` 改記「上一輪的**判定**」，新增 `last_written_status` 記「上次真的寫進看板的值」，而 **U-6 的 `write_status` 的 `expected` 讀的是後者**。

**後果**：U-7 若照字面實作，補平後只寫 `last_status`、不寫 `last_written_status` ⇒ U-6 下一輪的 `expected` 仍是補平**之前**的舊值 ⇒ 與剛被補平的看板不符 ⇒ **`Aborted` ＋ 假通報**。**這正是 R-6 這一整群存在的唯一理由**（其背景段逐字：「補平愈成功、假通報愈多」）——U-6 的修法從另一側把它重新打開了。

reviewer 未抓到此點：U-6 的兩輪審查都只審該單元，這是**跨單元的後果**。

- **A. U-7 的 R-6.1／R-6.5 兩欄都寫** — 補平時本單元**確實寫了看板**，所以「判定」與「寫進去的值」在那一刻本來就相同，兩欄同值是語意上正確而非將就。代價：擴充 U-7 已核可規則的字面，需標出並指派 Bolt 1 gate 追認
- B. 退回 U-6 的兩欄分家 — 會讓 iteration 2 的 Critical（不收斂、每次 push 產生真實 commit）或原本的假 `Aborted` 回來，兩者必取其一
- C. 先停，把 schema 決定交給 gate — 最保守，但擋住剩下四個單元的進度

[Answer]: A. U-7 兩欄都寫 <!-- 2026-09-05T15:14:57Z, via AskUserQuestion -->

## Plan Approval

[Answer]: Approve Plan <!-- 2026-09-05T15:16:47Z, via AskUserQuestion -->

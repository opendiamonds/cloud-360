# Integration Test Instructions — AI-DLC ↔ GitHub Projects 同步機制

<!-- Stage: build-and-test（Construction）· Test Strategy: Standard -->

## 這一層為什麼不能自動跑

離線層（`unit-test-instructions.md`）用 PATH shim 偽裝 `gh`。本層**不偽裝**——它對真實的
`opendiamonds/cloud-360` 與真實的 Projects v2 看板發出寫入。逐支的實際寫入面：

| 套件 | 它會在真實 GitHub 上做什麼 |
| --- | --- |
| `aidlc-sync-board/run-live-tests.py` | 對測試看板 **#23** 寫 Status／自訂欄位；改動並還原 issue **#538** 的 body |
| `aidlc-sync-record/run-live-tests.py` | 建立、推送、刪除一次性分支 `aidlc-sync/test/<utc-ts>` |
| `aidlc-sync-notify/run-live-tests.py` | 在正式 repo **建立並關閉真的 issue** |
| `aidlc-sync-forward/run-live-tests.py` | 對 #23 跑完整條寫入鏈；git 那一半走本機 bare repo |
| `aidlc-sync-selftest.yml` 第二段 | 在正式 repo 開一則真 issue，並因此**觸發 `issue-triage`（gh-aw／LLM）** |

**因此本階段沒有執行它們，也不建議由 agent 自行執行。** 它們需要一次明確的人工授權，
連同憑證鑄造一起裁決（U-3／U-9 的交還清單都指向同一個 Bolt 0 gate）。

## 三層防呆（跑之前先確認它們還在）

這一層之所以「可以被授權」而不是「不能碰」，靠的是實作者寫進 runner 的防呆。授權前
逐一複驗：

1. **看板隔離**：`board.sh` 與 forward 的 live runner 進場即斷言
   `AIDLC_PROJECT_NUMBER != 16`，不符 **exit 4**。同一份憑證同時寫得了正式看板 #16 ——
   **隔離只靠這個設定值，不靠權限**（ADR-0016 §3）。
2. **分支隔離**：record 的 live runner 有三層——(a) 進場斷言分支名以 `aidlc-sync/test/`
   開頭，(b) git shim 對每個 `push` 斷言 argv 含 `refs/heads/aidlc-sync/test/`，不含即
   exit 97，(c) `ut` 拒絕案在 origin URL 指向不存在路徑的 clone 內執行。
   這三層是**對平台的兜底**：`ut` 的 `enforce_admins: false` 而憑證為 admin，直推 `ut`
   平台不會擋。
3. **憑證缺席不靜默**：五支 runner 全部在拿不到憑證時 **exit 3** 並印 `SKIP：…`，
   不是回 0。**`exit 3` 不是失敗，是「這一層沒被驗證」的明確聲明**——把它讀成綠燈
   等於把未驗證當成已驗證。

## 執行方式（取得人工授權之後）

```bash
export AIDLC_PROJECT_NUMBER=23          # 絕不可為 16
export GH_TOKEN="$(gh auth token)"

python3 .github/actions/aidlc-sync-board/run-live-tests.py
python3 .github/actions/aidlc-sync-record/run-live-tests.py
python3 .github/actions/aidlc-sync-notify/run-live-tests.py
python3 .github/actions/aidlc-sync-forward/run-live-tests.py
```

退出碼語意（五支一致）：`0` 全綠／`1` 有失敗／`3` 未執行（缺憑證或無權限）／`4` 拒絕
執行（防呆條件不成立）。

### 憑證需求

`repo` ＋ `project` scope 的擁有者 token。**`repo` scope 整包涵蓋 contents／issues／PR
寫入，沒有更細的收斂手段**——這是 ADR-0016 把寫入身分由 GitHub App 改為擁有者 token 的
代價，`requirements.md` 的 OQ-1（把 repo 內容寫入權收斂到最小）候選手段幾乎耗盡。

## 跨單元的整合面（本層真正要驗的東西）

離線層驗得了每個單元自己，驗不了單元之間的契約。本層的價值集中在四條：

| # | 整合點 | 為什麼只有真實環境驗得到 |
| --- | --- | --- |
| L1 | `gh pr list --json number,state,closedAt,mergedAt,files` 的欄位集合合法 | stub 的 `gh` shim 永遠不會反對任何欄位名；寫錯欄位名會讓 R-2.5 的 fail-closed 每一輪都觸發 |
| L2 | 真實 GraphQL 回應形狀跑得完整條寫入鏈（`write_status`→`write_field`→`write_body`→`read_item`） | 回應形狀是 GitHub 的，不是我們定的 |
| L3 | **R-5.4 雜湊等價性**：U-6 回寫的 `managed_block_hash` 必須等於 U-8 對 GitHub 實際存下來的 body 重算的雜湊 | ADR-0015 §10 點名這是最危險的失敗模式；GitHub 對 body 是否做正規化，只有打過才知道 |
| L4 | issue 列舉的最終一致性 | **已由本 intent 實測推翻上游主張**：`gh issue list --label` 與 REST label 過濾**都是最終一致**（t=3.6s 看不到、t=5.9s 才看到），不是即時狀態 |

L4 對「連續兩輪」型完成判準有一個未被寫下的前提：**兩輪的間隔必須大於該視窗**。
產品行為不需要改（ADR-A8 的自我收斂涵蓋它），但判準的措辭有這個隱含條件。

## 明知不涵蓋的整合面（如實列出）

| 缺口 | 為什麼 |
| --- | --- |
| `main` 半邊的平台拒絕（GH006） | 驗它需要對 `main` 發真實 push；一旦保護設定有閃失，落地的是一則機器 commit 在 `main` 上。**只有 stub 涵蓋，無 live 反例** |
| U-3 的 R-2.4 競態視窗 | 重現需精準時序，無可構造的 live 反例；已由 ADR-0015 §2 綁進 Bolt 1 gate 的揭露項 |
| U-3 的 R-1.4 多筆分支 | 無可構造的 live 反例（ADR-0016 §6）；只在 stub 層驗，**不發明假的 live 觸發途徑** |
| 憑證做範圍外寫入回 403（U-9 完成判準③） | 在組織層授權下恆不發生——這是一條**不可達**的判定，只有 stub 證據 |
| 「CI 紅燈」本身 | 需要真實 PR 觸發 |

最後一列與第四列值得分開讀：**第四列不是缺工具，是那個狀態在本系統的資料流下走不到**。
把不可達的分支寫成「待補測試」會讓下一個人去補一個永遠不會綠也不會紅的東西。

## 與上游的對應

五支 live runner 的寫入面、退出碼語意與防呆層引自各 runner 的模組 docstring（本站實讀），其中「憑證缺席不得靜默跳過」的退出碼要求逐字來自 U-3／U-4／U-5 的 `code-generation-plan.md`（board 為 Step 8、notify 與 record 為 Step 7）；
看板隔離與擁有者 token 的代價引自 ADR-0016 §3／§4；`ut` 的 `enforce_admins: false` 與
憑證 admin 身分引自 U-4 的 `code-summary.md`；L1〜L3 引自 U-6 `run-live-tests.py` 的
stub／live 分工節；L4 的實測引自 U-5 `run-live-tests.py` 的模組 docstring；不可達的
403 判定引自 U-9 的 `security-requirements.md` 缺口 Q-1。

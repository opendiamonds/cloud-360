# 安全需求 — U-8 反向同步 workflow

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-8-reverse-workflow · kind: service -->

## 缺口 P-1：NFR-S1 的權限集合是**四項**，不是三項

`requirements.md` 的 NFR-S1 把「**開 PR（FR-G1）**」列為「repo 內容寫入」這一項的用途之一。**這在 GitHub 的權限模型中不成立**——推分支與開 PR 是兩個獨立權限。

**本 repo 自己的機器可查反證**（`.github/workflows/deploy.yml:174-175`）：

```yaml
      contents: write        # push the revert branch
      pull-requests: write   # open the revert PR
```

該 job 做的正是本單元要做的事——推一個分支、開一個 PR——而它必須**同時**宣告兩項，且註解逐字說明各自對應哪個動作。這不是推論，是這個 repo 上正在運行的設定。

**這與缺口 K-1 是同一類錯誤。** ADR-0014 已抓出「Issues 寫入獨立於 Contents」，但沒有檢查同一個句子裡的另一個歸併：「開 PR」同樣被歸進了 Contents。**修正一個歸併錯誤時沒有掃描同型的其餘部分**，是 K-1 的處置留下的缺口。

| # | 權限 | 需要它的動作 | 現行 NFR-S1 有無 |
| --- | --- | --- | --- |
| 1 | 組織層 Projects 讀寫 | 讀寫看板 item | 有 |
| 2 | repo 內容寫入 | 寫 `sync-state.json`、推分支 | 有 |
| 3 | Issues 寫入 | 通報 issue、讀寫受管區塊 | 有（ADR-0014 補入） |
| 4 | **Pull requests 寫入** | **開反向 PR（FR-G1）** | **無** |

**後果與 K-1 逐字相同，且更晚才會爆**：PRE-1 第 1 項若照 ADR-0014 只實測三項，會通過；缺第 4 項要到 **Bolt 3** 第一次真實執行反向同步時才失敗——比 K-1 的 Bolt 1 又晚了兩個 Bolt。而 ADR-0014 自己的 Risk 段寫明「權限一旦鑄出並安裝於組織層，變更需要組織管理者操作（E-1）」。

**處置**：本站不改已核可的 NFR-S1 與 ADR-0014，標出缺口並指派——**該新 ADR 已存在：ADR-0015 §8 的「附帶」段逐字承載本缺口**（權限實為四項，`deploy.yml:174-175` 為本 repo 上正在運行的佐證）。送審前自檢遷移，2026-08-29T23:42:35Z。**確認人維持 Bolt 0 的 gate**。指派目標非 CONDITIONAL stage，無 `units-generation:260822-ug-L2` 所指的無聲落空風險；但它**必須在鑄憑證之前**生效，這才是急迫性所在。

## 本單元的權限使用面

| 項 | 判定 |
| --- | --- |
| IAM | 本單元用到上表**全部四項**。**先前寫「不需要第 3 項（Issues 寫入）」，已被本 stage 自己的改動推翻**（2026-08-30T01:31:09Z，reviewer iteration 4 Group B M-5）：ADR-0015 §5 為反向路徑補上 C-5，本單元的 R-4c 因此新增 `notify` 呼叫，而開通報 issue 需要 `Issues: write`。與 U-3 的 SEC-2、U-4 的 SEC-1 記載的「單元拿到的權限大於它需要的」仍一致——無機制限制各單元只用自己那一份 |
| Encryption | 沿用 NFR-S4：僅 GitHub API 的 HTTPS，本單元不落地任何含機敏內容的檔 |
| Network exposure | 沿用 NFR-S5 不適用：無監聽、無端點，全部是出站呼叫 |
| Audit logging | 反向 PR 本身即紀錄——誰改的、改成什麼、何時，都在 PR 的 diff 與 metadata 內。**這是本單元相對於正向路徑的優勢**：正向靠 workflow log，反向靠 PR |

## 一項不得被靜默降級的邊界

`business-rules.md` 的 R-2.1 說明，在 E-1 的裁定下 PR 的 diff **結構上**只含 `sync-state.json`。**但結構性成立不免除斷言義務**——[US:S-6 AC 2] 逐字要求檢視 diff 不含 `aidlc-state.md` 任何一行。若未來有人擴大本單元的寫入範圍，沒有任何東西會失敗。斷言落點為 U-9，本站不裁定其形式。

## 既有技術堆疊的承接

NFR-S2 要求本 intent 的憑證是**獨立 secret**。[ck:technology-stack.md] 的 gh-aw 專節記載既有 11 支 workflow 已同時掛四個不同的 token secret（`COPILOT_GITHUB_TOKEN`、`GH_AW_GITHUB_MCP_SERVER_TOKEN`、`GH_AW_GITHUB_TOKEN`、`GITHUB_TOKEN`）——**多憑證併存的接線在這個 repo 已是既成事實，不是本 intent 要新開的路**，NFR-S2 的「獨立 secret」因此是沿用既有形狀而非新增機制。

## 與上游的對應

NFR-S1～S6 與 FR-G1 引自 `requirements.md`；PR 的寫入邊界與 R-2.1 的「結構性成立仍須斷言」引自本單元的 `business-rules.md`；反向 PR 的產生時機與 `pending_reverse` 的寫入引自本單元的 `business-logic-model.md`；權限集合的三項現況與 K-1 的處置引自 ADR-0014；本 repo 既有的 gh-aw／CI 堆疊事實引自 [ck:technology-stack.md]（`aidlc/spaces/default/codekb/cloud-360/technology-stack.md`）。

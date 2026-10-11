# Code Generation Questions — `U1 brain-infra`

## 前言：本站不重問的事

下列事項已由上游核可，**本站不重問**，逐項可引用到具體定案：

| 已定案 | 出處 |
|---|---|
| 記憶體上限六個服務全設、值先以公開基準設定並限期複量 | `[I2]`=C ＋ `[I2b]` 反轉（`infrastructure-design-questions.md` 的反轉紀錄表） |
| `maxmemory` ＋ `allkeys-lru`，承載為 compose `command:` | `[I1]`=A ＋ 審查 R-05 |
| 不引入監控堆疊，改加 healthcheck | `[I3]`=D |
| `logging:` 加在全部服務 | `[I4]`=A |
| CI test stack 不起 Ollama，`EMBEDDING_PROVIDER=stub` | `[I5]`=A |
| `networks:` 分段、`cloudflared` 不得進 `internal` | `nfr-design` D-3 |
| 主機層全碟加密、dump 檔三條要求 | `nfr-design` D-1／D-4 |
| 探測契約七條（`P-1`…`P-7`） | `nfr-design` `PROBE-CONTRACT` |
| 22 列改動清單的每一列落點與依據 | `cicd-pipeline.md` `§五` |
| 不做 `§六` 補閘門 (a)–(d) | `infrastructure-specification.md` `§六` 明文列為不屬本單元交付 |

## Plan Approval

**待核可的內容**：`code-generation-plan.md`（含其中內嵌的 Testing Contract）與
`unit-test-instructions.md`。

**核可後會發生什麼**：委派 `aidlc-developer-agent` 依計畫的 15 個步驟實際改動工作區——
包含兩份 compose、根 compose、`render-env.sh`、兩份 `.env.example`、`deploy.yml`、
`schema_rbac.sql`、`backend/database.py`、`DEPLOY.md`、`LOCAL-DEV.md`，並新增兩支測試檔。

**核可前請特別看三件事**（它們是本計畫與一般 code-generation 最不一樣的地方）：

1. **測試覆蓋面是窄的，而且我在計畫裡寫明了窄在哪**。本單元只有兩個元件有受測對象
   （vector extension 的呼叫順序、`render-env.sh` 的退出行為），合計 11 個新測試。
   compose 的服務集合、`networks:` 分段、記憶體上限、`logging:`、`healthcheck`、
   `deploy.yml` 的探測步驟**全部沒有自動化斷言**——`§六` 已把那四道補閘門列為不屬本單元交付。
2. **`AC2.1.4` 不會被本單元的測試驗證**。本單元只交付儲存層的持久化能力；「重啟後脈絡完整還原」
   取決於 `U10` 寫了什麼、`U14` 讀了什麼。計畫裡逐字寫了這條界線。
3. **第 14 步（`gh api` 複查新 secret）需要 repo 寫入權與 `gh` 認證**。若執行環境無法查，
   計畫要求記為未完成項並在摘要明說，不得靜默跳過——本 repo 為 public、Actions log 公開可讀。

<!--
再次取得核可的原因（2026-10-05，conductor 記）：

本計畫先前已由使用者核可，原紀錄為：

    Approval Fingerprint = sha256:v3:b5dbdc7961b9a95299b5d0b8ec594f9b0ed70e7984eeecd9af97914e44e3ae51
    Planned Source       = 135209658be073ed968dfe2e985c33867d41f12cfaf17b0817ac48e5760a35eb
    答覆                 = Approve Plan

（上面三行刻意不寫成 tag 形式：Plan Approval 的登記檢查要求全檔
恰有一個 `[Answer]:` 行，歷史紀錄若保留 tag 形式會讓它數到兩個。）

該核可之後，本單元的實作、對抗式審查六項處置與 conductor 覆核**全部完成**
（見 `code-summary.md` §三／§六／§七）。`code-generation-plan.md` 與
`unit-test-instructions.md` 自核可起**位元組未變**——以 `git status` 核對，
本目錄零修改，兩檔皆為已提交狀態。

重取核可**不是因為計畫內容改變**，而是引擎的核可綁定已失效：
`plan-approval-guard` 回報 fingerprint 與「active intent、target、stage attempt、
plan、test instructions、Testing Contract」的現值不符，而 fingerprint 涵蓋
stage attempt 與 Testing Contract 雜湊（兩者皆非本檔內容）。綁定失效期間，
守衛拒絕全部工作區改動與全部指令執行，連 `park` 與 `--doctor` 都被拒。

**核可後不會重跑實作。** 13 個檔的改動與兩支測試檔已在工作區內；
conductor 將逐項複驗落地狀態後登記本站完成，不重新產生程式碼。

此處保留原紀錄，是為了讓「本計畫曾被核可過一次」可追溯——
依 stage 檔的修訂規則，`[Answer]:` 必須先清空才能重新產生 fingerprint。
-->

[Approval Fingerprint]: sha256:v3:d28dfe13b1c8be3480fcebb50a2a40ff0cb5d12e4c89f1c89671a01b94e2d077
[Planned Source]: 060351af583bd73506f4750b02b7071ca4498a048a1e4148670f342a53917c52

- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan

[Answer]: Approve Plan

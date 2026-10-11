# Code Generation 問題檔 — `U24 member-pages-ui`

> 本檔承載 Plan Approval 的核可問題與兩個綁定標籤。
> **標籤刻意不寫進 `code-generation-plan.md`**：指紋覆蓋計畫全文，
> 把標籤寫進計畫會讓它自我指涉而永不收斂（`U11` 那站實證出三個不同值才查出原因）。

## 一、本站不重問的事（上游已定案）

| 事項 | 定案 | 出處 |
|---|---|---|
| 橫幅掛載層與取值時機 | `[F1]`=A、`[F2]`=A | `nfr-requirements` |
| 就地更新 vs 重抓 | `[F4]`=A | 同上 |
| 清單上限與超過時的行為 | `[N1]`=A（100 列，來源 `MAX_PAGE_SIZE`） | 同上 |
| 橫幅是否快取 | `[N2]`=A（不快取） | 同上 |
| 錯誤訊號 | `[N3]`=B ＋ 審查 `R-07` 的兜底規則 | 同上 |
| live region 由誰建 | `[N4]`=A（`U24` 自建，`U23` 沿用） | 同上 |
| live region 的形狀 | `[ND1]`=A（每頁各掛一個、props 驅動、`role="status"` 寫死） | `nfr-design` |
| `canManage` 的判定 | per-project `role` **AND** `can("K3","edit")`（審查 `R-01`） | `nfr-design` §一之三 |
| 掛載機制 | 直接渲染於 `Layout.tsx`，不走 `slotRegistry` portal（審查 `R-07`） | `nfr-design` §三之一 |
| 測試方法論與量級 | Testing Contract：`test-after`、`standard` | `code-generation-plan.md` 的 `## Testing Contract` |

## Plan Approval

**要核可的對象有三份，缺一不可**：

1. `code-generation-plan.md` 的 14 個步驟與其 story 追溯（§三、§五）
2. 該檔內嵌的 `## Testing Contract`（`contract_sha256: sha256:1f0b6822…3f2f77`，
   方法論 `test-after`、strategy `standard`）
3. `unit-test-instructions.md` 的 8 個 e2e 案例、本單元專屬執行指令與 mock 指引

**計畫摘要**（完整內容見該兩檔）：

- **交付 10 項**：`<LiveRegion />`（新建，供 `U23` 沿用）、抓取函式層、失敗訊號型別、
  成員清單頁、成員詳情頁、邀請對話框、交棒橫幅、`Layout.tsx` 掛載、路由與 Sidebar 入口、
  一支 e2e spec。
- **唯一要改的既有共用檔是 `Layout.tsx`**（22 行），改動後所有頁面共用它——
  失敗域因此是全域，這點已在設計階段寫明。
- **方法論 `test-after`**：逐層實作後補該層測試。本單元只有「Frontend behavior」
  一個適用層（data model／repository／API endpoint 皆屬 `U19`），故步驟數比
  contract 的 14 步基線少，但**方法論未改**。
- **8 個 e2e 案例**逐一對應 `cicd-pipeline.md` §五 的斷言標的，含審查 `R-01` 查出的
  「per-project admin 但缺 `K3.edit`」壞狀態——缺那一條，死循環不會被任何閘門抓到。
- **已知不可完成的部分**：`AC12.2.2` 的變更紀錄**取不到資料**（`OPEN-MP24-7`：
  六個端點與 13 個 facade 方法都沒有讀取路徑）。計畫 Step 9 的處置是渲染一個
  明確的「尚無法取得變更紀錄」佔位並在註解指向該 open item——**不捏造資料、
  不留空白區塊**，也不自行擴充 `U19` 的端點。
- **零新依賴、零新環境變數、零 schema 變更、零管線改動**（三項皆已實測，
  見 `infrastructure-specification.md` §一 與 `cicd-pipeline.md` §一）。

[Approval Fingerprint]: sha256:v3:db68e8167729d8acd2b2d580f64fc762f7f0e17a9a9ca0a44836a28b1980c329
[Planned Source]: 9de4140d8296a3ee4f29179c4d3cdcad403cb62f1b55c6a83ef044d8259c531f

- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan

[Answer]: Approve Plan

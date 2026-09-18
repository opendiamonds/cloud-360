# 安全需求 — api-type-contract（U5）

> Stage: nfr-requirements（Construction 3.2）· Unit: `api-type-contract`（C-8）
> Kind 為 `packaging`：本單元**完全在建置期**，不進生產環境的執行路徑，不部署。

> **上游輸入**：`../../../inception/application-design/components.md` 的 **C-8**（四個組成、兩道 gate、兩項位置約束、版本釘選）與 `decisions.md` 的 **AD-9**。本單元 kind 為 `packaging`，其行為完全由 C-8 界定，故**沒有**自己的 `functional-design/`（該階段的 `produces_kinds` 對 `packaging` 不產出 business-logic-model／business-rules）—— 這是 kind 的直接後果，不是缺漏。
> `service` kind 的效能／擴展性／可靠性文件矩陣對它**不適用**（判定與理由見 `tech-stack-decisions.md`），故本單元只產出安全與技術選型兩份。

## ADR-0006 四面向逐項判定

| 面向 | 判定 | 影響與處置 |
|---|---|---|
| **IAM** | **不適用** | 本單元不觸及角色、權限或任何授權路徑。產出物是規格檔與型別檔 |
| **Encryption** | **不適用** | 不處理憑證或個人資料；產出物是 API 形狀的描述，不含任何資料值 |
| **Network exposure** | **適用 —— 這是本單元唯一、也是最重要的安全面** | 規格檔是**完整的 API 地圖**（**本 intent 落地後實測為 36 個 path、29 個 schema、68,951 bytes** —— schema 由 28 增為 29 是新增的 `UserListPage`；28／約 66 KB 為 Revision 1 之前的值），含全部使用者管理與權限端點。它必須**不可被未認證訪客取得**。處置見下方 S-1 |
| **Audit logging** | **不適用** | 建置期資產，無執行期行為可記錄 |

## S-1 規格檔與型別檔不得落在會被靜態服務原樣供出的路徑

| 項目 | 內容 |
|---|---|
| 威脅 | `frontend/nginx.conf` 為 `root /usr/share/nginx/html` ＋ `try_files $uri`，而 Vite 會把 `frontend/public/` **原樣複製**進 `dist/`。規格檔若落在那裡，`https://<公開網域>/<檔名>` 會把完整 API 地圖對**未認證訪客**公開，且 nginx 已對 JSON 開 gzip |
| 現況（必須維持） | 後端自帶的規格端點在公網**不可達** —— nginx 只反向代理 `/api/`。本單元**不得破壞這個既有狀態** |
| 契約 | 規格檔置於 **repo 根目錄**（與 schema 檔、部署文件同層）；型別檔置於 `frontend/src/` 內。兩者**皆不得**置於 `frontend/public/` 或任何會被靜態服務原樣供出的路徑 |
| 為何這個形狀天然安全 | 規格檔在 repo 根 → 不在前端映像的 build context 內，不可能進 `dist/`；型別檔在 `src/` 內 → 會被 TypeScript 編譯掉，不以原始形式進入 bundle |

**驗證（reviewer Minor 2 後補上）**：`dist/` 產出物中不得出現規格檔檔名。此斷言原本只是「可機械檢查但沒人執行」，已於 CI 的 frontend job 補上實際的檢查步驟（`Spec must not be served statically`，在 `npm run build` 之後對 `dist/` 搜尋 `openapi*`）。**已以刻意違反實測**：把規格檔複製進 `dist/` 後該檢查確實命中並會 `exit 1`，移除後回到通過。「天然安全的形狀」因此由設計上的性質升格為**機械保證** —— 日後若有人把規格檔搬進前端樹，CI 會擋下。

## S-2 產生器只得輸出型別宣告

型別產生器**只得輸出型別宣告**（`.d.ts`），不得輸出任何會進入 bundle 的執行期程式碼。理由：進 bundle 的程式碼會擴大前端的攻擊面，而本單元的價值完全來自編譯期。

**現況**：採用的產生器輸出純 `.d.ts`，符合此約束。

## S-3 新增的建置期工具不進執行期依賴

型別產生器以**釘住版本的一次性執行**方式呼叫（`npx --yes <generator>@<exact-version>`），不列入 `dependencies`，因此不進生產 bundle。

> **與原設計的偏離（如實記載）**：application-design 的 C-8 原本假設它會成為 `devDependency` 並一併 commit 依賴鎖定檔。實作時發現本專案的 TypeScript 版本與該產生器宣告的 peer 範圍不相容（peer 要求 `^5.x`，專案為 `~6.0.2`，**目前沒有任何已發佈版本支援 TS 6**），`npm install` 直接 `ERESOLVE` 失敗。三個選項中選了成本最低且不說謊的一個：不加依賴、以釘住版本的 `npx` 呼叫。代價是產生器的**傳遞依賴不進 lockfile**；緩解是產生器自身的版本被精確釘住（且在兩處 —— `package.json` 的 `gen:types` 與漂移檢查腳本內的常數，兩處必須一致，否則 gate 會比對到不同產生器的輸出而誤報）。**與上游 AD-9 的交叉註記**（reviewer Minor 3）：AD-9 的 Consequences 段仍逐字寫著「新增一個 devDependency（這正是 AD-5 原本要避免的）」，而最終實作**沒有**新增 devDependency。依 `project.md ## Corrections` 的既有規則，下游不回改已核可的上游 artifact —— 此處明記該項後果**已被本站的實作取代**，讀 AD-9 時應一併讀本節。附帶結果：AD-5「不引入新依賴」在實作上比 AD-9 預期的**更完整地**成立。

另兩個被否決的選項：`--legacy-peer-deps`（會改變**整個 repo** 的安裝語意，影響面遠大於本 feature）、`overrides` 強制 peer（等於宣稱一個未經驗證的相容性）。

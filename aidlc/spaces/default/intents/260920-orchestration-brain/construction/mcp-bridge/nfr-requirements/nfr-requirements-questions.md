# NFR Requirements 問題檔 — `U21 mcp-bridge`

> 撰寫時間 2026-10-14T16:20:16Z（`date -u` 取值）。本單元是 `service`，五個 NFR 類別**全部適用**。
>
> **本站出題數為 1（`[MBN1]`）。** 逐類查過之後，其餘關鍵取捨若不是上游或本單元 functional-design 已定案、就是可由 repo
> 現況直接查證、或屬可隨時調整的常數（改值不構成重工）。唯一出題的一項，是 functional-design 標明「使用者於本站核可關卡裁決」、
> 但**查不到任何作答紀錄**的 `OPEN-MB21-14`：不論選哪一個方向，都會改寫或收窄一條已核可上游字面（`requirements.md:620` ③），
> 依 `project.md`，推翻或收窄上游定案只能由使用者裁決。先例為 `U13 brain-gateway` 的同一站（1 題）與 `U12`、`U15`、`U20`（皆 0 題）。

## 〇、不重問的事（已定案或可查證，附出處）

| 類別 | 事項 | 定案處 |
|---|---|---|
| 安全 | token 只走每次請求的 `Authorization` 標頭、用完即棄、不解碼 JWT | `[MB2]`=A；`BR73.1`–`BR73.5` |
| 安全 | agent 身分以 `X-Cloud360-Agent` 宣告、自報不可驗證 | `[MB3]`=A；`BR74.1`–`BR74.5`；`OPEN-MB21-2`（新 ADR 承接） |
| 安全 | 第一版只開三個工具、成員管理類結構性排除 | `[MB4]`=A；`BR72.2`、`BR72.11` |
| 安全 | 工具屬性 `field_key` 改名為 `field`，黑名單底線維持子字串比對 | `[MB6]`=A；`BR72.5` |
| 安全（Encryption） | **`OPEN-MB21-13` 的「`internal` 橋接網段上的明文 HTTP」**：不出題。容器間明文、信任邊界為 compose network 本身已由使用者裁決為 `[G2]`=A（`brain-infra` `nfr-design-questions.md:90`，作答 `:103`，2026-09-27T00:39:01Z 經選單）；且 `[I6]`=A 的「本題定案的效力」逐字寫「Encryption 面依 `OQ-16` 逐字『HTTP／SSE 須本機迴環或加密』→ 本案以 **`internal` 網段、不發佈 `ports:`** 滿足」（`brain-infra` `infrastructure-design-questions.md:299-303`，作答 2026-10-03T12:47:03Z 經選單）。functional-design 的 `OPEN-MB21-13` 是把同一決定的代價（JWT 8 小時、與 `redis`／`ollama`／`db` 共網段）寫得更誠實，**不是新的決定**；且同形的明文 JWT 傳輸今天已存在於主請求路徑（`frontend` 的 nginx 經 `edge` 網段反代至 `backend:8000`，`deploy/docker-compose.deploy.yml:362-365`）。本站在 `security-requirements.md` 以 `[G2]`／`[I6]` 為依據結案，並於核可關卡揭露殘留 | `[G2]`=A；`[I6]`=A |
| 技術棧 | `mcp` 依賴與 FastAPI 釘選的退路順序（第一順位同一 `requirements.txt` → 較舊版本 → 獨立 virtualenv → 升 FastAPI 須另開題） | `functional-spec.md` §十二 第 1 步（`:335` 起）、H-5（`:297`）；functional-design 核可時一併核可；`OPEN-MB21-15` 為其揭露 |
| 技術棧 | Python ＋ 官方 `mcp` SDK、沿用 backend 映像；`unittest`＋`hypothesis`，非 pytest | `[MB5]`=A；`team.md ## Testing Posture` |
| 部署 | compose 第七服務、`internal`、無 `ports:`、零環境變數 | `[I6]`=A；`BR71.1`、`BR71.2`；H-1、H-6 |
| 可靠性 | backend 不可用只讓該次呼叫失敗、不重試、逾時 3／10 秒；設定錯誤致命 | `BR71.4`、`BR71.5`、`BR75.1`；D-12 |
| 觀測 | log 欄位白名單、logger 命名、禁含項 | `BR77.1`、`BR77.2`；`team.md ## Code Style` |
| 觀測 | bridge log 與 backend log 的關聯鍵（`OPEN-MB21-9`） | 已指派 `nfr-design`（→ `code-generation`），本站不搶答 |
| 帶入項 | functional-design `review-02` 的 11 項（`R-11`–`R-21`） | 使用者 2026-10-14T16:16:10Z 裁決「核可，11 項帶進寫程式」（`carried-review-items.md`）；本站把其中可驗證者（`R-11`、`R-13`、`R-14`、`R-15`、`R-18`、`R-19`、`R-20`）轉為 NFR 判準，不重開設計 |
| 範圍 | 大腦側 MCP client 不存在（`OPEN-MB21-1`） | `[MB1]`=A；交回後續 intent 的 `scope-definition`；非 NFR 題 |

## 一、刻意不出成題目的事（附理由）

1. **`OPEN-MB21-10` 的頻率、並發與本體大小上限**：指派本站。皆為模組常數或啟動參數（`BR71.1` 規定設定全走命令列），改值是一行 diff，
   不構成重工；逐條查過 `requirements.md` 的 `NFR1`–`NFR11` 與 `X-04`，無任何已核可文字對 bridge 的上限有字面要求，故定值不牴觸上游。
   且本版**沒有任何實際 client**（`OPEN-MB21-1`），量測不到真實負載——出題請使用者挑數字是假選擇。數字與算式寫在
   `scalability-requirements.md`，於核可關卡揭露。（與 `U13` 的同站處置一致：全域常數不出題，只有「會改寫已核可上游字面」的上限才出題。）
2. **延遲預算數字**：本 repo 無延遲量測機制，數字是預算不是預測；量測落 `build-and-test`。bridge 多出的只是一次同主機 HTTP 往返，
   逾時上限已由 `BR75.1`（3／10 秒）定死。
3. **可用性 SLO 的百分比**：bridge 本版無實際 client，對使用者不可見；`restart: unless-stopped` 與 `/healthz` 已定（H-1、H-2）。
   以「不得成為 backend 的故障源、backend 故障不得使 bridge 退出」兩條可二元判定的需求代替百分比，理由寫在 `reliability-requirements.md`。
4. **`R-11` 的選路（第一順位 vs 獨立 virtualenv）**：選路是 `code-generation` 第一步的實測結果（§十二 第 1 步），不是偏好題；
   本站只把「不論選哪條路，`T-1`／`T-2`／`T-4`／`T-8` 都必須在 CI backend job 內可執行」寫成判準。
5. **`OPEN-MB21-13`（Encryption）**：見〇，已由 `[G2]`=A 與 `[I6]`=A 定案。

## 二、問題

### [MBN1] agent 經 MCP **成功讀取**需求欄位時，要不要留下「是哪位使用者讀的」紀錄？

**背景**：上游 `requirements.md:620` ③ 逐字要求「MCP 工具呼叫的稽核主體必須是**使用者本人**而非大腦服務帳號」。functional-design
查出它在**寫入與清空**成立（`updated_by`、facade 的變更 log，`BR77.3`），在**成功的讀取**不成立：需求欄位的 facade 只對**被拒**
的讀取記一行帶 `user_id` 的 WARNING（`backend/services/requirement_field_facade.py:272`），成功的 `read_fields`（`:301-305`）
什麼都不記——這是既有行為，**使用者直接開頁面讀也一樣不記**；而 bridge 刻意不解碼 JWT（`BR73.5`），自己的一行 log 只有工具名、
agent、結果碼、狀態碼、耗時（`BR77.1`），沒有使用者也沒有 `system_id`（`BR77.2` 禁記參數）。functional-design 把它列為
`OPEN-MB21-14` 並標明「使用者於本站核可關卡裁決」，但查遍 audit 與 record **找不到作答紀錄**，故在此補問。

**同 intent 的類似先例**：使用者已就「大腦代使用者呼叫成本功能」裁決 `AC10.2.4`：「授權主體為使用者本人……**不要求成本功能的讀取
端點新增稽核事件**」（`construction/deferred-ac-rulings.md:10`，2026-10-13T22:49:37Z 經選單）。形狀相同但對象不同（成本 vs 需求欄位），
本站不自行比照，交使用者確認。

**使用者實際會遇到的情況**：本版**沒有任何大腦 agent 實際呼叫 bridge**（`OPEN-MB21-1`），所以本版上線後真實的經 MCP 讀取次數是 0；
這題決定的是「日後大腦接上 client 之後，事後追查『某個 agent 讀了誰可見的系統』時查得到什麼」。

A. **（建議）比照 `AC10.2.4`：接受，讀取不新增帶使用者身分的紀錄。** 把 `requirements.md:620` ③ 讀成「凡留下的紀錄，主體都是使用者
   而非服務帳號」——bridge 沒有服務帳號，這一點成立；讀取的稽核程度與使用者直接開頁面讀**相同**（兩者都不記）。上游檔不回改，
   本站產出記為對 ③ 的收窄解讀並引本題作答。
   使用者會遇到的後果：日後若要追查某次讀取，只看得到 bridge log 的「某時刻、哪個工具、哪個 agent、成功」，**不知道是哪位使用者、
   哪個系統**；需要時只能依時間去對 backend 的存取紀錄（也沒有使用者欄位），實務上查不到人。
B. **改 `U20`：需求欄位 facade 的成功讀取記一行帶 `user_id`、`system_id` 的 INFO。** 頁面讀與 MCP 讀都會留下主體，
   `requirements.md:620` ③ 字面完整成立。代價：重開已完成的 `U20 requirement-field-service`（程式、測試、其 NFR 文件與審查），
   須另排一次修訂；每次有人打開需求欄位頁都會多一行 log。本單元不改程式。
C. **只改本單元：backend 回 2xx 之後，bridge 從 JWT 解出使用者 id 寫進自己那一行 log。** 只碰 bridge，不重開 `U20`。代價：
   **推翻已核可的 `BR73.5`**（「bridge 不解碼 JWT、不判斷身分」）；bridge 多一個身分解析器（不驗簽，靠「backend 已接受這個 token」
   當前提），與 backend 的身分來源形成第二份；且只涵蓋 MCP 路徑，頁面讀仍不記。
D. **本版暫時接受，等大腦側 client 真正落地（`OPEN-MB21-1` 的後續 intent）時再決定 B 或 C。** 本版的效果與 A 相同；差別是留下一個
   待決項掛在後續 intent 的範圍定義上。代價：若後續 intent 忘了處理，讀取稽核會在 client 上線後才以真實流量的形式缺漏。

[Answer]: A <!-- 2026-10-14T16:22:38Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

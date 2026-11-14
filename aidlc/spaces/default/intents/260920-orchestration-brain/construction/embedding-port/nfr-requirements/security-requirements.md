# Security Requirements — `U6 embedding-port`（`library`）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: embedding-port · kind: library -->

本單元交付 `EmbeddingPort` 與其三個實作（`ollama`／`fastembed`／`stub`），
**零端點、零畫面、零授權判定、不讀 DB**（K-06 `authorization_responsibility` 逐字
「無——本 Port 不碰授權，亦不讀 DB」）。

但它是**唯一把記憶文字送出 backend 行程的元件**——`ollama` 實作把待向量化的文字
送到一個外部服務。那一條線使本單元的 security 面並非「不適用」，而是本 intent 中
少數真正觸及 `NFR7`「傳輸加密」的地方。

**本檔消費的上游（逐一開檔核對）**：同目錄 `../functional-design/functional-spec.md`
（§一 W1／W2、§五 PBT、§七 四面向）、`../functional-design/rules.md`
（`BR1.*`／`BR2.7`／`BR3.*`／`BR4.*`／`BR6.*`／`BR7.*`）、
`inception/requirements-analysis/requirements.md`（`NFR1`–`NFR11`）、
`inception/contract-design/contract-summary.md`（`K-01`／`K-06`）、
`aidlc/spaces/default/codekb/chiton/technology-stack.md`。

## 一、適用的 inception NFR 與其衍生需求（`NFRx.y`）

| ID | 需求 | 來源 | 可驗證方式 |
|---|---|---|---|
| `NFR3.1` | **`embed` 呼叫落在首字回應路徑上**——這是本站新發現的連動，`NFR3` 的分析未計入它（見第二節）。本單元的義務是把這個事實寫下來並交付一個有上界的呼叫；**達成 `NFR3` 的 P50 ≤ 2 秒不由本單元保證**。 | 本站自檢；`NFR3` | 本檔第二節的連動說明；量測落點 `build-and-test`（3.6），與 `NFR1`／`NFR2`／`NFR3` 同 |
| `NFR3.2` | `ollama` 實作的 HTTP 呼叫**必須帶 timeout**，形式為**具名常數**（沿用 `LENS_AGENT_TIMEOUT_SEC` 的既有形狀，不得寫字面值），預設 **10 秒**，可由環境變數覆寫。逾時歸入既有的 `EmbeddingProviderUnavailable`，**不新增第二種例外**。 | `[Q3]`=A | 模組內 `grep` 不得出現裸數字 timeout；逾時路徑有測試（以不可達位址構造） |
| `NFR4.1` | `ProviderSelection` 存於行程記憶體，但它是**啟動期解析一次的不可變設定**（`BR1.2`），**不是** session 或工作狀態。重啟後由環境變數重新推導，`NFR4` 的可測不變量（「重啟後既有對話的脈絡與作業對象仍可完整還原」）**不受本單元影響**。　**這一列為什麼是 `OK` 而不是 `N/A`（審查 `R-02`）**：同表的 `NFR1`／`NFR2`／`NFR5`／`NFR6`／`NFR11` 之所以 `N/A`，是本單元**根本沒有碰到**那些面（零意圖識別、零 session、零 WebSocket、零 DB、零畫面）。`NFR4` 不同——本單元**確實持有行程記憶體狀態**（`ProviderSelection`），那是一個**看起來會違反**「狀態一律放 Redis，不得放行程記憶體」的具體對象；本列是證明它不違反的那個論證（它是啟動期設定而非 session／工作狀態，且重啟可由環境變數完整重新推導）。**有可能違反而證明未違反＝履行；從未接觸＝不適用。** | `NFR4`；`BR1.2` | 本單元不寫 Redis、不持有任何 per-user 或 per-session 狀態——可 `grep` 斷言（模組內無 Redis client、無 session 型別） |
| `NFR7.1` | 啟動時**必須驗證** `OLLAMA_BASE_URL` 的主機名是 compose 內部服務名：**不得**為 `localhost`、`127.0.0.1`、或任何公開 IP／網域。不通過即啟動失敗（併入 `BR1.3`）。 | `[Q1]`=A；K-01 的 validation 逐字「主機名須為 compose 內部服務名」 | 啟動驗證的單元測試：合法值通過、三類非法值各自拒絕 |
| `NFR7.2` | ollama 服務**不得 publish host port**。此為 `U1 brain-infra` 的交付，本單元**具名為依賴前提**——因為本單元是該服務的唯一消費端，這條約束失效時第一個受害的是本單元送出的記憶文字。 | `[Q1]`=A；K-01 `images_and_services` 的 `exposure` 逐字「compose 內部網路only；不得 publish port」 | `deploy/docker-compose.deploy.yml` 的 `ollama` 服務無 `ports:`（實測：目前整個 deploy stack 只有 `frontend` 有 `ports:`） |
| `NFR7.3` | 記憶文字以**明文 HTTP** 傳輸至一個**零認證**的服務，此為**具名殘餘風險**（`RR-1`），**不得**記為「不適用」。其唯一控制是網段隔離（`NFR7.1` ＋ `NFR7.2`）。**此判定的成立條件是「ollama 與 backend 在同一台主機的同一個 compose 網路內」**——該條件改變時本判定立即失效。 | `[Q1]`=A；`NFR7` 逐字「其靜態儲存與傳輸的加密要求須於設計階段明確」 | `RR-1` 的殘餘風險登記（第三節） |
| `NFR8.1` | `NFR3.2` 新增的 timeout 環境變數**必須在同一個 PR 內**讓 `deploy/render-env.sh` 寫它、`deploy/.env.example` 列它、`backend/.env.example` 列它，並同步更新 `LOCAL-DEV.md`。 | `NFR8`；`project.md ## Mandated`（**blocking**） | `python3 scripts/validate_env_contract.py` 通過 |
| `NFR8.2` | 本單元消費的四個既有變數（`EMBEDDING_PROVIDER`／`OLLAMA_BASE_URL`／`OLLAMA_EMBED_MODEL`／`FASTEMBED_MODEL`）**必須在啟動時真的被讀取並驗證**。`deploy/.env.example:96` 已以**現在式**宣稱「`EMBEDDING_PROVIDER` 缺值會讓 backend 拒絕啟動」，而**實測該宣稱目前為假**：`grep -rn 'EMBEDDING_PROVIDER' backend --include='*.py'` 零個執行期讀取點。本單元的 `BR1.1`／`BR1.3` 即是它的實作。 | `NFR8`；`BR1.1`／`BR1.3` | 啟動驗證測試；落地後該宣稱為真，**不需改那兩個 `.env.example`** |
| `NFR9.1` | 三個實作**皆為本機推論或純函式**，對外部 LLM／API 的花費貢獻為**零**。`ollama` 打的是同主機容器，`fastembed` 是行程內 ONNX，`stub` 無外部呼叫。 | `NFR9`；`deploy/.env.example:115` 逐字「同一台主機上的本機推論，對外部 API 花費貢獻為零」 | 模組內不得出現任何對計費端點的呼叫——可 `grep` 斷言（無 `openrouter`／`anthropic`／`openai` 等字串） |

## 二、`NFR3` 的連動（**把 domain-design 已標記的開放假設精確化**）

`NFR3` 的「與 NFR10 的連動（必讀）」段落逐字寫：

> 這條預算幾乎全部被**路由層的 LLM 呼叫**吃掉。FR4 的 Redis 往返在同一個 compose
> 網路內約 1ms，可忽略；真正的成本是「大腦先判意圖、再交辦」這個兩段式流程的第一段。

**它列舉了路由層 LLM 與 Redis 往返，沒有列舉 embedding 呼叫。** 但
`components.md` 給 `IntentRouter` 的互動逐字是「讀語意與程序記憶以輔助意圖判定」，
而語意記憶的讀取是**相似度檢索**——相似度檢索需要一個查詢向量，查詢向量由本 Port 產生。
所以 `embed` 的延遲**落在首字回應路徑上**，而 `NFR3` 的預算分析沒有它。

**這一條的出處要說清楚，因為初稿把它寫成「本站新發現」是誇大了（審查 `R-01`）。**
`inception/domain-design/components.md:511-514` **已經**把同一個缺口記為開放假設，逐字：
「`IntentRouter` 讀記憶以輔助判定，這條依賴使『首字回應時間 P50 ≤ 2 秒』的預算又多一段
（記憶檢索 ＋ embedding）。`[RA:NFR3]` 明寫該預算幾乎全被路由層 LLM 吃掉，
本站**未重新估算**加入記憶檢索後是否仍可達 [assumption]」。

所以本站的貢獻**不是**發現它，而是把那個 `[assumption]` 精確化為一條具體連動
（指名是 `embed` 呼叫、指名它落在哪一段、指名 timeout 不是它的保護機制），
並給它一個具名的殘餘風險登記與承接對象。**「`NFR3` 的分析未計入它」這半句仍然成立**
——`requirements.md` 的 `NFR3` 本文（`:495`–`:498`）確實只列舉路由層 LLM 與 Redis 往返
——但那是 `requirements.md` 的狀態，不是整個 intent 的狀態。

**本站不自行修改 `NFR3`，也不自行指派**（逕自掛給某個單元就是審查 `R-01` 的形狀）。
處置是登記為 `RR-4` 並具名給 `U8 memory-service`（檢索路徑的擁有者）與
`U11 intent-router`（該路徑的呼叫端）在各自的 `nfr-requirements` 站處理。

**一個必須誠實說出來的推論**：`NFR3.2` 定的 10 秒 timeout 是 `NFR3` 全部預算
（2 秒）的 **5 倍**。這表示 timeout **不是** `NFR3` 的保護機制——它保護的是
「服務掛掉時不要無限期掛住」，不是「這次呼叫夠快」。`NFR3` 的達成靠的是
本機推論在正常情況下的百毫秒級延遲，而那**沒有被任何自動化斷言守住**（見 `RR-4`）。

## 三、具名殘餘風險

| ID | 風險 | 為什麼接受 | 失效條件 |
|---|---|---|---|
| `RR-1` | 記憶文字以明文 HTTP 送至零認證的 ollama 服務 | 同主機 compose 內部網段；TLS 的威脅模型收益低（防的是已能進入該網段的攻擊者）而維運成本（憑證、輪替）高；與 Redis 在同一 stack 的處置一致 | **ollama 移出本主機**，或該服務被 publish port，或 compose 網路被其他非本 stack 的容器加入 |
| `RR-2` | `fastembed` 為使用者自裝、不經 CI 的依賴，首次使用會從 HuggingFace 下載約 1GB 權重 | 只在「本機且無 Ollama」一條路徑上；不進任何 image、不進 CI、不進 staging。把它拉進依賴掃描等於為一條開發者自選路徑建立 CI 基礎設施 | 它被加進 `requirements.txt`，或被用於 staging／CI |
| `RR-3` | **`NFR10` 未由本單元履行，且其承接狀態需要確認** | `NFR10` 逐字把落點指向 `nfr-requirements`（3.2）並寫「若該站被 skip，本工作流程**沒有自然承接站**」——但它講的是**路由層**模型（`typesafe/jev-1.13`），不是 embedding 模型。本站是 `U6` 的 3.2，不是 `U11` 的 | `U11 intent-router` 的 `nfr-requirements` 被 skip（該 stage 為 **CONDITIONAL**）。屆時判定 skip 的執行者**必須把 `NFR10` 重新提交給使用者**，不得靜默落空 |
| `RR-4` | `embed` 延遲落在 `NFR3` 的首字路徑上，而 `NFR3` 的預算分析未計入它；且正常情況的延遲無自動化斷言 | 本站不自行改已核可的 `NFR3`，也不自行指派承接單元 | 具名給 `U8`（檢索路徑擁有者）與 `U11`（呼叫端）的 `nfr-requirements`；量測落點與 `NFR1`–`NFR3` 同為 `build-and-test`（3.6） |

## 四、無對應 inception NFR 的本單元安全需求（`SEC-*`）

| ID | 需求 | ADR-0006 面向 | 可驗證方式 |
|---|---|---|---|
| `SEC-1` | 本單元**不得**讀資料庫、**不得**做授權判定、**不得**新增任何 HTTP 入口。 | IAM | **可機械斷言**：模組的 import 清單中，DB session 型別、`require_story_action`／任何 RBAC 判定函式、FastAPI router 裝飾器三者的 `grep` 結果須為零（與 `project.md` 對 cost 純函式層的可執行檢查同形） |
| `SEC-2` | 任何 log 與例外訊息**不得含憑證**：帶 endpoint 時只帶主機與埠，不得帶 `userinfo` 區段（`http://user:pass@host` 的密碼部分）。 | audit logging / encryption | `BR4.4`／`BR7.2` 的測試；以含 userinfo 的 `OLLAMA_BASE_URL` 構造，斷言訊息中不含密碼 |
| `SEC-3` | `fastembed` 的供應鏈風險為**具名接受**（`RR-2`），處置是在 `LOCAL-DEV.md` 釘一個已驗證的版本區間、寫明 HuggingFace 下載來源與快取位置、並明寫**此路徑不經 CI，其供應鏈風險由使用它的開發者承擔**。 | 供應鏈（OWASP #6 Vulnerable Components） | `LOCAL-DEV.md` 含帶版本的安裝指令與該段警語 |
| `SEC-4` | `stub` 的 `model_id()` **不得**與任何真實模型名相同（固定 `stub-v1`）。 | 完整性（跨環境資料可區分） | `BR3.6` 的測試；CI 寫入的列與 staging 寫入的列在 `embeddingModel` 上可區分 |

## 五、ADR-0006 四面向逐項判定（**自檢第七項**）

`project.md ## Mandated` 逐字要求逐項判定、不得留空白、不得以「已有 ADR-0006」帶過。
**每一格已與上游 K-06 同欄逐字比對**（依 `user-stories:d0658da6` 的教訓：與上游相反的
判定比沒跑更糟）。

| 面向 | 判定 | 與上游是否一致 | 處置 |
|---|---|---|---|
| **IAM** | **不適用** | **一致**。K-06 `authorization_responsibility` 逐字「無——本 Port 不碰授權，亦不讀 DB」；`functional-design §七` 亦判不適用 | `SEC-1` 把它寫成可 `grep` 的禁令，而不是一句宣告 |
| **Encryption** | **適用（一處，且為本單元最重的一面）** | **一致**。`functional-design §七` 已判「適用（一處）」並點名明文 HTTP；本站把它從一句觀察升格為三條需求（`NFR7.1`–`NFR7.3`）＋ 一項具名殘餘風險（`RR-1`） | 見第一、三節 |
| **Network exposure** | **適用** | **一致**。`functional-design §七` 判「適用」，理由為本單元是 ollama 的唯一消費端 | `NFR7.2` 具名為對 `U1` 的依賴前提；`BR1.5`（啟動不探測）另使 backend 的啟動路徑不產生對 ollama 的連線 |
| **Audit logging** | **適用（弱）** | **一致**。`functional-design §七` 判「適用（弱）」 | `BR7.1`（啟動記一條含 provider／model 的 INFO）＋ `SEC-2`（不得含憑證）。記憶層本身的稽核屬 `U8` |

**PBT hard constraint**：**適用，本單元即落點**（K-06 `pbt_note` 逐字）。
六個性質已於 `functional-design/functional-spec.md §五` 寫死，本站不重複定義，
但確認其中 `P5`（雙向一致性）是唯一三個實作都驗得到的；`P1`–`P4`／`P6` 對
`ollama`／`fastembed` 無 CI 驗證路徑，已登記為該檔的 `OQ-E2`。

## 六、交接給其他單元的具名需求

| ID | 需求 | 落點 | 為什麼不是本單元 |
|---|---|---|---|
| `U8-1` | **換模型的偵測**：啟動時比對「目前 `model_id`」與「記憶表中已存在的相異 `embeddingModel` 集合」；若目前這個不在其中且表非空，記一條 **WARN 以上**的訊息寫明「既有 N 列記憶以 `<舊 model>` 寫入，本次啟動為 `<新 model>`，那些記憶在重新 embed 之前不會被檢索到」。**不自動重算**。 | `U8 memory-service` | 偵測需要讀 DB，而 `BR2.7` 禁止本 Port 讀 DB。`[Q2]`=A 的作答已含此落點說明 |
| `U8-2` | 寫入記憶時，必須以**同一次** `ProviderSelection` 的 `model_id()` 配對該次 `embed` 的結果，不得分兩次取。 | `U8` | `BR5.2`：向量不攜帶 `model_id`，配對是呼叫方的責任 |
| `U5-1` | `memory_records.embeddingModel` 的值域由 2 擴為 3（新增 `stub-v1`）且須可為 `NULL`；schema 端**不應**寫成封閉 `CHECK`（會讓換模型變成資料庫錯誤）。 | `U5 memory-data` | 承 `functional-design` 的 `H-E1`。**已實測**：`memory_records` 尚未落地，遷移成本為零 |
| `U11-1`／`U8-3` | `NFR3` 的預算分析未計入 embedding 延遲（`RR-4`）。 | `U8`／`U11` 的 `nfr-requirements` | 本站不自行改已核可的 `NFR3`，也不自行指派承接單元 |

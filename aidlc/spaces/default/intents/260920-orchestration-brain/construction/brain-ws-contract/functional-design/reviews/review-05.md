## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

先前四輪審查的發現大多已處置，22 個實體、31 條規則與 9／6 個 type 值也和已落地的 `backend/services/brain_ws_contract.py` 一致。這次補審找到一個舊輪次沒抓到的契約洞：`error` 被劃為「輪次訊息」，envelope 與 payload 的 `turnId` 都不可為 null，但設計要求在沒有任何一輪的情境下回 `error`，這些情境在型別上無法構造。設計與程式在這一點上互相一致，兩邊都錯，所以不是漂移，而是契約本身無解。另有一項 Major 與兩項 Minor，內容見下表。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Critical | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/functional-design/rules.md > BR1.6、BR2.8、BR2.13；entities.md > ErrorPayload.turnId、WsEnvelope.turnId | 設計有四處要求在「不屬任何一輪」的情境回 `error`，但 `error` 在 BR1.6 屬輪次訊息（envelope turnId 必為非 null），`ErrorPayload.turnId` 也是必填 `string`（entities.md ErrorPayload；程式 `brain_ws_contract.py:370` 為 `turnId: str`，`:738-749` 的 `_br1_6_turn_id_partition` 對 error 強制非 null）。這四處是：(1) BR2.13，客戶端帶 turnId 時伺服器「拒絕並回 error(INVALID_REQUEST)」；(2) 上游 K-02 `:288`（`set_sharing_mode` 失敗回 error）；(3) K-02 `:308`（`set_work_target` 授權或解析失敗回 error），這兩個客戶端訊息是狀態訊息、不屬任何一輪；(4) BR2.8 的 UNAUTHORIZED「連線已建立後的授權失敗」，同樣不一定落在某一輪內。伺服器要送這些 error 必須捏造一個 turnId，而 turnId 的產生又被明文歸給 U13。BR1.5 還要求 payload.turnId 等於 envelope.turnId，所以兩處都要捏造。這和本單元 R-14 當年對 ready 與三個狀態訊息指出的是同一種形狀，修的時候只改了那四個伺服器訊息，沒回頭檢查 `error` 的非輪次用法。哪一邊對：upstream 要求回 error 的行為是必要的，BR1.6 的「error 必為輪次訊息」才是錯的前提。 | 擇一處置並同步 entities.md、rules.md、`brain_ws_contract.py` 與 ws-contract.json：(a) 讓 `error` 的 envelope.turnId 與 `ErrorPayload.turnId` 改為可為 null，BR1.6 與 BR1.5 補上「非輪次 error 兩處皆為 null」並寫出判準（回應客戶端狀態訊息或協定違規時為 null）；或 (b) 另定一個非輪次的錯誤型別，由 BR1.4 一併計入。無論選哪個，都要在 BR2.8 逐條標明每個 code 在輪次內與輪次外各自的 turnId 規則，並新增能構造「非輪次 error」的測試。 | New |
| R-02 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/functional-design/functional-spec.md > SM-2、entities.md > WorkItemsPayload；rules.md > BR1.6 | SM-2 把 `work_items` 列為 `InTurn` 內回報進度的訊息，§二並明寫「work_items 既可在一輪內回報進度」，但 BR1.6 規定 `work_items` 的 turnId 一律為 null。客戶端因此無法把一輪內的工作項更新歸到那一輪，也分辨不出它是輪內進度還是外部狀態變化的扇出。這使 AC1.2.1 以外的工作項顯示（US1.1 一輪交辦多個工作項）在傳輸面沒有歸屬依據。設計自己列了這個「兩處出現」是刻意的，卻沒說明歸屬靠什麼。 | 在 functional-spec.md 說明客戶端如何判斷 work_items 屬於哪一輪（例如以 workItemId 為準而非 turnId），並把 SM-2 的措辭改成與 BR1.6 一致；若需要輪次歸屬，則讓 work_items 的 turnId 可為輪次值，並調整 BR1.6 的兩類判準。 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/functional-design/rules.md > BR1.3 的 `source` 欄 | BR1.3 的 `source` 仍寫「WsClientEnvelope 的 turnId 是**選填**」，但 R-20 已把該欄位自客戶端封包移除（entities.md WsClientEnvelope.turnId 標「不存在」，程式 `WsClientEnvelope` 無此欄位且 `extra="forbid"`）。同一檔的 BR2.13 與這句直接矛盾。這是 R-20 修改時漏掉的跨檔傳播殘留。 | 把 BR1.3 `source` 中關於客戶端 turnId 選填的句子改為「客戶端封包沒有 turnId（BR2.13）」。 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/functional-design/functional-spec.md > SM-1、SM-2；entities.md > SharingModePayload、WorkTargetPayload | 連線建立時要推送 `sharing_mode` 與 `work_target`（entities.md 兩處「亦於連線建立時推送」），BR3.5 又規定客戶端「收到 ready 後才可開始送 user_message」，但 `ready` 與這兩則初始推送的先後順序沒有任何規則定義。客戶端若先收到 `sharing_mode` 再收到 `ready`，或相反，行為不同；這個順序無漂移閘門保護。 | 在 SM-1 明訂初始推送相對於 `ready` 的順序（建議 ready 先、狀態推送後，或反之），並指派 U13 實作與測試；或寫明客戶端不得依賴此順序。 | New |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/functional-design/functional-spec.md > SM-2、rules.md > BR2.14 | `clarify` 屬輪次訊息，但送出 clarify 之後該輪沒有終止事件，只能靠客戶端送 `select_clarify_candidate` 離開。使用者若不選、改送新的 `user_message`、或連線中斷時，這個懸置輪次怎麼處置沒有規定：是被新的 user_message 隱含取消，還是並存兩輪。BR3.4 的 Incomplete 只涵蓋連線中斷。 | 在 SM-2 補一條「clarify 等待選擇期間收到新的 user_message」的處置（隱含放棄該輪並開新輪，或拒絕並回 error），指派 U13。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀取 entities.md、rules.md、functional-spec.md、traceability.json 與 review-04 | 先前 29 項發現中僅 R-29（ci.yml 行號差一）在 review-04 仍為 New | 本次不重複已處置項；R-29 屬 Minor，不影響本輪判定 |
| 抽查 `backend/services/brain_ws_contract.py:338-376、570-622、738-749` | `ErrorPayload.turnId: str`；`error` 屬 `_TURN_SCOPED_TYPES`；`_br1_6_turn_id_partition` 強制 error 的 turnId 非 null | 證實 R-01：設計與程式一致，兩邊都使非輪次 error 不可構造 |
| 抽查 WsClientEnvelope（`brain_ws_contract.py:754-790`）與 `extra="forbid"` | 客戶端封包無 turnId | 證實 R-03：BR1.3 `source` 的「選填」是殘留 |
| 未執行任何會寫檔或產生快取的指令（測試、lint、建置、dump） | 未執行 | 依指示不跑；9／6 個 type 值與 22／31 計數沿用 review-04 的機械核對結果，本次只抽查程式對應行 |

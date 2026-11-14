## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

NFR 設計的主幹站得住腳：Hash 加 Lua 的選擇有並發論證，逐項否決熔斷器等模式並附理由，ACL 對 EVAL 的可行性前次審查已實測。但原子性設計有兩處缺口，且都已在已落地的程式裡暴露。第一，設計只處理了追加與切換為獨立段兩條寫入路徑的原子性，session 首次建立與 set_work_target 的寫入沒有被納入原子性分析，並被描述為單次 HSET；程式因此以多個獨立指令實作，崩潰時可能留下沒有到期時間的 key。第二，meta.userId 被列為 Hash 欄位，卻沒有任何一份設計產出指名寫入端。另有前次 review-01 已提、仍留在凍結產出中的三項，以及若干數字與引用問題。依判準 Critical 為 0、Major 為 2，判 READY，但 R-01 與 R-02 建議在關卡上優先裁決。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/session-store/nfr-design/reliability-design.md 第三節（原子性與崩潰一致性表）；performance-design.md 核心設計（TTL 續期併入同一支 Lua／同一次管線） | 原子性表只列四列：追加、set_work_target、set_sharing_mode 加建段、load。第一，session 首次建立（EC1 要求 segments 必含 shared，meta 與 seg:shared 兩個欄位須同時出現）沒有任何一列。第二，set_work_target 被描述為「K-07 解析（唯讀）加一次 HSET」並下結論「不留下任何不一致」，但漏了兩件事：key 剛好已到期時單獨一次 HSET 會重建一個沒有 meta、也沒有 TTL 的 Hash，違反 BR1.3 與 BR1.4；HSET 與 EXPIRE 是兩個指令，之間崩潰會留下永不到期的 key。已落地程式證實設計沒有涵蓋這條路徑：backend/services/session_store.py 的 set_work_target 先 _ensure_meta（exists 檢查，再兩次 hset），再 hset tgt 欄位，再 expire，共五個以上獨立往返，只有 append_message 與 switch_to_isolated 走 Lua；exists 與後續 hset 之間還有 TOCTOU。設計的不變量（整體到期、半建立狀態不可見）是對的，錯的是把「只有兩條路徑需要原子」當成全部。 | 在 reliability-design 的原子性表補上「首次建立」與「set_work_target」兩列，要求建立 meta、seg:shared、目標欄位與 EXPIRE 同在一支 Lua（或明訂檢查 key 存在才寫入且 HSET 後必須 EXPIRE 的單一腳本）。承接站為 U10 code-generation 的後續修正或 build-and-test；設計與程式矛盾時設計的不變量為準，程式需修。 | New |
| R-02 | Major | construction/session-store/nfr-design/performance-design.md 核心設計（Hash 欄位表，meta 含 userId）；logical-components.md 第一節；與 functional-design/entities.md 的 userId required: true | 契約端點三問的「誰寫」缺一：meta.userId 被列為 Hash 欄位並在 entities.md 宣告必填，但六份 nfr-design 產出沒有任何一份指名寫入者。K-09 凍結介面只有 set_work_target 帶 principal，append_message、set_sharing_mode、touch 都不帶身分，因此只被追加建立的 session，其 userId 為 null。code-generation/code-summary.md 第九節第 3 項自承此為「契約端點三問『誰寫』那一腿的缺口」，Owner 指向 U13。這是設計階段本該查出的缺口，卻留到實作才浮現。誰讀、誰清同樣沒有交代：沒有任何讀取端被指名需要它，sessionKey 又可由使用者 id 推導，則 userId 欄位是否有存在必要也未論證。 | 在 nfr-design 或其修正檔明確二選一：(a) 指名 userId 的寫入者與時點（需要契約修訂讓某方法帶身分）；(b) 論證 sessionKey 已可推導，並把 userId 降為可選或從 Hash 欄位表移除，同步更新 entities.md 的對應處。不得停在「null 直到第一次 set_work_target」。 | New |
| R-03 | Minor | construction/session-store/nfr-design/performance-design.md 連線池算式；與 nfr-design-questions.md 開頭第 1 點 | 前次 review-01 未提。連線池算式把峰值 RPS 取為 300（300 個 session 各每秒一次互動），但同一份問題檔自己寫「一輪互動約 2–3 次 Redis 呼叫」，而公式中的 RPS 應是 Redis 呼叫率，亦即約 600–900，算得 27 左右，超過所設的 max 20，與「max 20 為算式結果的兩倍餘裕」自相矛盾。此外同檔逾時表把重試最壞情況寫成約 3.3 秒，只計了指令逾時；連線層不可達時每次嘗試最多先吃 2 秒連線逾時，最壞可達約 7 秒。 | 重算：RPS 改以 Redis 呼叫率代入並更新 min／max 或餘裕說明；重試最壞情況分別列出指令逾時鏈與連線逾時鏈。 | New |
| R-04 | Minor | construction/session-store/nfr-design/scalability-design.md 容量門檻表第三列；reliability-requirements.md NFR4.51 | 設計稱觸及 maxmemory 後 append_message、set_*、touch 全部回 SessionBackendUnavailable、只有 load 可用。touch 底層是 EXPIRE，依我對 Redis 指令旗標的理解它不帶 denyoom，因此 OOM 時多半仍會成功；而 set_work_target 的 HSET 才會被拒。本點未實測（本審查不得執行會產生快取的指令），故以待查呈現。若屬實，「OOM 時 session 仍被續期」其實有利，但降級行為描述不精確。 | 部署後驗證時以 app 身分在 OOM 條件下實測 touch／EXPIRE 的行為，並修正文字。 | New |
| R-05 | Minor | construction/session-store/nfr-design/reliability-design.md 第一節 Retry 列；第三節 | append_message 因非冪等不重試，但指令逾時時伺服器可能已執行完成，呼叫端看到的是 SessionBackendUnavailable 且原因碼為 redis_unreachable，無法與「根本沒寫入」區分。呼叫端（U13）若重送會產生重複訊息。設計只說「失敗即拋出」，沒有交代結果未知這一類。 | 在可靠性設計補一句：逾時類失敗的結果未知，需由呼叫端重讀確認或接受重複風險；或讓 Lua 接受由呼叫端提供的 message id 以去重。 | New |
| R-06 | Minor | construction/session-store/nfr-design/reliability-design.md 第三節第 3 列（「W3 的第 4、5、6 步（建段、複製作業對象、改 pageModes）」）；functional-design/functional-spec.md W3 表 | 前次 review-01 已提 R-03，仍留在凍結產出。W3 第 4 步已同時含建段與複製作業對象，第 5 步只是「不重跑 K-07 驗證」的說明、不是寫入動作，第 6 步才是 pageModes。原子性結論正確，步驟歸屬錯。 | 改為「第 4、6 步」，或把第 5 步描述為免重驗的說明。 | New |
| R-07 | Minor | construction/session-store/nfr-design/ 全部產出（尤其 tech-stack-decisions.md 第 59 行對應的 nfr-requirements 產出）；security-design.md OPEN-N10-6 | 前次 review-01 已提 R-01 與 R-02，凍結產出中仍無處理。R-01：[D1]=A 已決定儲存結構（Hash 加 Lua），而 nfr-requirements/tech-stack-decisions.md 第 59 行逐字「本站不預選儲存結構」，nfr-design 的六份產出沒有任何一句承認這是取代該指派。R-02：OPEN-N10-6 要求超長訊息拒絕要「型別化」且可與後端不可用區分，卻沒有指定機制；K-09 的 raises 只列 SessionBackendUnavailable。程式已以新增 SessionMessageTooLong 解決，但設計仍未決定，且該例外是否經 K-09 契約修訂，我無法由本單元範圍內的檔案確認。 | 在 nfr-design 補一則 supersede 註記（指向 tech-stack-decisions 第 59 行）；在 OPEN-N10-6 補明機制選擇，並確認 SessionMessageTooLong 是否已回報為對 K-09 的契約補充。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀取六份 nfr-design 產出與 review-01 | 完成 | 前次三項發現中，R-03（步驟歸屬）與 R-01、R-02（取代註記、例外型別）在凍結產出中仍未處置，已併入 R-06、R-07 |
| 抽查已落地程式（session_store.py、append_message.lua、code-summary.md） | 完成 | 證實 R-01 與 R-02 的缺口已在實作層暴露；程式的 append 與切換路徑符合設計 |
| 引用核對（deploy compose 行號、hierarchy_facade 行號） | 未驗證 | 這兩個檔案在工作樹中已被後續單元修改，行號已漂移，無法以現況判定當時是否正確，不列為發現 |
| 驗證工具（測試、lint） | 未執行 | brief 禁止執行會寫檔或產生快取的指令 |

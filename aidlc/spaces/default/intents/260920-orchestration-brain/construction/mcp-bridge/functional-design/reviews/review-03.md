## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U21 mcp-bridge 的功能設計自洽且可實作：45 條規則（BR71 至 BR78 的 6、11、5、6、4、4、4、5 條）以 grep 實算與 functional-spec 宣稱一致；AC11.4.1 至 AC11.4.3 皆有落點；產生器的檢查順序、九個錯誤碼、七條 PBT 性質與突變清單互相對得上；契約三問（欄位誰寫誰讀誰清）在 entities.md 摘要表中完整。已落地的 backend/mcp_bridge 抽查（credentials.py、agents.py、calls.py、dispatch.py、outcomes.py、executor.py、app.py、guards.py、allowlist.json、agents.json）與設計主張沒有實質矛盾，且已把設計中途的審查發現（路徑段字元集白名單、fullmatch、總攔截）落實。需要人在關卡權衡的是兩項設計自己揭露、尚未裁決的對上游已核可要求的偏離：明文 JWT 的 Encryption 詮釋（OPEN-MB21-13）與成功讀取無使用者身分稽核（OPEN-MB21-14）。其餘為 Minor 的設計與落地漂移。無 Critical，Major 兩項，故判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/mcp-bridge/functional-design/functional-spec.md 第六節 Encryption 列、第 7.2 節 OPEN-MB21-13、rules.md BR71.2 | 上游 requirements.md:618 要求 HTTP 或 SSE 傳輸須為本機迴環或加密。設計承認 docker 橋接網段不是迴環，使用者 JWT（auth.py:33 為 8 小時有效，已實讀 ACCESS_TOKEN_EXPIRE_MINUTES 為 60 乘 8）以明文在與 redis、ollama 共用的網段往返，卻把「不離開本主機」詮釋為滿足。這是以詮釋化解 ADR-0006 hard constraint 的一個面向，且該詮釋至今沒有人裁決（設計自己寫「需使用者確認」）。程式端沒有任何收斂（executor.py 的 client 是 base_url 加明文 http，無 TLS 選項）。 | 在核可關卡取得明確裁決並記錄：接受殘留明文（連同 token 有效期與同網段暴露面一併寫入 ADR-0006 影響表），或指派收斂手段（bridge 與 backend 同網路命名空間經 127.0.0.1，或雙端 TLS）給具名單元，並寫明哪一邊的需求字面被修改。 | New |
| R-02 | Major | construction/mcp-bridge/functional-design/functional-spec.md 第六節 Audit logging 列、第 7.2 節 OPEN-MB21-14、rules.md BR77.3 | 上游 requirements.md:620 要求稽核主體為使用者本人。設計查證 facade 只記被拒的讀取（requirement_field_facade.py 的 _deny，約 268 至 278 行），成功的 read_fields（約 300 至 305 行）不記，bridge 又刻意不解碼 JWT（BR73.5、credentials.py 只做格式檢查），所以 agent 經 MCP 讀了誰可見的哪個系統，事後沒有任何帶使用者身分的紀錄；bridge log 與 backend log 還無關聯鍵（OPEN-MB21-9）。寫入與清空面成立，讀取面不成立。AC11.4.1 與 AC11.4.3 的主角正是讀取。 | 關卡上裁決：接受讀取面稽核缺口，或要求 U20 的 read_fields 補一行帶 user_id 的 INFO（設計已建議，但目前只是條件句，沒有單元承接）。若選補，須寫明承接單元與修訂方式；若接受，須在 ADR-0006 audit logging 列改寫為「寫入面適用、讀取面例外」。 | New |
| R-03 | Minor | construction/mcp-bridge/functional-design/functional-spec.md 第 7.2 節 OPEN-MB21-1、第 2.5 節 | 設計明載大腦側沒有任何 MCP client（U11、U12 對 MCP 命中為 0，U13 的 NFR13.16 禁止呼叫需求欄位 facade），能力 11 的「agent 取用需求欄位」在本 intent 內沒有真實呼叫者；AC11.4.1 與 AC11.4.3 只以單元自帶的測試 client 驗證（traceability.json 已誠實註明「未驗證：真實 agent 觸發此呼叫」）。使用者以 MB1 選 A 接受，故不升級，但承接站為「本 intent 內無自然承接站」，等於交回範圍定義。 | 關卡呈現時維持此揭露；後續 intent 的 scope-definition 須有具名項目承接 client 側，否則 US11.4 的使用者價值在線上為零。 | New |
| R-04 | Minor | construction/mcp-bridge/functional-design/entities.md RequestCredential、BackendCall；functional-spec.md 第 2.5 節與 MB-W1；backend/mcp_bridge/credentials.py、calls.py、app.py、observability.py | 設計與已落地程式有可見漂移，以落地程式為準（其 docstring 引用了後續 nfr 站審查，屬後續站增補）：(1) RequestCredential 設計有 authorization 與 declared_agent 兩屬性，程式只有 raw，agent 標頭另存於 guards.RawHeaders；(2) BackendCall 設計無 query 欄，程式有 query 元組；(3) parse_credential 設計吃 headers，程式吃單一標頭的值序列；(4) create_app 設計四個必填參數，程式另有 limits 與 call_hook；(5) 規格的模組表只列 generator、credentials、agents、calls、outcomes、app，程式另有 dispatch、executor、guards、limits、observability、server、startup、cli，且 configure_logging 規格放 app.py，程式在 observability.py:50。 | 不需回改凍結產出；在關卡紀錄註明「後續站與實作已擴充，以 backend/mcp_bridge 為準」，並確認 entities.md 的 RequestCredential 與 BackendCall 不被下游當成現行契約引用。 | New |
| R-05 | Minor | construction/mcp-bridge/functional-design/rules.md BR73.1；backend/mcp_bridge/credentials.py:AUTHORIZATION_PATTERN | bridge 以 ^Bearer 加字元集嚴格比對，scheme 大小寫敏感；backend 的 HTTPBearer 對 scheme 不分大小寫。使用 bearer 小寫的 client 直連 backend 成功，經 bridge 卻得 unauthenticated，與 AC11.4.1 與 AC11.4.3 所要的「與我直接存取相同」在此一邊界上不一致。屬相容性邊角，不影響授權安全。 | 擇一：BR73.1 明寫「scheme 僅接受 Bearer 精確大小寫」並列入 client 契約；或放寬為不分大小寫但轉送時正規化。 | New |
| R-06 | Minor | construction/mcp-bridge/functional-design/functional-spec.md 第 7.2 節 OPEN-MB21-15、第八節 H-5；backend/requirements.txt 的 mcp==2.3.0 註解 | mcp 與 backend 共用同一份 requirements 與 site-packages 的耦合，設計已揭露並排好退路；落地選了第一順位，但程式註解自己記載「Python 大於等於 3.14 時 mcp 要求 starlette 大於等於 0.48.0，與 FastAPI 釘選衝突」。設計未把「執行期 Python 版本」列為第一順位的前提，日後升 Python 基底映像會無聲打破相容。 | 在後續站或 ci 以斷言鎖住基底映像的 Python 主次版本，或把此前提補進 H-5 的第一順位條件。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| grep 規則數（rules.md 的 id: BR 列，依群組） | 71 為 6、72 為 11、73 為 5、74 為 6、75 為 4、76 為 4、77 為 4、78 為 5，合計 45 | 與 functional-spec 開頭宣稱的 45 條及分佈一致，無漂移 |
| traceability.json 覆蓋 | upstream_ids 為 AC11.4.1、AC11.4.2、AC11.4.3，三者皆 OK 且有落點與驗證方式；其餘 BR 列為 N/A 並附理由 | 與 stories.md:727 至 729 的三條 AC 逐字對得上，無漏接 |
| 契約三問（entities.md 摘要表） | AllowlistEntry、ToolSpec、AgentRegistry、RequestCredential、BackendCall 等皆能指名寫、讀、清 | 無孤兒欄位；OPEN-MB21-4（清空無持久溯源）已揭露為跨單元缺口 |
| 設計與程式抽查 | calls.py 的 fullmatch 與路徑段白名單、dispatch.py 的總攔截、outcomes.py 的七個錯誤碼與封閉表、agents.json 的 cost 與 architecture 兩組（對 requirement_field_definitions.py 的 GROUPS_BY_KEY）、KEY_PATTERN 與 SEGMENT_PATTERN 字串相同 | 設計主張與落地一致；差異僅 R-04 所列的凍結後增補 |
| 未執行 | 測試、lint、建置 | 依 brief 禁止產生快取，未執行 |

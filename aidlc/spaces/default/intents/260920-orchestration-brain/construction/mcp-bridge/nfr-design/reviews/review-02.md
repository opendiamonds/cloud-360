## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

nfr-design 的六份產出本身結構完整、對 NFR21.x 的承接與 ADR-0006 四面向都有落點，但凍結的產出沒有吸收前次 review-01 的兩項 Major，且已落地的程式與設計在多處分歧：程式（guards.py、limits.py）已用 MethodGuard、WallClock、ExactPath 補上缺口，設計文字卻仍是未補的版本；SDK 行為的靜讀基礎是 mcp 1.29.0，實作釘的是 mcp==2.3.0。以設計單獨實作，會得到前次已指出的並行閘鎖死與取消路徑雙寫 log 問題。分歧處以已落地的程式為準；建議以 corrections 檔取代而非回改。本補審未執行任何程式或測試。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/mcp-bridge/nfr-design/scalability-design.md > 1.2 設計與 1.3 判準；logical-components.md > 二 請求的層序 | 前次 review-01 已提 R-01：並行閘的名額沒有時間上界，且未討論 GET 與 DELETE，因此慢速上傳或長連線 SSE 的 16 條請求可無聲鎖死 bridge，而 /healthz 仍回 200。凍結產出完全未處置：1.2 偽碼仍只有 ConcurrencyGate，1.3 判準 ① 到 ⑤ 全是 POST tools/call。已落地的 backend/mcp_bridge/guards.py 與 limits.py 已增設 MethodGuard（非 POST 回 405）、WallClock（REQUEST_WALL_TIMEOUT_S 13 秒）、BodyLimit 讀取期限 2 秒回 408，並把牆鐘排在 BodyLimit 之外，層序與設計圖相反。設計與程式矛盾，程式這一邊是對的；下游只讀設計就會漏掉三個閘門與兩個新增的 request_rejected 原因。 | 以 corrections 檔取代 scalability-design.md 1.2 與 1.3、logical-components.md 二，寫入程式實際的七層順序、405／408／503 回應、牆鐘與 stop_grace_period 的關係式，以及慢速上傳與 GET 兩案的判準與突變。 | New |
| R-02 | Major | construction/mcp-bridge/nfr-design/reliability-design.md > 九 client 中途斷線；performance-design.md > 四 連線池；observability-design.md > 二 | 前次 review-01 已提 R-02：asyncio.shield 保護 exchange 與記 log，使名額在請求取消時先歸還、被保護的交換仍占連線池，因此 performance-design 四宣稱的進行中 backend 請求 ≤ 16 不成立；同時 tool_call 那一行的唯一寫出者在取消路徑下可能是 0 行或 2 行。第九節仍未指定名額與唯一寫出者，OPEN-MB21-16 的驗證案仍只斷言恰 1 筆與 outcome=ok，未斷言總行數。程式 dispatch.py 的檔頭已註明 tool_call 唯一寫出點在 finally，並以 CC-6 說明閘門歸還時交換已結束，等於程式內部已改了決策，但設計文字沒有同步。 | 在 corrections 檔寫明：被保護的交換持有名額直到結束，或放棄 shield；指定 tool_call 唯一寫出者；把 OPEN-MB21-16 改為斷言 tool_call 行總數恰為 1，並增列慢速 backend 加反覆斷線後合法呼叫仍成功的案。 | New |
| R-03 | Major | construction/mcp-bridge/nfr-design/security-design.md > 三 工具函式與 SDK 的交界；observability-design.md > 二；logical-components.md > 四、七 OPEN-MB21-17 | 整個 SDK 交界設計（validate_input=False、call_tool 裝飾器把例外轉成 isError、未知工具只能回 invalid_argument、allowed_hosts、logger 名稱）都建立在靜讀另一 clone 的 mcp 1.29.0。已落地實作釘的是 mcp==2.3.0（code-summary.md 標頭、backend/requirements.txt），且採 Server(get_tool_input_schema=...)、StreamableHTTPSessionManager(max_request_body_size=...)，Host 拒絕為 421。因此 validate_input 開關與 OPEN-MB21-17 的前提已不適用，凍結產出沒有任何一處標記被取代。前次 R-04 要求的 SDK 行為假設總表也未建立，假設與退路仍分散在六個檔案。後續維護者以設計為準會對錯誤版本寫程式。 | 在 corrections 檔或 logical-components.md 補一張 SDK 行為假設總表，逐列標明 1.29.0 的靜讀結論、2.3.0 的實際結論、判準編號與退路；明確把 validate_input 與 OPEN-MB21-17 標為已被取代並指向 code-summary。 | New |
| R-04 | Minor | construction/mcp-bridge/nfr-design/security-design.md > 九 ADR-0006（標題與 Encryption 列） | 前次 R-05 已提：上游要求 HTTP 須為本機迴環或加密，本單元是 internal 網段明文，由使用者 2026-10-14T23:02:07Z 接受的例外。標題仍寫無一格相反，Encryption 列未註明這是對上游條件的例外，自檢 7 也寫無一格相反。 | 標題改為判定欄無相反、Encryption 一格為經使用者接受的例外，並逐字引用上游條件。 | New |
| R-05 | Minor | construction/mcp-bridge/nfr-design/reliability-design.md > 五 致命的啟動錯誤；observability-design.md > 四 | 前次 R-07 已提：設計只規定 main 捕捉 StartupConfigError，沒有規定檔案缺失、非 JSON、編碼錯誤如何包裝，凍結文字下會漏出 traceback。code-summary 稱程式已把這些包成 StartupConfigError，設計未同步，NFR21.6 判準也沒有對應兩案。 | corrections 檔補上包裝規則與缺檔、非 JSON 兩個判準案。 | New |
| R-06 | Minor | construction/mcp-bridge/nfr-design/scalability-design.md > 六 最壞記憶體上界；logical-components.md > 三 | 前次 R-08 已提：17825792 位元組是緩衝位元組上界，被當作 infrastructure-design 記憶體上限輸入，未註明解碼與雙份序列化的放大係數未量測。第 124 行仍未更正。 | 改名為緩衝位元組上界，並註明放大係數未量測，記憶體上限不得直接取該值。 | New |
| R-07 | Minor | construction/mcp-bridge/nfr-design/logical-components.md > 一 limits 列（五個具名常數）；NFR21.24 | 設計寫 limits.py 有五個具名常數，程式為七個（新增 BODY_READ_TIMEOUT_S、REQUEST_WALL_TIMEOUT_S）。這是 R-01 的連帶不一致，NFR21.24 的單一來源檢查若依五個常數寫就會漏查兩個。 | 隨 R-01 的 corrections 一併更正為七個，並同步 NFR21.24 的可執行檢查。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 人工比對設計與 guards.py、limits.py、dispatch.py | 設計缺 MethodGuard、WallClock、ExactPath，常數數量不符 | 支持 R-01、R-07 |
| grep MethodGuard、WallClock、405 於 nfr-design | 零命中 | 前次 R-01 未被凍結產出吸收 |
| 未執行測試或建置 | 依 brief 禁止產生快取 | 不作行為斷言，僅作文字與原始碼比對 |

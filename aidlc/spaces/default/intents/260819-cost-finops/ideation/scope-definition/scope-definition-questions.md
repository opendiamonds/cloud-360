# Scope Definition — 釐清問題

> Stage: scope-definition（Ideation 1.4）· Depth: Standard · Scope: mvp
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。
> 上游輸入：`../intent-capture/intent-statement.md`（intent-statement）、`../feasibility/feasibility-assessment.md`（feasibility-assessment）、`../feasibility/constraint-register.md`（constraint-register）。

## 已由上游定案、不重問

- 產品邊界為 `mvp`；本輪只做 C1，不交付 C2／C3 [intent:Q8] [intent:Q9]
- 必須公開免帳號官方價目；必須帶金鑰的雲走 Manual Override；三雲都能打開成本畫面 [feas:Q2] [feas:Q1a]
- 本輪 TCO 不含 egress [feas:Q3]
- 每張架構圖一個月預算 [feas:Q4]
- 架構師改時數；FinOps 與工程主管設預算；僅 FinOps 覆寫單價 [feas:Q5]
- 超支期間每次進入產品都看到橫幅，無 inbox [feas:Q6]
- 未對應列名、不計入總額、顯示 N 項尚未定價 [feas:Q7]
- 無時間盒，可被插隊 [feas:Q8]
- 入口：Sidebar C＋產圖後 CTA；本輪不做核准流 [intent:Q13] [intent:Q14]
- 不做 WSJF／RICE 數值評分（單一決策者、Must 已鎖）

## Sources

- [intent:Q3] 成功＝擷取＋官方報價＋圓餅＋時數重算＋預算上限＋超支警告
- [intent:Q9] 本輪只做 C1；C2／C3 不交付
- [intent:Q12] 官方報價 API，不得使用 production credentials
- [intent:Q13] Sidebar C＋產圖後 CTA
- [intent:Q14] 本輪不實作核准流
- [feas:Q1a] 「能報價」＝成本畫面可用；官方 API 僅限公開免帳號價目
- [feas:Q3] 本輪 TCO 不含 egress
- [feas:Q8] 有競爭優先事項，可被插隊
- [feas:R1] 公開價目雲別覆蓋未知（raid-log R1）
- [memory:M1] `project.md#Testing Posture`: cost calculator 必須含 property-based testing
- [memory:M7] schema／seed 變更須同步部署資產（blocking）

## Q1. 可被插隊的前提下，C1 還能不能切成更小的上線增量？

> 上游已把 C1 本輪能力鎖成必做，不是「哪些是 Must」的重問 [intent:Q3]。feasibility 又確認可被插隊 [feas:Q8]。本題只定：若做不完，最小仍能對外交付的切法，還是必須整包才算完成。

A. 整包 Must — 擷取、官方／覆寫報價、圓餅、時數、每圖預算、超支畫面標示與橫幅、Sidebar C、產圖後 CTA，缺一不算本輪完成；被插隊就暫停，不先上半套。
B. 允許兩段 — 第一段：擷取＋報價（官方或 Override）＋總額／圓餅／時數／入口；第二段：每圖預算＋超支標示與橫幅。第一段可單獨上線。
C. 允許三段 — (1) 擷取＋報價＋總額；(2) 圓餅＋時數＋入口；(3) 預算＋超支。更早可展示，但第一段還沒對上「可拆解的 TCO」。
D. Not yet defined
X. Other (please specify)

[Answer]: B. 允許兩段 — 第一段：擷取＋報價（官方或 Override）＋總額／圓餅／時數／入口；第二段：每圖預算＋超支標示與橫幅。第一段可單獨上線。

## Q2. 本輪工作的排序偏好？

> 技術依賴大致是：圖上資源 → 價目（或 Override）→ 總額／圓餅／時數 → 預算比對 → 超支橫幅；入口可與畫面平行。公開價目覆蓋是最大不確定性 [feas:R1]。

A. Dependency-first — 依擷取 → 價目 → 畫面 → 預算／橫幅 的鏈排序；入口跟畫面走。
B. Risk-first — 先查證各雲公開免帳號價目能否用（R1），再做畫面與預算；避免先做完 UI 才發現幾乎全是 Override。
C. Value-first — 先讓架構師在產圖後看到總額與圓餅（含 CTA），預算與橫幅殿後。
D. Not yet defined — 交由 delivery-planning 決定。
X. Other (please specify)

[Answer]: B. Risk-first — 先查證各雲公開免帳號價目能否用（R1），再做畫面與預算；避免先做完 UI 才發現幾乎全是 Override。

## Q3. Won't Have（本次明確排除）清單是否就是這些？

> 「Won't Have」防止範圍蔓延。下列皆來自上游已拒絕或未選取的項。未列入 Won't Have、也未列入 Must 的，會記成「未承諾」，不推定未來去做或永遠不做。

建議清單：C2（pricing models）；C3（data egress 路徑分析）；本輪 TCO 的 egress／資料傳輸列；FinOps 核准流；站內 inbox；staging 價目憑證；讀取客戶帳單／Cost Explorer。

A. 接受上列全部為本輪 Won't Have。
B. 上列太嚴 — 我要拿掉其中幾項（請用 Other 寫出要拿掉的）。
C. 還要再排除別的（請用 Other 補上）。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 接受上列全部為本輪 Won't Have。

## Q4. 若設計階段查到三雲都沒有可用的公開免帳號官方價目，本輪怎麼辦？

> 這是 R1 的範圍後果，不是重開 Q2 的存取策略。現在不定案，Inception 查證後會缺少決策。

A. 仍做 C1 — 全部單價走 Manual Override，畫面與預算照做；本輪官方 API 覆蓋可以是零。
B. 暫停本輪 C1 — 回到可行性，重新考慮 staging 價目憑證或縮雲，不在「零官方價」狀態上線。
C. 只對查到有公開價目的雲做官方價；若一雲都沒有，改走 B。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 仍做 C1 — 全部單價走 Manual Override，畫面與預算照做；本輪官方 API 覆蓋可以是零。

## Q5. 測試底線與部署資產同步，在 backlog 裡怎麼算完成？

> cost calculator 必須有 property-based testing [memory:M1]；新 HTTP 端點要 `TestClient`；改權限種子要 allow/deny；schema／seed 變更要同步 `schema_rbac.sql` 與 `DEPLOY.md` [memory:M7]。這些是完成條件，不是可選能力。

A. 內建於各 Must 能力的 Definition of Done — 不獨立成 backlog 項；沒寫進 DoD 視同該能力沒做完。
B. 獨立列成一個 Must 項（「測試底線＋部署資產同步」），集中追蹤。
C. Not yet defined
X. Other (please specify)

[Answer]: B. 獨立列成一個 Must 項（「測試底線＋部署資產同步」），集中追蹤。

## Consolidated Summary Confirmation

> 5 題已作答。矛盾檢查（§3）：無阻斷矛盾。Q1=B 不刪掉第二段，只允許被插隊時第一段可單獨上線；整輪仍含預算與超支。Q4=A 是 Q2／Q1a「無公開價目 → Override」在覆蓋為零時的範圍後果，不是重開「必須走官方 API」。
>
> 答案彙整：Q1=B（兩段增量，第一段可單獨上線）、Q2=B（Risk-first：先查證公開價目）、Q3=A（Won't Have = C2、C3、本輪 egress 列、核准流、inbox、staging 價目憑證、讀客戶帳單）、Q4=A（三雲都沒公開價目仍做 C1，全 Override）、Q5=B（測試底線＋部署資產同步獨立列為 Must）。

**Prompt**: Does this all look correct before I generate the artifacts?

A. Looks correct — 依這些答案產出 artifact
B. Request changes — 先修改一或多題答案

[Answer]: A. Looks correct — 依這些答案產出 artifact

## Assumption Confirmation

> 兩份 artifact 的 `## Assumptions & Open Questions` 皆非 `None.`，依 learned rule 需人工確認。
> **接受不等於把 assumption 變成事實** —— `[assumption]` 標籤會原樣保留。

**`scope-document.md` / `intent-backlog.md`（內容對應）**

- [assumption] 被插隊時第一段單獨上線，仍須滿足該段對應的測試與部署資產；不是「沒測也可以先上」[Q1] [Q5]
- [assumption] 三種變更的權限切法仍是設計階段必答 [feas:Q5]
- [assumption] 超支橫幅出現在哪些受保護頁，仍留設計 [feas:Q6]
- [assumption] proto-unit 粒度不是最終 Unit 切分，由 units-generation 檢驗

A. Accept assumptions — 保留 [assumption] 標籤，帶著這些未解項目進入下一關
B. Convert to follow-up questions — 補題釐清後再修訂 artifact

[Answer]: A. Accept assumptions — 保留 [assumption] 標籤，帶著這些未解項目進入下一關

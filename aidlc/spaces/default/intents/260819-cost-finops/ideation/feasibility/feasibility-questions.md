# Feasibility & Constraints — 釐清問題

> Stage: feasibility（Ideation 1.3）· Depth: Standard · Scope: mvp
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。
> 上游輸入：`../intent-capture/intent-statement.md`（intent-statement）。market-research 已跳過，其可選輸入（competitive-analysis、market-trends、build-vs-buy）依 scope 設計不存在。

## 已由上游定案、不重問

- 必須接雲端官方報價 API，且不得使用 production credentials [intent:Q12] [memory:M2] [memory:M3]
- 本輪只做 C1；C2／C3 不交付 [intent:Q9]
- 時數可隨時覆寫；官方 API 缺價或失敗時單價可覆寫並標記 Manual Override [intent:Q15]
- 每月預算上限與超支警告屬本輪 C1 必做；收件人為 FinOps 分析師、工程主管、雲端架構師 [intent:Q10] [intent:Q11]
- 超支時：成本畫面視覺標示＋進入產品時站內通知 [intent:Q16]
- 入口：Sidebar 的 C（成本／FinOps）＋產圖成功後 CTA「查看預估成本」[intent:Q13]
- 本輪不實作 FinOps 核准流 [intent:Q14]
- cost calculator 的測試必須含 property-based testing，不得只有 example-based [memory:M1]
- 新增或修改 HTTP 端點需 `TestClient` 測試；授權矩陣變更需 allow/deny 雙向測試 [memory:M5] [memory:M6]

## Sources

查證事實（僅用於出題與選項設計，依 ideation 規則不寫入產出 artifact 的設計層）：

- [code:C1] `backend/services/wa_rule_engine.py:125-164` — `parse_diagram_summary` 只抽出 mxCell 的 id／label／style 與連線，**沒有 SKU、執行個體型號、區域或價目表對應**。
- [code:C2] `backend/services/wa_rule_engine.py:874-878` — `detect_provider` 依關鍵字對 aws／gcp／azure 計分；回傳最佳雲別。
- [code:C3] `backend/models.py:80-89` — `user_diagrams` 存 `xml_data`，**無 provider 欄位**；雲別不是圖的持久屬性。
- [code:C4] `backend/services/rbac_seed_data.py:82-92` — C1 預設：`FinOps_Analyst` view+edit；`Project_Architect`、`Project_Editor`、`Project_Admin`、`SRE`、`Ops_Lead`、`Platform_Admin`、`Platform_Owner` 僅 view；`Developer`、`Platform_Engineer`、`Security_Reviewer` 全 false。
- [code:C5] `backend/services/rbac.py:44-47` — `Engineering_Manager` 別名對應 `Project_Editor`。
- [code:C6] `frontend/src/components/Sidebar.tsx:17-22` — 側欄只有架構（Workspace／Assessment）與 Admin；**沒有 C（成本／FinOps）分組**。
- [code:C7] `frontend/src/App.tsx` — 路由無成本／FinOps 路徑。
- [code:C8] 全 repo 搜尋 `notification`／inbox／user alert 資料表與模組：**沒有站內通知原語**（無 inbox 表、無未讀計數、無進產品橫幅元件）。
- [code:C9] 全 repo 搜尋 `cost_calculator`／`pricing_api`：**沒有 cost calculator 或官方報價客戶端**。`team.md` 記載 ADR-0006 三個 hard-constraint 落點「尚無對應實作模組」。
- [intent:Q2] 主要使用者為雲端架構師（產圖後要給可對外說明的成本數字）。
- [intent:Q9] 本輪只做 C1；C2／C3 不交付。
- [intent:Q12] 查報價必須走雲端官方報價 API，不得使用 production credentials。
- [intent:Q15] 時數可覆寫；API 缺價或失敗時單價可覆寫並標記 Manual Override。
- [intent:Q16] 超支：成本畫面視覺標示＋進入產品時站內通知。
- [stories:C1] `core-pillars.md` C1 AC：Estimates compute, database, cache, storage, network, CDN, **egress** and observability；Shows pricing assumptions and source timestamp。
- [memory:M1] `project.md#Testing Posture`: "**Property-based testing 為 hard constraint**（ADR-0006）。下列核心模組的測試必須包含 property-based 測試，不得只有 example-based：IaC generator、cost calculator、agent routing。其餘模組沿用 `org.md` 的預設門檻。"
- [memory:M2] `project.md#Scope Overrides`: "❌ **Out of scope（除非經新 ADR 核可）**：雲端供應商 production 環境、production credentials、environment-specific secrets、direct production IaC、destructive cloud operations、native iOS/Android app。"
- [memory:M3] `project.md#Forbidden`: "NEVER commit 私鑰或 AWS / Azure / GCP 的 credential 字串。"
- [memory:M4] `project.md#Tech Stack`: "**雲端範圍**：AWS / GCP / Azure 三雲的架構與維運設計"
- [memory:M5] `team.md#Testing Posture`: "**B — 新增或修改 HTTP 端點需 `TestClient` 測試**：斷言其 status code 與 `response_model` 的欄位集合。"
- [memory:M6] `team.md#Testing Posture`: "**A — 授權矩陣變更需 allow/deny 雙向測試**：任何 `role_permissions` 預設值變更，必須有測試同時驗證「該角色能做到」與「其他角色做不到」。"
- [memory:M7] `project.md#Mandated`: "ALWAYS 在變更**資料庫結構或部署必知的 schema／seed 行為**時同步更新部署資產（blocking，未完成不得標示相關 Construction／部署階段為完成）："
- [memory:M8] `project.md#Mandated`: "**ALWAYS 對每一項變更檢查 ADR-0006 security baseline 的四個面向（IAM、encryption、network exposure、audit logging）**"

## Q1. 本輪 C1 必須能對哪些雲查出官方報價？

> 查證：平台定位涵蓋 AWS／GCP／Azure [memory:M4]；圖上雲別目前是從 XML 關鍵字推得，並非圖的持久欄位 [code:C2][code:C3]。intent 要求官方報價 API [intent:Q12]，但三雲官方價目表的認證模型不同：有的可免帳號讀公開價目，有的需要專案或金鑰。本輪雲別決定整合面有多大，也決定 Q2 的憑證策略是否擋路。

A. 跟圖走 — 圖被辨識為哪一雲，就查那一雲的官方價目；三雲都要能報價（辨識失敗時走 Manual Override，不另選預設雲）。
B. 本輪只做 AWS — GCP／Azure 圖可看成本畫面，但單價一律 Manual Override，官方查價留後續。
C. 只做「免帳號公開價目」覆蓋得到的雲 — 需要金鑰或計費專案才能讀目錄的雲，本輪改走 Manual Override。
D. Not yet defined — 留到 requirements-analysis 再定。
X. Other (please specify)

[Answer]: A. 跟圖走 — 圖被辨識為哪一雲，就查那一雲的官方價目；三雲都要能報價（辨識失敗時走 Manual Override，不另選預設雲）。

## Q2. 在禁止 production credentials 的前提下，官方報價 API 的存取怎麼取得？

> 查證：intent 禁止 production credentials [intent:Q12][memory:M2][memory:M3]；repo 今日沒有任何報價客戶端 [code:C9]。這是本 stage 最主要的技術不確定性：沒有合法的價目來源，C1 無法從「對到圖上資源」走到「可重算的數字」。選項談的是**存取策略**，不是選定哪一家 SDK。

A. 只用公開、免帳號的官方價目端點 — 某雲若讀目錄必須帶金鑰或計費專案，該雲本輪不查官方價，改走 Manual Override。
B. 允許 staging 專用、僅能讀價目表的非 production 憑證 — 由部署環境注入、永不進 git；涵蓋必須帶金鑰才能讀目錄的雲。
C. 混合 — 能公開讀的就公開讀；只有在公開端點不存在時，才為該雲使用 B 的 staging 價目憑證。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 只用公開、免帳號的官方價目端點 — 某雲若讀目錄必須帶金鑰或計費專案，該雲本輪不查官方價，改走 Manual Override。

## Q3. C1 故事寫了 egress，本輪又排除 C3。流量費用算不算進本輪 TCO？

> 矛盾檢查：C1 驗收列出 compute、database、cache、storage、network、CDN、**egress**、observability [stories:C1]；intent 同時說本輪不交付 C3（data egress）[intent:Q9]。若不釐清，下游會把「一條 egress 單價列」做成整套跨雲路徑分析，或把 C1 驗收的 egress 靜默刪掉。

A. 本輪 TCO 不含 egress／資料傳輸列 — 那些等 C3；本輪估運算、資料庫、快取、儲存、網路、CDN、可觀測性。
B. 本輪可以有「圖上明顯的傳輸元件 → 一條官方價目列」；C3 仍負責跨雲／跨區路徑分析與熱點。不把路徑分析做進本輪。
C. 本輪把 C1 驗收列出的類別都估到（含 egress 的盡力官方價）；C3 之後再補路徑與熱點。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 本輪 TCO 不含 egress／資料傳輸列 — 那些等 C3；本輪估運算、資料庫、快取、儲存、網路、CDN、可觀測性。

## Q4. 「每月預算上限」掛在什麼上面？

> intent 已確認預算上限屬本輪 C1 必做 [intent:Q10]，但沒說上限是一張圖、一個專案、還是一次試算。粒度決定誰能改、超支警告何時觸發、以及資料是否隨圖走。

A. 每張架構圖一個月預算 — 換圖即換上限；警告綁在該圖的估價。
B. 每個專案／工作區一個月預算 — 同一專案多張圖共用上限。
C. 每次估價快照自己比對上限 — 沒有長期掛著的預算物件，只在當次畫面與通知裡比對。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 每張架構圖一個月預算 — 換圖即換上限；警告綁在該圖的估價。

## Q1a. 追問：Q1=A 與 Q2=A 如何並存？

> Q1=A 要求三雲都要能報價；Q2=A 規定讀目錄必須帶金鑰的雲本輪不查官方價、改走 Manual Override。若「能報價」=「打得到官方 API」，兩題互斥。需要定錨「能報價」的意思，不重開「跟圖走」或「禁止 production credentials」。

A. 以 Q2 為準 — 三雲都能打開成本畫面；只有公開免帳號價目覆蓋得到的雲才打官方 API，其餘雲的單價走 Manual Override。Q1 的「都要能報價」= 畫面可用，不是三雲都打官方 API。
B. 改 Q2 — 為了讓三雲都打官方價目，允許 staging 專用、僅能讀價目表的非 production 憑證（原 Q2=B 或混合 C；請在 X 註明選 B 或 C）。
C. 改 Q1 — 本輪只對公開價目覆蓋得到的雲做官方查價與完整 TCO；其他雲不承諾官方數字（比 Q1=B 更接近「本輪不做該雲官方價」）。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 以 Q2 為準 — 三雲都能打開成本畫面；只有公開免帳號價目覆蓋得到的雲才打官方 API，其餘雲的單價走 Manual Override。Q1 的「都要能報價」= 畫面可用，不是三雲都打官方 API。

## Q5. 誰可以改數字，誰只能看？

> 查證：今日種子權限下，只有 FinOps 分析師能對 C1 做變更（可進入成本畫面並改預算／覆寫）；雲端架構師（`Project_Architect`）與工程主管（系統角色對應 `Project_Editor`）只能看 C1，不能改 [code:C4][code:C5]。intent 卻說主要使用者是雲端架構師，且每日時數可隨時覆寫 [intent:Q2][intent:Q15]。權限擴張會改 seed，必須有 allow/deny 雙向測試 [memory:M6]，並記入 security baseline 的 IAM 面 [memory:M8]。本題不重開「警告收件人」（三人已定）。

A. 維持種子 — 只有 FinOps 分析師能改預算、時數與單價覆寫；雲端架構師與工程主管看得到圓餅、總額、超支標示與進產品通知，但不能改任何數字。
B. 架構師可改每日時數；只有 FinOps 能設預算與單價 Manual Override；工程主管維持只看（含超支標示與通知）。
C. 架構師可改每日時數；FinOps 與工程主管都能設預算；只有 FinOps 能做單價 Manual Override。
D. Not yet defined
X. Other (please specify)

[Answer]: C. 架構師可改每日時數；FinOps 與工程主管都能設預算；只有 FinOps 能做單價 Manual Override。

## Q6. 「進入產品時的站內通知」需要什麼能力？產品今日沒有通知原語。

> 查證：intent 已定超支時要在進入產品時看到站內通知 [intent:Q16]；repo 沒有 inbox、未讀計數或進產品橫幅 [code:C8]。本題不重開「要不要通知、通知誰」，只定本輪通知能力的上限，避免下游做成完整訊息中心。

A. 下次進入產品時出現一次可關閉橫幅 — 關閉後該次超支不再擋路；沒有歷史 inbox。
B. 只要估價仍超支，每次進入產品都看到橫幅 — 不能「永遠關閉」而讓超支消失；仍沒有歷史 inbox。
C. 要持久站內 inbox（未讀數、歷史）— 範圍明顯大於「進入時看到」。
D. Not yet defined
X. Other (please specify)

[Answer]: B. 只要估價仍超支，每次進入產品都看到橫幅 — 不能「永遠關閉」而讓超支消失；仍沒有歷史 inbox。

## Q7. 圖上對不到官方價目的元件，本輪怎麼處理？

> 查證：擷取結果只有 label／style，沒有 SKU [code:C1]。intent 已規定 API 缺價或失敗時可 Manual Override [intent:Q15]，但「圖上有盒子、價目表沒有對應項」是擷取缺口，不一定等於 API 失敗。若當成靜默省略，總額會看起來很完整但其實漏了資源，與「報價要對到圖上資源」矛盾。

A. 列出來但沒有單價 — 該列標成待覆寫；使用者不覆寫也可以看總額（未定價列不計入總額），並看到「N 項尚未定價」。
B. 從 TCO 省略，只顯示「N 個資源未計入」警告 — 不列名、不要求覆寫。
C. 擋下估價 — 有任何未對應項就不給總額，直到覆寫或從圖上排除。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 列出來但沒有單價 — 該列標成待覆寫；使用者不覆寫也可以看總額（未定價列不計入總額），並看到「N 項尚未定價」。

## Q8. 有沒有時程、預算或組織性阻塞？

> 可行性仍需確認沒有 change freeze、競爭優先工作或依賴他人的時窗。本 intent 的觸發是故事已寫、產圖後要銜接估價，不是外部事故期限。

A. 無阻塞 — 隨開發能量排入，無時間盒。
B. 有時間盒 — 希望在特定時間內收斂（請在 X 補充天數或日期）。
C. 有競爭優先事項 — 本功能隨時可能被插隊，接受中斷後再續。
D. Not yet defined
X. Other (please specify)

[Answer]: C. 有競爭優先事項 — 本功能隨時可能被插隊，接受中斷後再續。

## Consolidated Summary Confirmation

> 全部 9 題已作答（8 題原題＋Q1a 追問）。矛盾檢查（§3）：Q1a=A 解消 Q1=A 與 Q2=A 的「三雲都要官方價」vs「必須帶金鑰就不查官方價」衝突——「能報價」定錨為成本畫面可用，官方 API 僅限公開免帳號價目覆蓋得到的雲。
> 記入 artifact 的張力（非矛盾）：(1) C1 故事 AC 含 egress，本輪 TCO 不含 [Q3=A][intent:Q9] → 本輪驗收切片，egress 列留給 C3；(2) Q5=C 區分時數／預算／單價三種變更，既有權限只有 view／edit／review → 切法留設計階段，本 stage 只鎖產品語意；(3) 哪些雲實際有公開免帳號價目，本 stage 不預判，列為依賴。
>
> 答案彙整：Q1=A（跟圖走、三雲畫面都要能開）、Q2=A（只用公開免帳號官方價目）、Q1a=A（以 Q2 為準，其餘雲 Manual Override）、Q3=A（本輪 TCO 不含 egress）、Q4=A（每張架構圖一個月預算）、Q5=C（架構師改時數；FinOps 與工程主管設預算；僅 FinOps 單價覆寫）、Q6=B（超支期間每次進入產品都看到橫幅，無 inbox）、Q7=A（未對應列名且不計入總額，顯示 N 項尚未定價）、Q8=C（有競爭優先事項，可被插隊）。

**Prompt**: Does this all look correct before I generate the artifacts?

A. Looks correct — 依這些答案產出 artifact
B. Request changes — 先修改一或多題答案

[Answer]: A. Looks correct — 依這些答案產出 artifact

## Assumption Confirmation

> 三份 artifact 的 `## Assumptions & Open Questions`（raid-log 為 `## Assumptions（假設）` 表格）皆非 `None.`，依 learned rule 需人工確認。
> **接受不等於把 assumption 變成事實** —— `[assumption]` 標籤會原樣保留在 artifact 中。

**`feasibility-assessment.md`**

- [assumption] 本輪不要求三雲都打得到官方 API；只要公開免帳號價目覆蓋得到的雲走官方價、其餘走 Manual Override，C1 畫面仍算交付 [Q1a] [Q2]
- [assumption] 內部平台的估價資料不受 PCI／HIPAA／SOC 2／GDPR 等外部框架約束；此判斷未經法務或合規方獨立確認
- [assumption] 「進入產品」指使用者已登入後進入受保護畫面；橫幅出現在哪些頁面留待設計，本階段只鎖定「超支期間每次進入都看到、不能永遠關閉」[Q6]
- [assumption] C1 故事驗收中的 egress 本輪不交付，不視為刪除 baseline 故事，而是本 intent 的驗收切片；不回改 `stories.md` [Q3] [intent:Q9] [stories:C1]
- [assumption] （開放問題）現有 view／edit／review 能否表達 [Q5] 的三種變更，或需要更細的動作，本階段不定案，列為設計階段必答 [Q5]

**`constraint-register.md`**

- [assumption] 內部平台，無外部法規框架適用於估價資料；未經法務或合規方獨立確認
- [assumption] 公開免帳號官方價目至少覆蓋部分雲，其餘雲 Manual Override 仍可交付 C1 畫面 [Q1a] [Q2]
- [assumption] （開放問題）view／edit／review 三旗能否承載 [Q5] 三種變更，留待設計階段
- [assumption] （開放問題）超支橫幅出現在登入後的哪些受保護頁，留待設計；本階段只鎖定「超支期間每次進入都看到」[Q6]

**`raid-log.md`**（Assumptions 表 A1–A5，內容與上列對應）

A. Accept assumptions — 保留 [assumption] 標籤，帶著這些未解項目進入下一關
B. Convert to follow-up questions — 補題釐清後再修訂 artifact

[Answer]: A. Accept assumptions — 保留 [assumption] 標籤，帶著這些未解項目進入下一關

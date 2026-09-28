# User Stories — 故事計畫與釐清問題

> Stage: user-stories（Inception 2.4，mob）· Depth: Standard · Scope: mvp
> Intent: `260819-cost-finops`（C1 第一輪）
> 作答：在每題 `[Answer]:` 後填選項字母。X 為自由填答。
> **成本揭露**：本題組共 4 題。答完後起草 personas／stories，再平行派出 design／developer／quality 盲審，整合後經 reviewer 與你的核可。三位盲審是本 stage 固定成本。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 本輪只做 C1；不做 C2／C3、egress、核准流、inbox | [req] 範圍外 |
| 兩段增量皆 Must；第一段可單獨上線 | [req] 意圖分析 |
| 三個受益者：雲端架構師、FinOps 分析師、工程主管（種子對應 `Project_Editor`） | [intent]／[feas] |
| 架構師改時數與估價區域；FinOps＋工程主管設預算；僅 FinOps 覆寫單價 | [req] FR-3.3／FR-4.1／FR-6.2／FR-2.4 |
| 跟圖走：每次重算以目前 XML 重擷取，列以 mxCell id 對齊 | [req] FR-1.5 |
| 月費公式、預設時數 24、USD、圓餅四類、多圖一條橫幅 | [req] Q3–Q6 |
| AC 禁止「正常／成功」；PBT／TestClient／e2e 是 DoD 不是獨立使用者故事 | [req] DoD、[tp] |
| 權限如何對到 view／edit／review 留設計 | [req] OQ-1 |

## Sources

- [req] `../requirements-analysis/requirements.md`
- [intent] `../../ideation/intent-capture/intent-statement.md`
- [flow] `../../ideation/rough-mockups/user-flow.md`
- [tp] `../practices-discovery/team-practices.md`
- [kb] `aidlc/spaces/default/codekb/cloud/business-overview.md`、`component-inventory.md`
- [baseline-C] `aidlc/spaces/default/intents/260802-default/inception/user-stories/stories.md` 的 **C. 成本估算與 FinOps**（C1／C2／C3）與同目錄 `personas.md`（Alex／David／Hannah）

## 故事計畫（供作答參考）

- **Persona**：以上游已確認受益者為準，不新創角色
- **格式**：`As a [persona], I want [goal], so that [benefit]`；AC 用 Given/When/Then，可觀測結果
- **優先序**：兩段皆 Must Have；MVP 邊界正式定於 delivery-planning，故事優先序只供參考
- **INVEST**：第一段與第二段允許依賴（第二段建立在總額上）；完全 Independent 不可得，註記即可

---

## Q1. Persona 寫幾個？

> 上游已確認三個受益者都會碰到 C1。baseline C1 寫 David＋Hannah；C3 才帶 Alex。本輪 intent 的主要使用者是架構師，故三人皆要有故事。Admin 類角色若無 C1 view 則看不到入口。
> 角色名沿用 [baseline-C]：Alex（`Project_Architect`）、David（`FinOps_Analyst`）、Hannah（`Project_Editor`）。

A. **三個都寫完整 persona**（雲端架構師、FinOps 分析師、工程主管），並註明無 C1 view 者看不到入口。**（建議）** 對齊 intent 受益者與三種變更權，下游不會漏橫幅收件人。
B. **只詳寫架構師**，FinOps／工程主管用一段「次要角色」帶過。代價：預算與覆寫故事容易變成無 persona 的任務。
C. **再加上 Platform_Admin 等管理角色** 作為完整 persona。代價：他們對 C1 的利益未被 intent 確認，屬無來源需求。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 三個都寫完整 persona：Alex／David／Hannah（沿用 baseline 名與 RBAC），並註明無 C1 view 者看不到入口。

---

## Q2. 故事怎麼切？

> 一則對一條 FR 會產出「作為系統我要持久化」的偽故事。依使用者價值切，可用對照表追溯 FR。

A. **依使用者可感知切片切，容許多 FR 進同一則故事**；第一段（看估價／改時數／入口／覆寫）與第二段（預算／超支橫幅）分開成 Must 故事，讓第一段可單獨上線。**（建議）** 對齊 scope 兩段增量與 INVEST Valuable。
B. **一則故事對一個 FR 群**（FR-1 擷取、FR-2 單價、FR-3 畫面……）。代價：擷取與持久化對使用者不可見，易成技術任務。
C. **依 persona 各寫一套完整流程**（架構師一組、FinOps 一組、工程主管一組）。代價：同一總額畫面會重複三次，Independent 更差。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 編號沿用 C1；依使用者切片切成多則 Must 故事（第一段可單獨上線）。不寫 C2／C3。

---

## Q3. 測試底線（PBT、TestClient 403、Playwright）寫在哪？

> [tp] 與 [req] DoD 已鎖定這些是交付條件，不是使用者想要的新能力。

A. **不寫獨立「作為 QA」故事**；把對應自動化斷言寫進引入該 HTTP／畫面的故事 AC（例如覆寫故事含無權 403，Cost 頁故事含 e2e 可見總額）。**（建議）** 符合 DoD 定位，避免 backlog 出現沒有使用者的故事。
B. **另寫 1–2 則測試故事** 讓測試工作在 backlog 可見。代價：與 DoD 重複，且 persona 不真實。
C. **故事與 AC 都不提測試**，全部留給 tcms-test-cases。代價：Construction 容易漏 403／PBT。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 不寫獨立 QA 故事；PBT／403／e2e 寫進引入該 HTTP／畫面的故事 AC。

---

## Q4. 第二段（預算＋橫幅）在 backlog 的形狀？

> 兩段皆 Must；被插隊時第一段可單獨上線。故事層要讓 delivery-planning 排得出「先上第一段」。

A. **獨立 Must 故事（或一小組）描述設預算與超支標示／橫幅**，標明依賴第一段總額；第一段故事的 AC 不要求橫幅。**（建議）** 對齊 FR-6／FR-7.1 分段驗收。
B. **全部寫進同一則「完整 C1」Must 故事**。代價：無法單獨驗收第一段上線。
C. **第二段標 Should Have**，讓 delivery-planning 可以砍。代價：直接違反已核可 scope（兩段皆 Must）。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 第二段獨立 Must 故事（預算＋超支橫幅），依賴第一段總額；第一段 AC 不要求橫幅。

---

## Consolidated Summary Confirmation

以下為本站 4 題答案，並已鎖定沿用 baseline C 柱血緣。確認後才會起草 personas／stories，再派出 mob 盲審。

1. **Q1=A** — 三個完整 persona：Alex（`Project_Architect`）、David（`FinOps_Analyst`）、Hannah（`Project_Editor`）；無 C1 view 看不到入口。
2. **Q2=A** — 編號沿用 **C1**；依使用者切片切成多則 Must；**不寫 C2／C3**。C1 內文以本輪 `requirements.md` 覆寫，不照抄 baseline 的 8 小時／流量重置／inbox／Billing Alarm。
3. **Q3=A** — 測試底線寫進故事 AC，不另寫 QA 故事。
4. **Q4=A** — 第二段（預算＋超支橫幅）獨立 Must，依賴第一段總額；第一段不驗橫幅。

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct

---

# Mob 中場提問（Round 1 後的判斷題）

> 三位協作者盲審後，事實類 OBJECT 已折入 `stories.md`。下列兩題屬 stage-protocol §5 **judgment call**（兩種立場都合理）。

## Q5. C1-1 要不要再拆？

> developer：C1-1 一次引入 router／calculator／pricing_client／Cost 頁／Sidebar／CTA／schema，超出 1–2 天分支。建議拆成「入口＋擷取」「官方價＋總額／圓餅」「產圖 CTA」三則仍有 Alex 價值的 Must。
> 反面：Q2=A 已拒絕按 FR 切；再拆三則會讓第一段 backlog 變長，delivery-planning 仍可把同一則切成多個 Bolt。

A. **現在拆成三則 Must**（入口＋擷取／官方價＋圓餅／CTA），皆屬第一段。**（建議若你希望 Construction 一則故事對一個 Bolt）**
B. **維持一則 C1-1**，在故事上加「delivery-planning 可拆 Bolt」註記，本檔不再拆。**（建議若你希望 backlog 維持五則）**
C. **拆成兩則**：入口＋擷取＋CTA 一則；官方價＋總額／圓餅一則。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 現在拆成三則 Must（入口＋擷取／官方價＋圓餅／CTA），皆屬第一段。

---

## Q6. 每日時數的合法區間？

> design：沒有上界時，「立刻重算」可讓 100 小時變成對外月費。requirements 未鎖 0–24。預算金額上界本輪不另問（正數 USD 即可）。

A. **每日時數必須在 0–24（含）**；非法輸入不送出並有文字錯誤。**（建議）**
B. **禁止負數與非數字**；允許 >24（例如 24×多台折進一列），上界留設計。
C. **本檔不寫區間**，全部留 application-design。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 每日時數必須在 0–24（含）；非法輸入不送出並有文字錯誤。



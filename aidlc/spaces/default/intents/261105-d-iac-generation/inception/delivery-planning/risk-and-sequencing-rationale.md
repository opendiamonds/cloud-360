# Risk and Sequencing Rationale — 為何是這兩條 Bolt

> Stage: delivery-planning · Intent: `261105-d-iac-generation`  
> 上游：units DAG、contract-summary、stories、Q1–Q5=A。

## 啟發法

**不使用正式 WSJF 表**（未選 Q1=D）。候選有意義的部署切片本質上只有兩個 unit。

實際採用：

| Bolt | 啟發法 | 一句話 |
|---|---|---|
| B1 | **risk-first**（閘／授權／契約） | 最高失敗模式是繞過 D3 閘與無權非 403；契約 R-01／R-02 也在 U1 |
| B2 | value／可見面（可∥B1） | UI 證明路徑可走完；e2e 依附真實或 stub API |

**不是** walking-skeleton-first 儀式：本 intent 已定 `skeleton: off`。B1／B2 皆為普通 Construction Bolt。

## 為何不走其他切法

| 被拒路徑 | 擋下理由 |
|---|---|
| 先 U2 再開 U1（Q1=B） | 「有按鈕無真實閘」窗口；與 Q5 主風險相反 |
| 單一粗 Bolt 捆 U1＋U2（Q2=B） | 失去平行與較小 PR；DAG 並未要求同批 |
| 把 U1 拆成 generate／scan／rewrite 三 Bolt（Q2=C） | 契約與 Session 閘是一體；重複開工 |
| 強制串行合入（Q3=B） | 浪費 DAG 無邊；平行＋e2e 延後即可 |

**無拓樸偏離**：兩 unit `depends_on: []`；平行合法。經濟敘事寫「先證明閘」不強迫 merge 順序。

## 最早要打掉的風險（Q5=A）

| 風險 | 為何最早 | 落在 |
|---|---|---|
| 無 D2 成功報告仍可 D3 | US4.1／R-01 核心；繞過＝產品失敗 | B1 Session 閘＋TestClient |
| 切圖後舊 `report_id` 仍可用 | US1.3；行程內作廢必須後端強制 | B1 |
| 無權非 403 | US6.1；種子領先漏授權 | B1 成對測試 |
| download／scan 契約歧義（advisory R-01／R-02） | 實作者猜測→錯誤 RBAC 或錯 session | B1 DoD 必關（Q4=A） |

LangGraph／OpenRouter 慢（Q5=B）**不是** B1 完成閘：可 stub。Playwright test-id（Q5=C）屬 B2。OpenAPI drift（Q5=D）屬 B1 CI，次於閘正確性。

## 規模直覺（非正式）

| Bolt | 相對規模 | 風險降低 | 使用者可見價值 |
|---|---|---|---|
| B1 | L | 高（閘／PBT／RBAC／契約） | 中（API／TestClient；演示需 UI） |
| B2 | M | 中（空態／modal／權限入口） | 高（工作區可見路徑） |

平行開工時：風險軌（B1）與可見軌（B2）同時推進；整合驗證在 API 可用後。

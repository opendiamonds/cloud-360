# Unit of Work — Story Map

> Maps Cloud-360 user stories to development units.  
> Focus: **A1 / A2 / A3 / A4 / A5 / J**. Other stories listed as unassigned.


### 1. 已開發／進行中 Story → Unit

| Story | 標題 | Unit ID | Unit 名稱 | Construction 追溯 | 開發狀態 |
|---|---|---|---|---|---|
| **J1**–**J5** | 身分／RBAC／註冊授權 | `U-J` | Identity & RBAC | `j/` | ✅ Core＋J5 |
| **A1** | 自然語言轉架構 | `U-A1` | Architecture Design Generation | `a1/` | ✅ Code |
| **A2** | 畫布協同編輯 | `U-A2` | Canvas Collaborative Editing | `a2/` | 🔄 核心；AC 部分缺 |
| **A3** | Well-Architected 評核與模擬 | `U-A3` | Well-Architected Review | `a3/` | ✅ MVP Code；🔄 Lens Editor Inception ✅ → Construction 待核准 |
| **A4** | 聊天與上次開啟圖 | `U-A4` | Chat & Last-Opened Persistence | `a4/` | ✅ Code |
| **A5** | 分享與即時共編 | `U-A5` | Diagram Sharing & Real-time Collab | `a5/` | 🔄 核心；游標缺 |

### 2. Unit → Stories（反向）

| Unit ID | Stories | 一句話 |
|---|---|---|
| `U-J` | J1–J5 | 身分、RBAC、註冊授權 |
| `U-A1` | A1 | NL → XML 產圖（Agent SDK） |
| `U-A2` | A2 | 畫布編輯、存檔、多圖 |
| `U-A3` | A3 | WA 評核：規則＋ReviewAgent、SSE、儀表板、PDF；Lens 標準編輯（Security_Reviewer） |
| `U-A4` | A4 | 聊天持久化、bootstrap |
| `U-A5` | A5 | 分享、WebSocket |

### 3. 產品權限欄 vs 開發 Unit

| 產品矩陣欄 | 對應開發 Units |
|---|---|
| 架構圖生成（A1＝A2＝A4） | `U-A1` + `U-A2` + `U-A4` |
| **Well-Architected 評核（A3）** | **`U-A3`** |
| 共編／分享行為 | `U-A5` |
| 使用者／細項（J） | `U-J` |

### 4. A3 AC 歸屬

| AC／場景 | 歸屬 | 期別 |
|---|---|---|
| 規則＋LLM 建議、分數／發現、持久化 | `U-A3` | ✅ MVP |
| 三入口（CTA／按鈕／儀表板）、SSE | `U-A3` | ✅ MVP |
| 同 Agent SDK、獨立 ReviewAgent | `U-A3` | ✅ MVP |
| PDF 下載 | `U-A3` | ✅ 增量 |
| Lens 五大柱標準動態編輯（DB） | `U-A3` | 🔄 Inception ✅；Construction 待 |
| SPOF／AZ 模擬、riskRules UI、lens 版本／重跑 | `U-A3` | ⏳ 下期 |

### 5. 尚未指派 Unit 的 Stories

| Stories | Pillar |
|---|---|
| B1–B3 | B |
| C1–C3 | C |
| D1–D3 | D |
| E1–E3 | E |
| F1–F3 | F |
| G1–G3 | G |
| H1–H3 | H |

### 6. 覆蓋檢查

- [x] A1, A2, **A3**, A4, A5, J1–J5 皆已指派且僅一個開發 unit  
- [x] A3 已自「未指派」移除  

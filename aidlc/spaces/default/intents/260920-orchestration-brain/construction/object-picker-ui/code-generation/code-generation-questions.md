# Code Generation 問題檔 — `U16 object-picker-ui`

## 核可範圍說明

本題核可的是同目錄下的 `code-generation-plan.md`（14 步，含其內嵌的 Testing Contract，`test-after`、`standard`）與 `unit-test-instructions.md`。明白揭露（逐條對應計畫第三、七節）：

- **交付規模**：新檔 `objectPickerModel.ts`、`objectPickerData.ts`、`ObjectPicker.tsx`、`ObjectPickerGroup.tsx`、`ObjectPickerCreateForm.tsx`、`object-picker.spec.ts`。零後端、零 DDL、零環境變數、零 secret、零 workflow 檔、零新依賴。
- **會修改三個不屬本單元的檔**：`U14` 的 `ContextBar.tsx`（加鈕與選單開關、斷線處置；不動五態與名稱節點）、`U17` 的 `a11y.spec.ts`（加兩個掃描點，基準清單維持空）、共用的 `eslint.config.js`（末端加選單檔案的禁令區塊，既有區塊不動）。
- **多處上游設計被更正附錄取代**，實作照附錄（計畫第二節第二張表逐條列出）。
- **`AC9.2.3` 讀為 Deferred**，只交付畫面面。
- **本機無 Docker**：以 `vite preview` 跑，全部走攔截層。
- **關卡事項 `G-1`–`G-6`** 列於計畫第七節第 6 點，待使用者裁決，不影響本計畫的實作內容。

## Plan Approval

[Approval Fingerprint]: sha256:v3:604574d1e1b03f242e04cdae33de62989353d9f779a836961f1647c18c749480
[Planned Source]: 7cae46098811134951f3cd078f8182baea610bca91d0056aa90cbacbad7a8814
- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan
[Answer]: Approve Plan

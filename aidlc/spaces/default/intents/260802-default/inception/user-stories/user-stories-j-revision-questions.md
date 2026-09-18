# User Stories Pillar J — Revision Questions

> Stage: Inception → User Stories (revision)  
> Scope: `aidlc-docs/inception/user-stories/stories.md` §J (J1–J5)  
> Context: 現況已實作 JWT 登入、Sidebar／RouteGuard、Admin 使用者角色頁、細項矩陣（A1=A2=A4 合併、矩陣 UI 僅含 J3a／J3b）；與原文部分 AC 可能不一致（如 MFA、重設密碼、Audit Log UI）。


請回答下列問題，以便精確修正 Pillar J 使用者故事。（已於 2026-07-17 依答案套用修訂。）

---

## Question 1
你主要想修正 Pillar J 的哪個範圍？

A) 對齊已實作行為（把故事改成「現況真實能驗收」的描述，拿掉未做的 MFA／重設密碼等）

B) 擴充需求（保留理想 AC，並明確標出「已做／未做／下期」）

C) 重寫故事結構（例如合併／拆分 J1–J4，或改角色命名）

D) 只改某幾個 AC／BDD 文句（下一題指定）

X) Other (please describe after [Answer]: tag below)

[Answer]:B

---

## Question 2
與**實作落差**最大、你最在意要改的是哪些？（可複選，寫在 Answer，例如 `A,C,E`）

A) **J1**：拿掉／改寫 MFA、密碼複雜度策略、重設密碼（目前僅帳密 + JWT）

B) **J2**：改為「角色 × Story 細項」驅動可見性（三旗標全空才隱藏），而非只寫 Role 屬性

C) **J3**：拆成「指派角色」與「啟停用帳號」；Audit Log 改為「已記錄／UI 未做」或刪除 UI 期待

D) **J4**：寫明 A1＝A2＝A4 合併為「架構圖生成」一欄；矩陣不含完整 Pillar J（僅 J3a／J3b）

E) **角色命名**：Stories 內 `Security_Admin`／`Engineering_Manager` 等別名改為正式 handle

F) 以上全部對齊實作

X) Other (please describe after [Answer]: tag below)

[Answer]:X
針對剛註冊的使用者，不可賦予他任何角色，並且需要提供給平台管理員授權邀請，請管理員賦予剛註冊的使用者角色，註冊時會詢問使用者想要被授權哪個角色，並列出角色介紹以及該角色可使用的功能，選擇後向管理員提出申請，管理員也有權限在後台刪除使用者

---

## Question 3
修正後的 J 故事，雙語要怎麼處理？

A) 中文與 English Version **同步改**（維持 repo contract）

B) 先只改中文，English 標註待補（不建議，可能違反 contract）

X) Other (please describe after [Answer]: tag below)

[Answer]:Ａ

---

## Question 4
改完 `stories.md` 後，還要連動更新哪些？

A) 只改 `stories.md`

B) 連動 `personas.md`（若角色敘述不一致）

C) 連動 `construction/plans/role-permission-design.md` 對照表／AC

D) 連動 `aidlc-docs/inception/user-stories/` 以外相關 unit／summary（J code summary）

E) A + 你指定的項目（請在 Answer 列出）

X) Other (please describe after [Answer]: tag below)

[Answer]:ＢＣＤ

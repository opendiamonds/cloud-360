# Team Allocation — 統一入口大腦

<!-- Stage: delivery-planning（Inception 2.9）· Record: 260920-orchestration-brain -->

## 這份檔在做什麼

把 **Bolt**（一次建置通過，做完一個或多個工作單元，結束時有東西能跑、能展示）
指派給執行者。當有多個團隊時，這份檔就是 **Program Board**——一張看板，讓每個團隊
看得到自己負責哪些 Bolt、以及誰在等誰。

本檔可獨立閱讀，不需先看 `bolt-plan.md`。

## 結論：全部由 AI 執行，沒有人類團隊分工

**`team-formation`（1.5）在本 intent 未執行。** 本輪查證 `ideation/` 目錄下只有
`intent-capture`、`feasibility`、`scope-definition`、`rough-mockups`、`approval-handoff`
五個站的產出，沒有 `team-formation/`。

依 stage 檔的規定：當 1.5 被 skip 時，**所有 Bolt 由 `aidlc-developer-agent`（AI）執行**。

**因此本檔不是 Program Board**——Program Board 是團隊數大於 1 時才有的東西，
這裡只有一個執行者。

## 指派表

| Bolt | 單元 | 執行者 | 說明 |
|---|---|---|---|
| B1 | `U1`、`U2`、`U3`、`U6` | `aidlc-developer-agent` | 兼做五項跨單元未決事項的定案 |
| B2 | `U4`、`U7` | `aidlc-developer-agent` | |
| B3 | `U5`、`U8` | `aidlc-developer-agent` | |
| B4 | `U10`、`U12` | `aidlc-developer-agent` | |
| B5 | `U11` | `aidlc-developer-agent` | 進入條件須人工裁決，見下 |
| B6 | `U13`、`U14` | `aidlc-developer-agent` | |
| B7 | `U15`、`U16` | `aidlc-developer-agent` | |
| B8 | `U17` | `aidlc-developer-agent` | |
| B9 | `U9` | `aidlc-developer-agent` | **條件式**，見下 |

**9 個 Bolt、17 個單元、1 個執行者。**

## 人在哪裡介入

「全部由 AI 執行」不等於「沒有人的參與」。本計畫有**三類**必須有人的點：

### 一、每個 Bolt 的核准關卡

`[D4]`=A 定案序列執行——一次一個 Bolt，做完再做下一個。每個 Bolt 結束時有一次核可，
核可後才開始下一個。合併進 `ut` 即部署到自有 staging，所以**每個 Bolt 邊界都是一次
真實部署**。

### 二、B5 的進入條件——這一項 AI 不得自行決定

`U11`（路由層）開工前必須先有 `OQ-10`（路由層能否產出可比較的信心值）與 `OQ-4`
（路由層模型定案）的答案，**兩者必須一併決定**。它們的落點 `nfr-requirements`（3.2）
是 CONDITIONAL，而 `nfr-design` 的執行條件依賴它已執行，故兩站會一併 skip。

**若該站被 skip，須重新提交使用者裁決，不得由實作者當場決定。**
理由是 `[RA:FR1.6]` 逐字寫的那句話：「若實作出一個不輸出信心值的路由層，`FR1.3` 會
**靜默永不觸發**，而文件上看起來已解決」。這類失敗不會有紅燈，只有人會發現。

### 三、B9 的執行與否

`OQ-13`（清除 workflow 如何取得資料庫連線）是 `U9` 的單元層級阻塞。其落點
`infrastructure-design` 與轉移目標 `deployment-pipeline` **皆為 CONDITIONAL**——
兩者都 skip 時須重新提交使用者。若到 B9 仍未定案，該 Bolt 不執行，
`U9` 與 `[RA:FR4.5]`（90 天保存）列為已知未交付項。

## Construction 怎麼迭代——每個單元做完再做下一個

本計畫的每個 Bolt 都以「結束時有東西能跑、能展示」定義，且**每個 Bolt 邊界都是一次
真實部署**（合併進 `ut` 即部署到自有 staging）。那要求設計與實作**在同一個增量內
一起走完**，而不是先把 17 個單元的設計全做完、最後才開始寫 code——後者會讓第一份
可運行的成果落在整條流程的末端，與本計畫的九個信心假說全部牴觸。

**故 Construction 以「單元優先」迭代**：單元依 Bolt 順序一個一個設計並實作完成，
再換下一個。已記錄於工作流程狀態。

**這個選擇有兩個要先知道的後果**：

1. **各階段的核可關卡會集中在區塊末端一次串起來**（每個階段一次人工核可），
   不是每做一件事就停一次。
2. **不會有平行批次建置**——實作由單一序列的走查承載，依 Bolt 的建置順序進行。
   這正是 `[D4]`=A（序列執行）要的形狀，不是限制。

## 為什麼沒有 mob

**mob programming**（整個團隊同時、同地、在同一台電腦上做同一件事）在有多位人類
開發者時是最快的知識傳遞方式。本 intent 只有一個 AI 執行者，mob 的前提不成立，
故本檔不含 mob 組成、driver／navigator 輪替或輪替節奏。

若日後本 repo 引入人類團隊分工，`team-formation`（1.5）會產出團隊，屆時本檔才會
變成真正的 Program Board。

## Assumptions & Open Questions

- 本檔的「全部由 AI 執行」是 `team-formation` 未執行的**直接後果**，不是本站的選擇
  ——stage 檔逐字規定了這個 fallback [assumption]
- 三類人工介入點中，第二與第三類**沒有機制保證它們會被執行**：它們依賴屆時判定
  skip 的執行者記得重新提交使用者。本檔明寫它們，但明寫不等於強制 [assumption]
- 未估工時、未估每個 Bolt 的時間——沒有實證輸入，估了也是虛假精確 [assumption]

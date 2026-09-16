# NFR Requirements — U-2 受管區塊渲染與雜湊

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-2-managed-block · kind: library -->

## CONDITIONAL 適用性判定

| 條款 | 判定 | 依據 |
| --- | --- | --- |
| Performance | ❌ | `produces_kinds` 限 `[service, ui]`，本單元為 `library` |
| Security | ✅ | 本單元使用 sha256，需釐清它**是不是**安全控制（結論：不是） |
| Scalability | ❌ | 同 `produces_kinds`，限 `[service]` |
| Tech stack selection | ✅ | **C-6 的承載形式上游未指定**——`components.md` 的 C-6 條目沒有「承載形式」那一列（C-1／C-2 有） |
| Skip if 兩者皆無 | ❌ | 上述兩項皆有 |

**判定：EXECUTE**，產出兩份。

## 問題

### Q1. C-6 的承載形式？

C-6 有 `render`／`parse`／`content_hash` **三個各自獨立的操作**，而 composite action 只有一個進入點。U-1 的情況不同——它是「record 文字 → Decision」的單一管線，不需分派。

A. **單一 action ＋ `operation` 輸入**：`.github/actions/aidlc-sync-block/`，用 `operation: render|parse|hash` 分派。看得到的效果：三個操作共用同一份格式定義與版本分派邏輯（`FORMAT_VERSION`、解析器集合），不會被複製三份——`team.md` 的「單一真實來源」規則正是禁這個；且 `REQUIRED_FILES` 只需鎖一個路徑。代價：`inputs` 成為聯集（每次呼叫都有用不到的 input），`outputs` 亦然，YAML 層看不出哪些組合合法。

B. **三支獨立 action**：每支的 `inputs`／`outputs` 都真實且完整，呼叫端不會傳錯組合。代價：格式定義與版本分派要麼複製三份（直接違反單一真實來源），要麼再抽一層共用檔——而 composite action 沒有乾淨的共用機制，只能靠相對路徑 source。

C. **併入 U-1 的 `aidlc-sync-map`**：部署面最簡。代價：把 U-1 與 U-2 兩個單元綁到同一個檔，兩者的完成判準會在同一個檔上互相干擾；且 `components.md` 明分 C-1／C-2（純函式層）與 C-6（呈現層）為不同層。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T11:52:24Z（讀自 date -u）· 單一 action ＋ operation 輸入 -->

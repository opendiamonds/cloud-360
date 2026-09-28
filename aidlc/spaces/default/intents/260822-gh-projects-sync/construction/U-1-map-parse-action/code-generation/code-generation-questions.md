# Code Generation Questions — U-1 映射與解析 composite action

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-1-map-parse-action -->

## Plan Approval

`code-generation-plan.md` 共 11 步，涵蓋 `action.yml` ＋ `map.sh` ＋ fixture 集 ＋ runner ＋ 總函式性檢查。

**計畫層有兩項需一併裁決的決定**（兩項都擴充了 `unit-of-work.md` 字面的交付清單，故不由 AI 自行認定）：

1. **邏輯放 `map.sh`，`action.yml` 只做介面轉接** — 讓「零 I/O」成為可測事實、fixture 不必起 workflow 就能斷言。代價：多一個交付檔。
2. **fixture runner（`run-fixtures.py`）由 U-1 交付** — 上游未指定「斷言器」的擁有者，這是真實的契約缺口。理由是完成判準寫在 U-1、且 U-9 已定案用 `python3`。替代方案是歸 U-9，把 U-1 的完成判準降為「fixture 集齊備」。

**選項**：

- **Approve Plan** — 依計畫產生程式碼（含上述兩項決定）
- **Request Changes** — 修改計畫後重新送審

[Answer]: Approve Plan  <!-- 2026-08-30T06:19:46Z（讀自 date -u）· 人工核可，含兩項擴充交付清單的決定 -->


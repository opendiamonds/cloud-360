# Code Generation Questions — U-2 受管區塊渲染與雜湊

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-2-managed-block -->

## Plan Approval

9 步計畫，交付 `.github/actions/aidlc-sync-block/`（`action.yml` ＋ `block.sh` ＋ fixture ＋ runner），`operation: render|parse|hash` 分派。

**三項需一併裁決的決定**（詳見 `code-generation-plan.md` 開頭）：

1. **是否現在補 `has_managed_marker`** — R-3.4「不覆寫較新版本區塊」的保護目前字面上不存在（`parse` 對「沒有標記」與「版本較新」回同一個 `null`）。ADR-0015 §6 指名 **Bolt 1 gate** 為確認人，本閘門即是。傾向補（純新增、不動已核可簽章）。
2. **`FORMAT_VERSION` 起始值 `1` 還是 `2`** — 首次上線既有受管 item 為 0，「bump」無對象。傾向 `1` ＋ 登錄表首筆註明零成本。
3. **`format-migrations` 用 `.md` 還是 `.json`** — 傾向 `.md`（人可讀、diff 好看）。

**選項**：

- **Approve Plan** — 依計畫與上述三項傾向產生程式碼
- **Approve，但不補 `has_managed_marker`** — 其餘照計畫，R-3.4 的保護留待後續，實作寫明「保護未生效」
- **Request Changes** — 修改計畫後重新送審

[Answer]: Approve Plan（含補 has_managed_marker；FORMAT_VERSION 起始 1；登錄表用 .md）  <!-- 2026-08-30T07:49:35Z（讀自 date -u）· 人工核可 -->


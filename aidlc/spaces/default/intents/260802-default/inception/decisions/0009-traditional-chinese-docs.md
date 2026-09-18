# ADR 0009: 文件一律繁體中文（取代雙語，supersede ADR-0005）

- Status: Accepted
- Date: 2026-07-18
- Supersedes: ADR-0005（Bilingual Documentation）
- Related: `.aidlc-overrides/traditional-chinese-docs.md`

### Context

Cloud-360 原本依 ADR-0005 與 upstream 的 bilingual-docs extension，強制每份 aidlc-docs 文件同時含 `## 中文版` 與 `## English Version`，等於每份寫兩遍。專案主要讀者為繁體中文工作團隊，英文版價值有限，卻讓文件產出與維護成本加倍（兩邊要同步）。

### Decision

1. **AIDLC 文件一律繁體中文**，停用雙語強制；ADR-0005 由本 ADR supersede。
2. 以 override `.aidlc-overrides/traditional-chinese-docs.md` 落地（override 永遠勝出，升級 upstream 不受影響）。
3. `scripts/validate_repo_contract.py` 的檢查從「必須同時含中英文標題」改為「不得殘留 `## English Version` 標題」（line-anchored，內文提及不算），並移除相關雙語必要字。
4. 既有 38 份雙語文件一次性 retrofit 為純繁中（移除英文版分段），CLAUDE.md 與 gh-aw workflow 的雙語措辭一併對齊。
5. 範圍：Cloud-360。程式碼、識別字、專有名詞維持原文；upstream `.aidlc-rule-details/` 英文規則檔不受影響。

### Consequences

**正面**：文件產出量砍半；對繁中團隊更直覺；免除中英同步負擔。
**負面 / 風險**：非繁中讀者需自行翻譯；若未來要對外提供英文，需再評估（可屆時另開 ADR 恢復或補英文版）。

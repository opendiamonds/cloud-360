import React from 'react';

/**
 * LiveRegion — 共用的螢幕閱讀器播報區（`BR27.1`）
 *
 * **契約（`U23` 之後沿用本元件，請勿改簽章）**
 *
 * `[N4]`=A／`TS-U24-6`／`HO-U24-1`：本元件由 `U24` 自建並做成**可共用形狀**，
 * `U23` 屆時只需 `import`、不需接線。上游 `functional-design` 的
 * `frontend-components.md:41`／`:46`／`:53` 與 `rules.md` 的 `BR27.1` logic
 * 字面仍寫「由 `U23` 提供」——那是依 `[F3]`=A 寫的，而 `[F3]` 的排序理由是
 * **反的**（已核可的 Bolt 交錯順序裡 `U24` 在 B12、`U23` 在 B13，故 `U24` 先施工）。
 * 依 `refined-mockups:c3` 不回改已核可的上游，落差紀錄在
 * `nfr-design/logical-components.md` §一之一。
 *
 * **設計決定（`[ND1]`=A，皆不開放為 prop）**
 *
 * 1. **不持有任何狀態**：純 props 驅動。`message` 的「誰清」只能由呼叫端做
 *    （下一次播報或操作完成時覆寫為空字串），元件內不會有殘留。
 * 2. **`role="status"` 寫死**：`[ND1]`=C（開放 role prop）被排除——
 *    `role="alert"` 會**打斷**正在進行的朗讀，而上游沒有任何需求區分
 *    polite／assertive。寫死使「某個呼叫點不小心用了 assertive」不可能發生。
 * 3. **每頁各掛一個實例**，不走 context（`[ND1]`=B 被排除：那需要新增一組
 *    Context，而 `team.md` 的 lint 結構約束要求 Context 拆兩檔）。
 *
 * **已知殘留（`OPEN-ND24-1`，不美化）**：成員頁掛載時，文件中同時存在**兩個**
 * `role="status"` 區域——`Layout` 的橫幅宿主與本元件。`[ND1]`=A 的選項文字曾
 * 宣稱 A 能維持「只有一個」，那在 DOM 語意上是假的（頁面渲染於 `Layout` 的
 * `{children}` 之內），`[ND1]`=B 的數量**相同**。兩者同時變動時的播報順序
 * 未定義，落點 `U17 a11y-gate`。
 *
 * `sr-only` 的先例為 `EstimateAdvicePanel.tsx:278`（`<div className="sr-only"
 * aria-live="polite">`）。本元件改用 `role="status"`——它隱含 `aria-live="polite"`
 * 且另帶語意角色，而既有那處是唯一的 `aria-live` 命中、repo 內
 * `role="status"` 與 `role="alert"` 的命中數皆為 0。
 */
export interface LiveRegionProps {
  /** 要被朗讀的文字。空字串＝不播報（區域仍在 DOM 裡）。 */
  message: string;
  /**
   * 是否僅對螢幕閱讀器可見。預設 `true`——載入／錯誤文字的**視覺**呈現由
   * 頁面自己負責，本元件只管無障礙面，兩者不互相替代。
   */
  srOnly?: boolean;
}

export const LiveRegion: React.FC<LiveRegionProps> = ({ message, srOnly = true }) => (
  <div
    // role 寫死：見檔頭設計決定 2。
    role="status"
    data-testid="live-region"
    className={srOnly ? 'sr-only' : 'text-sm text-gray-600'}
  >
    {message}
  </div>
);

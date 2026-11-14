import { useEffect, type RefObject } from 'react';

/**
 * useDialogKeyboard — modal 對話框的鍵盤行為（合併前必修第 23 項 (c)）
 *
 * 宣告 `role="dialog" aria-modal="true"` 的對話框，鍵盤上必須真的是 modal：
 *   - **Escape 關閉**（`escapeDisabled` 為 true 時不關，例如送出中）；
 *   - **焦點圈限**：Tab／Shift+Tab 在對話框內可聚焦元素之間循環，不離開對話框。
 *     焦點若已在對話框之外（例如點了背景遮罩），下一次 Tab 把它收回對話框。
 *
 * 焦點**回到觸發按鈕**由呼叫端負責（呼叫端才持有觸發按鈕的 ref）。
 *
 * **形狀來源**：焦點圈限沿用 `components/brain/ObjectPicker.tsx` 的 `onKeyDown`
 * （取可聚焦元素、首尾互換）；監聽掛在 `window` 而非對話框節點則沿用
 * `components/ShareModal.tsx`／`components/cost/EstimateSaveModal.tsx`——
 * 使焦點落在對話框外時 Escape 與 Tab 仍會被處理。不新增依賴。
 */

const FOCUSABLE =
  'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])';

export interface DialogKeyboardOptions {
  /** 對話框是否開啟。false 時不掛任何監聽（對話框以條件渲染存在於同一元件時需要）。 */
  open: boolean;
  /** Escape 的處置，通常就是關閉對話框的那個函式。 */
  onEscape: () => void;
  /** true 時 Escape 不關閉（例如送出中，與停用的「取消」鈕一致）。焦點圈限照常。 */
  escapeDisabled?: boolean;
}

export function useDialogKeyboard(
  dialogRef: RefObject<HTMLElement | null>,
  { open, onEscape, escapeDisabled = false }: DialogKeyboardOptions,
): void {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (escapeDisabled) return;
        event.preventDefault();
        onEscape();
        return;
      }
      if (event.key !== 'Tab') return;
      const root = dialogRef.current;
      if (!root) return;
      const items = Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (items.length === 0) {
        // 沒有可聚焦元素時仍不得讓焦點離開對話框。
        event.preventDefault();
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      const activeEl = document.activeElement;
      const outside = !root.contains(activeEl);
      if (event.shiftKey && (activeEl === first || outside)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (activeEl === last || outside)) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [dialogRef, open, onEscape, escapeDisabled]);
}

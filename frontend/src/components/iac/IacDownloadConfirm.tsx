import { useEffect, useRef, type RefObject } from 'react';

type Props = {
  highCount: number;
  criticalCount: number;
  onConfirm: () => void;
  onCancel: () => void;
  returnFocusRef: RefObject<HTMLButtonElement | null>;
};

export function IacDownloadConfirm({
  highCount,
  criticalCount,
  onConfirm,
  onCancel,
  returnFocusRef,
}: Props) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    const previous = returnFocusRef.current;
    dialog?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        onCancel();
        return;
      }
      if (event.key !== 'Tab' || !dialog) return;
      const focusable = [
        ...dialog.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        ),
      ];
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      previous?.focus();
    };
  }, [onCancel, returnFocusRef]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="iac-download-confirm-title"
        tabIndex={-1}
        data-testid="iac-download-confirm"
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl outline-none"
      >
        <h2 id="iac-download-confirm-title" className="text-lg font-bold text-gray-900">
          下載前確認
        </h2>
        <p className="mt-3 text-sm text-gray-700">
          這份掃描報告含 HIGH {highCount} 筆、CRITICAL {criticalCount} 筆。確認後才會下載。
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-xl bg-gray-100 px-4 py-2 text-sm font-bold text-gray-700 hover:bg-gray-200"
          >
            取消
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700"
          >
            確認下載
          </button>
        </div>
      </div>
    </div>
  );
}

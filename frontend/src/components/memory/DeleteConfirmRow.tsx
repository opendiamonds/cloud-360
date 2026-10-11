import React, { useEffect, useRef } from 'react';

/**
 * DeleteConfirmRow — 記憶的就地確認列（`BR34.1`／`BR34.2`）
 *
 * **不使用 `window.confirm`**：它是瀏覽器 modal，阻塞事件迴圈且無法套用無障礙規格。
 *
 * - 掛載時焦點移到「刪除」（鍵盤使用者不必額外 Tab 才找得到確認鍵）。
 * - Escape 或「取消」→ `onCancel`；焦點還給原本的刪除入口由**呼叫端**負責
 *   （本元件卸載後就沒有東西可以接焦點了）。
 * - 文案必須說明兩件事：大腦不再依據它回答、此刪除會被記錄（`NFR7.91`，
 *   ADR-0006 audit logging 面：刪除不得以使用者察覺不到的方式發生）。
 */
export interface DeleteConfirmRowProps {
  /** 被刪除那則的 `memory_id`，用於組 test id。 */
  memoryId: string;
  /** 內容摘要，放進確認鍵的 `aria-label`。 */
  summary: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export const DeleteConfirmRow: React.FC<DeleteConfirmRowProps> = ({
  memoryId,
  summary,
  onConfirm,
  onCancel,
}) => {
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    confirmRef.current?.focus();
  }, []);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      onCancel();
    }
  };

  return (
    <div
      role="group"
      aria-label="確認刪除"
      onKeyDown={handleKeyDown}
      className="mt-2 flex flex-wrap items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2"
    >
      <span className="text-sm text-red-800">
        確定刪除？刪除後大腦將不再依據它回答，此刪除會被記錄。
      </span>
      <button
        ref={confirmRef}
        type="button"
        data-testid={`memory-item-${memoryId}-delete-confirm`}
        aria-label={`確認刪除：${summary}`}
        onClick={onConfirm}
        className="rounded-md bg-red-600 px-3 py-1 text-sm font-bold text-white hover:bg-red-700"
      >
        刪除
      </button>
      <button
        type="button"
        data-testid={`memory-item-${memoryId}-delete-cancel`}
        onClick={onCancel}
        className="rounded-md border border-gray-300 bg-white px-3 py-1 text-sm font-bold text-gray-700 hover:bg-gray-50"
      >
        取消
      </button>
    </div>
  );
};

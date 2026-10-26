import React, { useEffect, useRef, useState } from 'react';
import type { MemoryView } from '../../memory/memoryApi';
import { OTHERS_MEMORY_MARKER, scopeLabel } from '../../memory/memoryLabels';
import { DeleteConfirmRow } from './DeleteConfirmRow';

/**
 * MemoryItem — 記憶頁的一則記憶（`W2`／`W4`，`functional-spec.md §六之二` 的狀態機）
 *
 * 狀態：`idle → confirming → deleting → (removed | failed)`；`failed` 可再點刪除回到
 * `confirming`。**只有擁有者的列有這個狀態機**——非擁有者的列沒有刪除入口
 * （`BR35.2`），是純顯示的條目。
 *
 * **輸出編碼**：`content` 是不可信文字，一律以 React 文字節點渲染；本檔不使用
 * React 的原始 HTML 注入 API，也不把 `content` 放進 `href`／`src`（`security-design.md §三`）。
 */

/** 內容摘要的長度上限（`aria-label`「刪除：<前 30 字>」）。 */
const SUMMARY_LENGTH = 30;

function summarize(content: string): string {
  const flat = content.replace(/\s+/g, ' ').trim();
  return flat.length > SUMMARY_LENGTH ? `${flat.slice(0, SUMMARY_LENGTH)}…` : flat;
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('zh-TW');
}

type ItemState = 'idle' | 'confirming' | 'deleting' | 'failed';

export interface MemoryItemProps {
  record: MemoryView;
  /** 是否顯示日期與保存期限列（情節記憶）。 */
  showDates: boolean;
  /** 擁有者是不是自己（`BR35.1` 的「你」）。由 `MemoryZone` 判定，本元件不讀 `useAuth()`。 */
  isOwn: boolean;
  /**
   * 是否渲染刪除入口（`BR35.2`）。**UI 判定，非授權**：伺服器仍以 404 拒絕
   * 非擁有者（`SEC-U15-2`）；移除這個判定只會多出一個必然失敗的按鈕。
   */
  canDelete: boolean;
  /**
   * 發出 `DELETE`。回 `'deleted'`（204）或 `'already-gone'`（404 **且**重讀清單已不含
   * 該則，由 `MemoryZone` 確認），其餘——含 404 後重讀仍列出該則或重讀失敗——拋例外。
   */
  deleteRecord: (memoryId: string) => Promise<'deleted' | 'already-gone'>;
  /** 204，或經重讀確認的 404 之後，由區塊就地移除本則（`BR34.4`／`BR34.5`）。 */
  onRemoved: (memoryId: string, summary: string) => void;
  announce: (message: string) => void;
}

export const MemoryItem: React.FC<MemoryItemProps> = ({
  record,
  showDates,
  isOwn,
  canDelete,
  deleteRecord,
  onRemoved,
  announce,
}) => {
  const [itemState, setItemState] = useState<ItemState>('idle');
  const [errorText, setErrorText] = useState('');
  const entryRef = useRef<HTMLButtonElement>(null);
  // 取消確認後要把焦點還給刪除入口；入口在確認列收起後才重新出現，故在 effect 裡做。
  const restoreFocusToEntry = useRef(false);

  useEffect(() => {
    if (restoreFocusToEntry.current && (itemState === 'idle' || itemState === 'failed')) {
      restoreFocusToEntry.current = false;
      entryRef.current?.focus();
    }
  }, [itemState]);

  const id = record.memory_id;
  const summary = summarize(record.content);

  const handleCancel = () => {
    restoreFocusToEntry.current = true;
    setItemState('idle');
  };

  const handleConfirm = () => {
    setItemState('deleting');
    setErrorText('');
    deleteRecord(id)
      .then(() => {
        // 204 與「經重讀確認」的 404 同一條路徑：移除並播報（`BR34.5`）。焦點由區塊移到區標題。
        onRemoved(id, summary);
      })
      .catch((err) => {
        const message = err instanceof Error && err.message ? err.message : '刪除失敗';
        restoreFocusToEntry.current = true;
        setItemState('failed');
        setErrorText(`刪除失敗：${message}`);
        announce(`刪除失敗：${summary}`);
      });
  };

  const isDeleting = itemState === 'deleting';

  return (
    <li
      data-testid={`memory-item-${id}`}
      aria-disabled={isDeleting || undefined}
      className={`rounded-lg border border-gray-200 bg-white px-4 py-3 ${isDeleting ? 'opacity-50' : ''}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {showDates && (
            <div className="text-xs font-bold text-gray-500">{formatDate(record.created_at)}</div>
          )}
          <p className="whitespace-pre-wrap break-words text-sm text-gray-900">{record.content}</p>
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
            <span data-testid={`memory-item-${id}-owner`} data-owner-user-id={record.owner_user_id}>
              擁有者：{isOwn ? '你' : '其他使用者'}
            </span>
            <span data-testid={`memory-item-${id}-scope`}>
              可見範圍：{scopeLabel(record.visibility_scope)}
            </span>
            {showDates && record.expires_at && (
              <span>保存至 {formatDate(record.expires_at)}</span>
            )}
          </div>
        </div>
        <div className="shrink-0">
          {canDelete ? (
            itemState !== 'confirming' && (
              <button
                ref={entryRef}
                type="button"
                data-testid={`memory-item-${id}-delete`}
                aria-label={`刪除：${summary}`}
                disabled={isDeleting}
                onClick={() => setItemState('confirming')}
                className="rounded-md border border-gray-300 bg-white px-3 py-1 text-sm font-bold text-gray-700 hover:border-red-300 hover:text-red-600 disabled:cursor-not-allowed"
              >
                刪除
              </button>
            )
          ) : (
            <span className="rounded-md bg-gray-100 px-2 py-1 text-xs font-bold text-gray-600">
              {OTHERS_MEMORY_MARKER}
            </span>
          )}
        </div>
      </div>
      {canDelete && itemState === 'confirming' && (
        <DeleteConfirmRow
          memoryId={id}
          summary={summary}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
        />
      )}
      {itemState === 'failed' && errorText && (
        <p className="mt-2 text-sm text-red-600">
          {errorText}
        </p>
      )}
    </li>
  );
};

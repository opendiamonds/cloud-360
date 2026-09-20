import { useEffect, useState } from 'react';
import type { EstimateSetSummary } from './types';
import { cloudLabel } from './types';

type Props = {
  open: boolean;
  onClose: () => void;
  items: EstimateSetSummary[];
  canEdit: boolean;
  onSelect: (id: number) => void;
  onDelete: (id: number) => Promise<void>;
};

export function EstimateHistoryDrawer({
  open,
  onClose,
  items,
  canEdit,
  onSelect,
  onDelete,
}: Props) {
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) setDeletingId(null);
  }, [open]);

  if (!open) return null;

  const handleDelete = async (it: EstimateSetSummary) => {
    const title = it.note?.trim() || `未命名 #${it.id}`;
    if (
      !window.confirm(
        `確定刪除「${title}」？\n明細、分享與 AI 建議會一併刪除，且無法復原。`,
      )
    ) {
      return;
    }
    setDeletingId(it.id);
    try {
      await onDelete(it.id);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-[9990] flex justify-end bg-black/30" role="presentation">
      <aside
        data-testid="estimate-history-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="歷史上傳"
        className="h-full w-full max-w-md bg-white shadow-xl"
      >
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
          <h2 className="text-lg font-bold text-gray-900">歷史上傳</h2>
          <button
            type="button"
            className="rounded-lg px-2 py-1 text-gray-500 hover:bg-gray-100"
            onClick={onClose}
          >
            ✕
          </button>
        </div>
        <ul className="max-h-[calc(100%-3.5rem)] overflow-y-auto p-3 space-y-2">
          {items.length === 0 ? (
            <li className="text-sm text-gray-500 py-8 text-center">尚無歷史</li>
          ) : (
            items.map((it) => (
              <li key={it.id}>
                <div className="flex items-stretch gap-2 rounded-xl border border-gray-100 hover:border-brand-200 hover:bg-brand-50">
                  <button
                    type="button"
                    className="min-w-0 flex-1 px-3 py-2 text-left"
                    onClick={() => {
                      onSelect(it.id);
                      onClose();
                    }}
                  >
                    <div className="text-sm font-semibold text-gray-900 truncate">
                      {it.note?.trim() || `未命名 #${it.id}`}
                      {!it.is_owner && (
                        <span className="ml-2 text-[10px] font-medium text-gray-400">
                          他人分享
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500">
                      {it.created_at ? new Date(it.created_at).toLocaleString() : ''}
                      {' · '}
                      {it.clouds.map((c) => cloudLabel(c.cloud)).join(' · ') || '無雲別'}
                    </div>
                  </button>
                  {it.is_owner && canEdit && (
                    <button
                      type="button"
                      data-testid={`estimate-history-delete-${it.id}`}
                      className="shrink-0 self-center mr-2 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
                      disabled={deletingId === it.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleDelete(it);
                      }}
                    >
                      {deletingId === it.id ? '刪除中…' : '刪除'}
                    </button>
                  )}
                </div>
              </li>
            ))
          )}
        </ul>
      </aside>
    </div>
  );
}

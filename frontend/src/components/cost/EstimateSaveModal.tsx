import { useEffect, useRef, useState } from 'react';
import { apiUrl } from '../../config/api';
import { authHeaders } from './types';

type Props = {
  isOpen: boolean;
  onClose: () => void;
  estimateSetId: number | null;
  initialName?: string | null;
  onSaved: (detail: unknown) => void;
};

export function EstimateSaveModal({
  isOpen,
  onClose,
  estimateSetId,
  initialName,
  onSaved,
}: Props) {
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    setName((initialName || '').trim());
    setError('');
    const t = window.setTimeout(() => inputRef.current?.focus(), 0);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.clearTimeout(t);
      window.removeEventListener('keydown', onKey);
    };
  }, [isOpen, initialName, onClose]);

  if (!isOpen) return null;

  const save = async () => {
    if (!estimateSetId) return;
    const cleaned = name.trim();
    if (!cleaned) {
      setError('請輸入名稱');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const res = await fetch(apiUrl(`/api/cost/v1/sets/${estimateSetId}`), {
        method: 'PATCH',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: cleaned }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(typeof data.detail === 'string' ? data.detail : '儲存失敗');
        return;
      }
      onSaved(data);
      onClose();
    } catch {
      setError('儲存失敗');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="estimate-save-title"
        data-testid="estimate-save-modal"
        className="w-full max-w-md rounded-2xl bg-white shadow-xl"
      >
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
          <h2 id="estimate-save-title" className="text-lg font-bold text-gray-900">
            儲存到歷史
          </h2>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-700">
            ✕
          </button>
        </div>
        <div className="space-y-3 p-5">
          <label className="block text-sm font-medium text-gray-700" htmlFor="estimate-save-name">
            名稱
          </label>
          <input
            ref={inputRef}
            id="estimate-save-name"
            data-testid="estimate-save-name"
            type="text"
            maxLength={200}
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                void save();
              }
            }}
            placeholder="例如：電商上線估價 2026-09"
            className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-900"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
        <div className="flex justify-end gap-2 border-t border-gray-100 px-5 py-4">
          <button
            type="button"
            className="rounded-xl px-4 py-2 text-sm font-bold text-gray-600"
            onClick={onClose}
          >
            取消
          </button>
          <button
            type="button"
            data-testid="estimate-save-confirm"
            disabled={busy}
            className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
            onClick={() => void save()}
          >
            {busy ? '儲存中…' : '確認儲存'}
          </button>
        </div>
      </div>
    </div>
  );
}

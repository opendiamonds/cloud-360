import { useEffect, useRef, useState } from 'react';
import { apiUrl } from '../../config/api';
import { authHeaders } from './types';

type UserRow = { id: number; username: string; role: string };

type Props = {
  isOpen: boolean;
  onClose: () => void;
  estimateSetId: number | null;
  onSaved?: () => void;
};

export function EstimateShareModal({
  isOpen,
  onClose,
  estimateSetId,
  onSaved,
}: Props) {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen || !estimateSetId) return;
    setError('');
    const load = async () => {
      try {
        const [usersRes, sharesRes] = await Promise.all([
          fetch(apiUrl('/api/cost/v1/share-users'), { headers: authHeaders() }),
          fetch(apiUrl(`/api/cost/v1/sets/${estimateSetId}/shares`), {
            headers: authHeaders(),
          }),
        ]);
        const usersData = await usersRes.json().catch(() => []);
        if (!usersRes.ok) {
          setError(
            typeof usersData.detail === 'string'
              ? usersData.detail
              : '載入分享名單失敗'
          );
          setUsers([]);
        } else {
          setUsers(Array.isArray(usersData) ? usersData : []);
        }
        if (sharesRes.ok) {
          const sharesData = await sharesRes.json();
          const ids = (sharesData.shares || []).map(
            (s: { user_id: number }) => s.user_id
          );
          setSelected(ids);
        }
      } catch {
        setError('載入分享名單失敗');
      }
    };
    void load();
  }, [isOpen, estimateSetId]);

  useEffect(() => {
    if (!isOpen) return;
    panelRef.current?.querySelector<HTMLElement>('button,input')?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const save = async () => {
    if (!estimateSetId) return;
    setBusy(true);
    setError('');
    try {
      const res = await fetch(apiUrl(`/api/cost/v1/sets/${estimateSetId}/shares`), {
        method: 'PUT',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_ids: selected }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(typeof data.detail === 'string' ? data.detail : '分享失敗');
        return;
      }
      onSaved?.();
      onClose();
    } catch {
      setError('分享失敗');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40">
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="estimate-share-title"
        data-testid="estimate-share-modal"
        className="w-full max-w-md rounded-2xl bg-white shadow-xl"
      >
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
          <h2 id="estimate-share-title" className="text-lg font-bold text-gray-900">
            分享估價表
          </h2>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-700">
            ✕
          </button>
        </div>
        <div className="max-h-[50vh] overflow-y-auto p-5 space-y-2">
          {users.length === 0 && !error && (
            <p className="text-sm text-gray-500">目前沒有可分享的使用者</p>
          )}
          {users.map((u) => (
            <label
              key={u.id}
              className="flex cursor-pointer items-center gap-3 rounded-xl border border-gray-100 p-3 hover:bg-brand-50"
            >
              <input
                type="checkbox"
                checked={selected.includes(u.id)}
                onChange={() =>
                  setSelected((prev) =>
                    prev.includes(u.id) ? prev.filter((x) => x !== u.id) : [...prev, u.id]
                  )
                }
              />
              <span className="text-sm font-semibold text-gray-800">{u.username}</span>
              <span className="text-xs text-gray-500">{u.role}</span>
            </label>
          ))}
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
        <div className="flex justify-end gap-2 border-t border-gray-100 px-5 py-4">
          <button type="button" className="rounded-xl px-4 py-2 text-sm font-bold text-gray-600" onClick={onClose}>
            取消
          </button>
          <button
            type="button"
            data-testid="estimate-share-save"
            disabled={busy}
            className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
            onClick={save}
          >
            {busy ? '儲存中…' : '確認分享'}
          </button>
        </div>
      </div>
    </div>
  );
}

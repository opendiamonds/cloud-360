import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/auth-context';
import { apiUrl } from '../config/api';

interface AuthRequestRow {
  id: number;
  user_id: number;
  username: string;
  requested_role: string;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export const AuthorizationRequestsPage: React.FC = () => {
  const { token, can, user } = useAuth();
  const canEdit = can('J3a', 'edit');
  const isPlatformAdmin = user?.role === 'Platform_Admin';
  const [statusFilter, setStatusFilter] = useState('pending');
  const [rows, setRows] = useState<AuthRequestRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const restricted = new Set(['Platform_Admin', 'Platform_Owner']);

  // 純抓取，完全不碰 state。react-hooks/set-state-in-effect 會做過程間分析：
  // 只要 effect 同步呼叫的函式內部有 setState 就會被擋，因此 state 更新一律留在
  // 呼叫端的 .then／.catch／.finally callback 內（規則允許的形式）。
  const fetchRequests = useCallback(async () => {
    const res = await fetch(
      apiUrl(`/api/auth/authorization-requests?status=${statusFilter}`),
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '載入失敗');
    return data;
  }, [token, statusFilter]);

  // 使用者主動觸發的重載（核准／拒絕後）：先切回 loading 再抓。
  const fetchRows = useCallback(() => {
    setLoading(true);
    setError(null);
    return fetchRequests()
      .then(setRows)
      .catch((err) => setError(err instanceof Error ? err.message : '載入失敗'))
      .finally(() => setLoading(false));
  }, [fetchRequests]);

  useEffect(() => {
    if (!token) return;
    // 初次載入時 loading 已是 true，不需要再設一次。
    let cancelled = false;
    fetchRequests()
      .then((data) => { if (!cancelled) setRows(data); })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : '載入失敗'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [token, fetchRequests]);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  };

  const canDecide = (requestedRole: string) => {
    if (!canEdit) return false;
    if (isPlatformAdmin) return true;
    return !restricted.has(requestedRole);
  };

  const handleApprove = async (id: number) => {
    if (!confirm('確定核准此授權申請？')) return;
    try {
      const res = await fetch(apiUrl(`/api/auth/authorization-requests/${id}/approve`), {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '核准失敗');
      showToast(`✔ 已核准 ${data.username} → ${data.role}`);
      fetchRows();
    } catch (err) {
      showToast(err instanceof Error ? err.message : '核准失敗');
    }
  };

  const handleReject = async (id: number) => {
    if (!confirm('拒絕後將刪除該使用者帳號，確定？')) return;
    try {
      const res = await fetch(apiUrl(`/api/auth/authorization-requests/${id}/reject`), {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '拒絕失敗');
      showToast(`✔ 已拒絕並刪除 ${data.deleted_username}`);
      fetchRows();
    } catch (err) {
      showToast(err instanceof Error ? err.message : '拒絕失敗');
    }
  };

  return (
    <div className="relative min-h-full bg-slate-950 p-6 md:p-10 text-white w-full">
      {toast && (
        <div className="fixed top-6 left-1/2 -translate-x-1/2 z-50 px-6 py-3 rounded-2xl bg-slate-800 border border-white/10 text-sm">
          {toast}
        </div>
      )}

      <div className="flex flex-col gap-2 mb-6">
        <h1 className="text-3xl font-black tracking-tight">授權申請</h1>
        <p className="text-slate-400 text-sm">
          檢視並處理新註冊使用者的角色授權申請（J5）。{' '}
          <Link to="/admin/users" className="text-blue-400 hover:underline">
            返回使用者設定
          </Link>
        </p>
      </div>

      <div className="flex gap-2 mb-4">
        {(['pending', 'approved', 'rejected'] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatusFilter(s)}
            className={`px-4 py-2 rounded-xl text-xs font-bold border ${
              statusFilter === s
                ? 'bg-blue-600 border-blue-500 text-white'
                : 'bg-slate-900 border-slate-700 text-slate-400'
            }`}
          >
            {s === 'pending' ? '待處理' : s === 'approved' ? '已核准' : '已拒絕'}
          </button>
        ))}
      </div>

      <div className="bg-white/5 border border-white/10 rounded-[2rem] overflow-hidden">
        {loading ? (
          <div className="p-16 text-center text-slate-400 text-sm">載入中…</div>
        ) : error ? (
          <div className="p-16 text-center text-red-300 text-sm">{error}</div>
        ) : rows.length === 0 ? (
          <div className="p-16 text-center text-slate-400 text-sm">目前沒有此狀態的授權申請</div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 text-xs text-slate-400 uppercase">
                <th className="px-6 py-4">申請人</th>
                <th className="px-6 py-4">申請角色</th>
                <th className="px-6 py-4">時間</th>
                <th className="px-6 py-4">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {rows.map((row) => (
                <tr key={row.id}>
                  <td className="px-6 py-4 font-bold">{row.username}</td>
                  <td className="px-6 py-4 text-blue-300">{row.requested_role}</td>
                  <td className="px-6 py-4 text-slate-400 text-xs">
                    {row.created_at ? new Date(row.created_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-6 py-4">
                    {row.status === 'pending' && canEdit ? (
                      <div className="flex gap-2">
                        <button
                          type="button"
                          disabled={!canDecide(row.requested_role)}
                          title={
                            !canDecide(row.requested_role)
                              ? '僅 Platform_Admin 可核准此角色'
                              : undefined
                          }
                          onClick={() => handleApprove(row.id)}
                          className="px-3 py-1.5 rounded-lg bg-emerald-600 text-xs font-bold disabled:opacity-40"
                        >
                          核准
                        </button>
                        <button
                          type="button"
                          disabled={!canDecide(row.requested_role)}
                          onClick={() => handleReject(row.id)}
                          className="px-3 py-1.5 rounded-lg bg-red-600/80 text-xs font-bold disabled:opacity-40"
                        >
                          拒絕
                        </button>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-500">{row.status}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

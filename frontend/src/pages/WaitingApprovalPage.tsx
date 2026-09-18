import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/auth-context';
import { apiUrl } from '../config/api';

interface CatalogRole {
  role: string;
  display_name: string;
  features: string[];
}

export const WaitingApprovalPage: React.FC = () => {
  const { user, token, logout, refreshMe, isPending, isLoading } = useAuth();
  const navigate = useNavigate();
  const [catalog, setCatalog] = useState<CatalogRole[]>([]);
  // 使用者是否手動改過下拉；未改過時直接沿用伺服器上的申請角色（derive，
  // 不用 effect 同步 state — 送出後 refreshMe() 會讓兩者一致）。
  const [roleOverride, setRoleOverride] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isLoading && !isPending) {
      navigate('/', { replace: true });
    }
  }, [isLoading, isPending, navigate]);

  useEffect(() => {
    fetch(apiUrl('/api/auth/roles/catalog'))
      .then((r) => r.json())
      .then((d) => setCatalog(d.roles || []))
      .catch(() => setCatalog([]));
  }, []);

  const selectedRole = roleOverride ?? user?.pending_request?.requested_role ?? '';

  const handleChangeRole = async () => {
    if (!selectedRole || !token) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(apiUrl('/api/auth/me/authorization-request'), {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ requested_role: selectedRole }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '更新失敗');
      await refreshMe();
      setMessage(`✔ 已更新申請角色為 ${data.requested_role}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新失敗');
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (isLoading) return null;

  return (
    <div className="min-h-screen w-screen flex items-center justify-center bg-slate-900 text-white p-6">
      <div className="w-full max-w-lg bg-white/5 border border-white/10 rounded-3xl p-8 flex flex-col gap-5">
        <h1 className="text-2xl font-bold">等待管理員授權</h1>
        <p className="text-slate-300 text-sm leading-relaxed">
          您好，{user?.username}。您的帳號已建立，但尚未指派正式角色。管理員核准後即可使用平台功能。
        </p>
        <div className="rounded-2xl bg-slate-800/60 border border-slate-700 p-4 text-sm">
          <div className="text-slate-400 text-xs mb-1">目前申請角色</div>
          <div className="font-bold text-blue-300">
            {user?.pending_request?.requested_role || '（尚未載入）'}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-xs font-bold text-slate-400 uppercase">更改申請角色</label>
          <select
            value={selectedRole}
            onChange={(e) => setRoleOverride(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm"
          >
            {catalog.map((r) => (
              <option key={r.role} value={r.role}>
                {r.display_name}（{r.role}）
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={saving || !selectedRole}
            onClick={handleChangeRole}
            className="py-3 rounded-xl bg-blue-600 font-bold text-sm disabled:opacity-50"
          >
            {saving ? '更新中…' : '更新申請'}
          </button>
        </div>

        {message && <p className="text-emerald-300 text-sm">{message}</p>}
        {error && <p className="text-red-300 text-sm">{error}</p>}

        <button
          type="button"
          onClick={handleLogout}
          className="mt-2 py-3 rounded-xl border border-slate-600 text-slate-300 text-sm font-bold hover:bg-slate-800"
        >
          登出
        </button>
      </div>
    </div>
  );
};

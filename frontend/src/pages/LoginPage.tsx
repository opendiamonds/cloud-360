import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/auth-context';
import { apiUrl } from '../config/api';

interface CatalogRole {
  role: string;
  display_name: string;
  features: string[];
}

const SHOW_DEMO_QUICK_USERS =
  import.meta.env.DEV || import.meta.env.VITE_ENABLE_DEMO_QUICK_USERS === 'true';

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [requestedRole, setRequestedRole] = useState('');
  const [catalog, setCatalog] = useState<CatalogRole[]>([]);
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showHelper, setShowHelper] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isRegisterMode) return;
    fetch(apiUrl('/api/auth/roles/catalog'))
      .then((r) => r.json())
      .then((d) => {
        const roles: CatalogRole[] = d.roles || [];
        setCatalog(roles);
        if (roles.length && !requestedRole) setRequestedRole(roles[0].role);
      })
      .catch(() => setCatalog([]));
  }, [isRegisterMode, requestedRole]);

  const handleToggleMode = () => {
    setIsRegisterMode(!isRegisterMode);
    setError(null);
    setPassword('');
    setConfirmPassword('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!username.trim() || !password.trim()) {
      setError('請輸入帳號與密碼');
      return;
    }

    if (isRegisterMode) {
      if (!confirmPassword.trim()) {
        setError('請再次輸入密碼以進行確認');
        return;
      }
      if (password !== confirmPassword) {
        setError('兩次輸入的密碼不一致');
        return;
      }
      if (password.length < 6) {
        setError('密碼長度至少需要 6 個字元');
        return;
      }
      if (!requestedRole) {
        setError('請選擇欲申請的角色');
        return;
      }
    }

    setError(null);
    setIsSubmitting(true);

    const endpoint = isRegisterMode ? 'register' : 'login';
    const body = isRegisterMode
      ? { username, password, requested_role: requestedRole }
      : { username, password };

    try {
      const response = await fetch(apiUrl(`/api/auth/${endpoint}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : isRegisterMode
              ? '註冊失敗'
              : '登入失敗'
        );
      }

      await login(data.username, data.access_token, data.role ?? null);

      if (data.authorization_status === 'pending') {
        navigate('/waiting-approval');
      } else {
        navigate('/');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '連線失敗，請檢查後端是否啟動');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSelectQuickUser = (user: string, pw: string) => {
    setUsername(user);
    setPassword(pw);
    setError(null);
  };

  const selectedCatalog = catalog.find((c) => c.role === requestedRole);

  return (
    <div className="relative min-h-screen w-screen flex items-center justify-center bg-slate-900 overflow-hidden font-sans">
      <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] bg-blue-600/30 rounded-full blur-[120px] animate-pulse duration-[8000ms]"></div>
      <div className="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] bg-purple-600/20 rounded-full blur-[100px] animate-pulse duration-[6000ms]"></div>

      <div className="relative w-full max-w-md mx-4 p-8 md:p-10 bg-white/5 backdrop-blur-2xl border border-white/10 rounded-[2.5rem] shadow-[0_30px_100px_rgba(0,0,0,0.5)] z-10 flex flex-col gap-6 transition-all duration-300 max-h-[95vh] overflow-y-auto">
        <div className="text-center">
          <div className="inline-flex p-3 bg-blue-500/10 text-blue-400 rounded-2xl mb-4 border border-blue-500/20">
            <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">
            {isRegisterMode ? '建立新帳號' : 'Cloud-360'}
          </h2>
          <p className="text-sm text-slate-400 mt-2 font-medium">
            {isRegisterMode ? '選擇角色並送出授權申請' : '多雲架構設計與智慧維運平台'}
          </p>
        </div>

        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center gap-3 text-red-300 text-sm">
            <span className="font-semibold">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-slate-300 tracking-wider uppercase ml-1">帳號</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="請輸入您的帳號"
              className="w-full px-5 py-4 bg-slate-800/50 border border-slate-700 text-white rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 font-medium placeholder-slate-500"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-slate-300 tracking-wider uppercase ml-1">密碼</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="請輸入密碼"
              className="w-full px-5 py-4 bg-slate-800/50 border border-slate-700 text-white rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 font-medium placeholder-slate-500"
            />
          </div>

          {isRegisterMode && (
            <>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-300 tracking-wider uppercase ml-1">確認密碼</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="請再次輸入密碼"
                  className="w-full px-5 py-4 bg-slate-800/50 border border-slate-700 text-white rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 font-medium placeholder-slate-500"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-300 tracking-wider uppercase ml-1">
                  申請角色
                </label>
                <select
                  value={requestedRole}
                  onChange={(e) => setRequestedRole(e.target.value)}
                  className="w-full px-5 py-4 bg-slate-800/50 border border-slate-700 text-white rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                >
                  {catalog.map((r) => (
                    <option key={r.role} value={r.role}>
                      {r.display_name}（{r.role}）
                    </option>
                  ))}
                </select>
                {selectedCatalog && (
                  <div className="mt-2 p-3 rounded-xl bg-slate-800/40 border border-slate-700 text-xs text-slate-300">
                    <div className="font-bold text-slate-200 mb-1">可使用功能摘要</div>
                    {selectedCatalog.features.length ? (
                      <ul className="list-disc pl-4 space-y-0.5 max-h-36 overflow-y-auto overscroll-contain pr-1">
                        {selectedCatalog.features.map((f) => (
                          <li key={f}>{f}</li>
                        ))}
                      </ul>
                    ) : (
                      <span>此角色目前無預設功能旗標</span>
                    )}
                  </div>
                )}
              </div>
            </>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold rounded-2xl shadow-lg active:scale-[0.98] transition-all flex items-center justify-center disabled:opacity-50 mt-2"
          >
            {isSubmitting ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : isRegisterMode ? (
              '送出註冊申請'
            ) : (
              '登入系統'
            )}
          </button>
        </form>

        <div className="flex flex-col gap-4 border-t border-white/5 pt-4 text-center">
          <button
            onClick={handleToggleMode}
            className="text-xs text-slate-400 hover:text-white transition-colors cursor-pointer font-bold"
          >
            {isRegisterMode ? '已有帳號？立即登入系統' : '沒有帳號？立即註冊新帳號'}
          </button>

          {!isRegisterMode && SHOW_DEMO_QUICK_USERS && (
            <>
              <button
                onClick={() => setShowHelper(!showHelper)}
                className="text-[11px] text-blue-400 hover:text-blue-300 font-bold transition-colors cursor-pointer"
              >
                {showHelper ? '隱藏測試帳號資訊 ▲' : '顯示 Persona 測試帳號資訊 ▼'}
              </button>

              {showHelper && (
                <div className="p-4 bg-slate-800/40 rounded-2xl border border-white/5 text-left flex flex-col gap-2.5 max-h-48 overflow-y-auto">
                  <span className="text-xs text-slate-400 font-bold">點擊下方帳號可快速輸入：</span>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => handleSelectQuickUser('admin', 'admin123')}
                      className="px-3 py-2 bg-slate-800 text-slate-300 text-[11px] font-semibold rounded-lg hover:bg-slate-700"
                    >
                      admin（平台管理員）
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSelectQuickUser('catherine', 'catherine123')}
                      className="px-3 py-2 bg-slate-800 text-slate-300 text-[11px] font-semibold rounded-lg hover:bg-slate-700"
                    >
                      Catherine（管理員）
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSelectQuickUser('alex', 'alex123')}
                      className="px-3 py-2 bg-slate-800 text-slate-300 text-[11px] font-semibold rounded-lg hover:bg-slate-700"
                    >
                      Alex（架構師）
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSelectQuickUser('ian', 'ian123')}
                      className="px-3 py-2 bg-slate-800 text-slate-300 text-[11px] font-semibold rounded-lg hover:bg-slate-700"
                    >
                      Ian（開發者）
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

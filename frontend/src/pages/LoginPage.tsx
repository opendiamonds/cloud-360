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

const CATALOG_ERROR_HEADLINE = '無法取得可申請的角色清單';
const CATALOG_ERROR_FALLBACK = '未知錯誤';

// 純抓取，完全不碰 state：react-hooks/set-state-in-effect 會做過程間分析，只要
// effect 同步呼叫的函式裡有 setState 就會被擋，因此 state 更新一律留在呼叫端的
// .then／.catch 內（與 AdminPage 的 fetchUserPage 同一個形狀）。
async function fetchRoleCatalog(): Promise<CatalogRole[]> {
  // 先判 res.ok 再解析 body：這條路徑最常見的失敗是反向代理或後端回非 JSON
  // （例如 502 的 HTML），先解析會把有診斷價值的狀態碼換成一個語意不明的
  // parse 錯誤。跨來源被擋的情況連 Response 都拿不到，fetch 本身就丟 TypeError。
  const res = await fetch(apiUrl('/api/auth/roles/catalog'));
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const data = await res.json();
  return (data?.roles ?? []) as CatalogRole[];
}

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [requestedRole, setRequestedRole] = useState('');
  const [catalog, setCatalog] = useState<CatalogRole[]>([]);
  // 角色目錄抓取失敗的原因。`null` 代表「沒有失敗」，不代表「已載入」——
  // 兩者靠 catalog.length 區分，見下方的三態渲染。
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showHelper, setShowHelper] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  // 進入註冊模式時抓一次角色目錄。
  //
  // deps 刻意**不含** requestedRole：把它放進 deps 會讓使用者每選一次角色就重抓
  // 一次目錄。預設值改以 updater 形式讀舊值，effect 因此完全不需要依賴它。
  //
  // 失敗**必須看得到**。原本這裡是 `.catch(() => setCatalog([]))`：所有失敗都被
  // 收斂成「空目錄」，畫面上就是一個打開來沒有選項的下拉——使用者看不出是壞了
  // 還是清單真的是空的，也沒有任何線索指向真正的原因。
  useEffect(() => {
    if (!isRegisterMode) return;
    let cancelled = false;
    fetchRoleCatalog()
      .then((roles) => {
        if (cancelled) return;
        setCatalog(roles);
        setCatalogError(null);
        if (roles.length) setRequestedRole((prev) => prev || roles[0].role);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setCatalog([]);
        setCatalogError(err instanceof Error ? err.message : CATALOG_ERROR_FALLBACK);
      });
    return () => {
      cancelled = true;
    };
  }, [isRegisterMode]);

  // 重試走與 effect 相同的純抓取函式；先清掉錯誤讓畫面回到「載入中」狀態。
  const handleRetryCatalog = () => {
    setCatalogError(null);
    fetchRoleCatalog()
      .then((roles) => {
        setCatalog(roles);
        if (roles.length) setRequestedRole((prev) => prev || roles[0].role);
      })
      .catch((err: unknown) => {
        setCatalog([]);
        setCatalogError(err instanceof Error ? err.message : CATALOG_ERROR_FALLBACK);
      });
  };

  const handleToggleMode = () => {
    setIsRegisterMode(!isRegisterMode);
    setError(null);
    setCatalogError(null);
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
                {/*
                  三態渲染。原本這裡只有一個 <select>，所以「抓取失敗」與「清單為空」
                  在畫面上長得一模一樣：一個打得開、但裡面什麼都沒有的下拉。
                */}
                {catalogError ? (
                  <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex flex-col gap-2 text-xs text-red-300">
                    <span className="text-sm font-semibold">{CATALOG_ERROR_HEADLINE}</span>
                    {/* 原因照實顯示，不改寫成推測。跨來源被擋時瀏覽器給的就是
                        `Failed to fetch`，那個字串本身就是最有用的線索。 */}
                    <span className="text-red-300/80 break-words">
                      原因：{catalogError}。請確認後端服務是否正常，或稍後重試。
                    </span>
                    <button
                      type="button"
                      onClick={handleRetryCatalog}
                      className="self-start px-3 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 font-bold transition-colors cursor-pointer"
                    >
                      重新載入角色清單
                    </button>
                  </div>
                ) : catalog.length === 0 ? (
                  <div className="px-5 py-4 bg-slate-800/40 border border-slate-700 rounded-2xl text-sm text-slate-400">
                    角色清單載入中…
                  </div>
                ) : (
                  <select
                    value={requestedRole}
                    onChange={(e) => setRequestedRole(e.target.value)}
                    // `[color-scheme:dark]` 與 option 的深色底不是這個下拉曾經空白的
                    // 原因（那是跨來源請求被擋、目錄根本沒抓到），而是獨立的對比度
                    // 加固：本 app 裡只有這一個 select 把 `text-white` 配上**半透明**
                    // 底（bg-slate-800/50），原生彈出層若沿用那個半透明底就可能是淺色，
                    // 白字會讀不到。AdminPage 與 WaitingApprovalPage 的 select 用的是
                    // 不透明的 bg-slate-900，所以它們不需要這一組。
                    className="w-full px-5 py-4 bg-slate-800/50 border border-slate-700 text-white [color-scheme:dark] rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                  >
                    {catalog.map((r) => (
                      <option key={r.role} value={r.role} className="bg-slate-800 text-white">
                        {r.display_name}（{r.role}）
                      </option>
                    ))}
                  </select>
                )}
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

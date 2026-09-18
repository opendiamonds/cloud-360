import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/auth-context';
import { useLayoutNav } from './NavChromeContext';

export const Sidebar: React.FC = () => {
  const { user, logout, can, canArch } = useAuth();
  const navigate = useNavigate();
  const { sidebarCollapsed, toggleSidebarCollapsed } = useLayoutNav();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // 細項三旗標皆未勾選 → 不顯示該功能（can/canArch 的 view 已含 edit／review）
  const showArchWorkspace = canArch('view');
  const showAssessment = can('A3', 'view');
  const showUsersAdmin = can('J3a', 'view');
  const showMatrixAdmin = can('J3b', 'view');
  const showCoreSection = showArchWorkspace || showAssessment;
  const showAdminSection = showUsersAdmin || showMatrixAdmin;

  // 預設展開，且隨時可收放（不因目前路由鎖死）
  const [archOpen, setArchOpen] = useState(true);
  const [adminOpen, setAdminOpen] = useState(true);

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-4 py-2.5 text-sm font-bold rounded-xl transition-colors ${
      isActive
        ? 'bg-brand-50 text-brand-700'
        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
    }`;

  const adminLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-4 py-2.5 text-sm font-bold rounded-xl transition-colors ${
      isActive
        ? 'bg-blue-50 text-blue-700'
        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
    }`;

  const groupHeaderClass =
    'w-full flex items-center justify-between px-4 py-2.5 text-base font-bold text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-xl transition-colors';

  if (sidebarCollapsed) {
    return (
      <div className="w-14 bg-white border-r border-gray-200 h-screen flex flex-col shrink-0 items-center py-3 gap-3">
        <button
          type="button"
          data-testid="sidebar-toggle"
          onClick={toggleSidebarCollapsed}
          className="p-2 text-gray-500 hover:text-brand-600 hover:bg-brand-50 rounded-xl transition-colors"
          title="展開側欄"
          aria-label="展開側欄"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        </button>
        <div className="w-6 h-6 bg-brand-600 rounded-sm flex items-center justify-center rotate-45 shrink-0">
          <div className="w-3 h-3 bg-white -rotate-45" />
        </div>
        <div className="flex-1" />
        <button
          onClick={handleLogout}
          className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"
          title="登出系統"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
            />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div className="w-64 bg-white border-r border-gray-200 h-screen flex flex-col shrink-0">
      <div className="h-16 flex items-center justify-between px-4 border-b border-gray-100 gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-6 h-6 bg-brand-600 rounded-sm flex items-center justify-center rotate-45 shrink-0">
            <div className="w-3 h-3 bg-white -rotate-45" />
          </div>
          <span className="font-bold text-lg text-gray-900 tracking-tight truncate">
            Cloud-360
          </span>
        </div>
        <button
          type="button"
          data-testid="sidebar-toggle"
          onClick={toggleSidebarCollapsed}
          className="p-2 text-gray-400 hover:text-brand-600 hover:bg-brand-50 rounded-xl transition-colors shrink-0"
          title="收合側欄"
          aria-label="收合側欄"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
            />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-4">
        {showCoreSection && (
          <div className="mb-2">
            <button
              type="button"
              className={groupHeaderClass}
              onClick={() => setArchOpen((o) => !o)}
              aria-expanded={archOpen}
            >
              <span>架構</span>
              <svg
                className={`w-3.5 h-3.5 transition-transform ${archOpen ? 'rotate-90' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
            {archOpen && (
              <nav className="space-y-1 px-2 mt-1">
                {showArchWorkspace && (
                  <NavLink to="/workspace" className={linkClass}>
                    <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                      />
                    </svg>
                    架構圖生成
                  </NavLink>
                )}
                {showAssessment && (
                  <NavLink to="/assessment" className={linkClass}>
                    <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                      />
                    </svg>
                    評估儀表板
                  </NavLink>
                )}
              </nav>
            )}
          </div>
        )}

        {showAdminSection && (
          <div className={showCoreSection ? 'mt-4' : ''}>
            <button
              type="button"
              className={groupHeaderClass}
              onClick={() => setAdminOpen((o) => !o)}
              aria-expanded={adminOpen}
            >
              <span>系統管理</span>
              <svg
                className={`w-3.5 h-3.5 transition-transform ${adminOpen ? 'rotate-90' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
            {adminOpen && (
              <nav className="space-y-1 px-2 mt-1">
                {showUsersAdmin && (
                  <NavLink to="/admin/users" className={adminLinkClass}>
                    <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                      />
                    </svg>
                    使用者角色
                  </NavLink>
                )}
                {showUsersAdmin && (
                  <NavLink to="/admin/authorization-requests" className={adminLinkClass}>
                    <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                      />
                    </svg>
                    授權申請
                  </NavLink>
                )}
                {showMatrixAdmin && (
                  <NavLink to="/admin/role-permissions" className={adminLinkClass}>
                    <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
                      />
                    </svg>
                    角色細項權限
                  </NavLink>
                )}
              </nav>
            )}
          </div>
        )}

        {!showCoreSection && !showAdminSection && (
          <p className="px-4 text-xs text-gray-400 leading-relaxed">
            目前角色尚未開放任何功能選單，請聯絡管理員調整權限。
          </p>
        )}
      </div>

      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-xl bg-brand-600 text-white flex items-center justify-center text-sm font-bold shrink-0 shadow-md shadow-brand-500/20">
              {user?.username ? user.username[0].toUpperCase() : 'U'}
            </div>
            <div className="min-w-0">
              <div className="text-sm font-extrabold text-gray-900 truncate">
                {user?.username || 'User'}
              </div>
              <div className="text-[10px] font-bold text-gray-500 truncate uppercase tracking-wider">
                {user?.authorization_status === 'pending'
                  ? '待授權'
                  : user?.role || 'Guest'}
              </div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"
            title="登出系統"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

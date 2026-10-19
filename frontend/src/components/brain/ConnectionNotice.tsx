import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/auth-context';
import { useBrainSession } from '../../brain/brainSession';

/**
 * ConnectionNotice — 連線的終止與放棄提示（`BR92.2`、`BR92.5`；security-design §六之二）
 *
 * 4401 → 「連線已失效，請重新登入」＋ 按鈕（登出後導 /login），不自動重連、不自動跳轉；
 * 放棄 → 「無法連線到大腦」＋「重新連線」；版本不符 → 不重試；4403 → 不導航、無按鈕。
 */
export const ConnectionNotice: React.FC = () => {
  const conn = useBrainSession();
  const { logout } = useAuth();
  const navigate = useNavigate();
  let body: React.ReactNode;
  switch (conn.status) {
    case 'gave-up':
      body = (
        <>
          <span>無法連線到大腦</span>
          <button type="button" data-testid="brain-reconnect" onClick={conn.reconnect} className="font-semibold text-brand-700 hover:underline">
            重新連線
          </button>
        </>
      );
      break;
    case 'needs-login':
      body = (
        <>
          <span>連線已失效，請重新登入</span>
          <button
            type="button"
            data-testid="brain-relogin"
            onClick={() => {
              logout();
              navigate('/login');
            }}
            className="font-semibold text-brand-700 hover:underline"
          >
            重新登入
          </button>
        </>
      );
      break;
    case 'version-mismatch':
      body = <span>版本不相容，請重新整理頁面</span>;
      break;
    case 'forbidden':
      body = <span>你目前沒有使用大腦的權限</span>;
      break;
    default:
      body = null;
  }
  if (body === null) return null;
  return (
    <div data-testid="brain-connection-notice" data-status={conn.status} className="flex flex-wrap items-center gap-3 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
      {body}
    </div>
  );
};

import React, { useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/auth-context';
import { LiveRegion } from '../components/LiveRegion';
import { objectCreateAction, ObjectCreateError } from '../projects/objectCreateAction';

/**
 * ProjectCreatePage — 建立專案（`BR82.1`–`BR82.3`、`BR82.5`）
 *
 * **路由**：`/projects/new`，由 `App.tsx` 以 `CapabilityRoute`（`K2`／`edit`）把關。
 *
 * - 寫入只經 `objectCreateAction`（唯一的建立寫入路徑）。
 * - 送出期間按鈕進入 pending、**保持可聚焦**（`aria-disabled` 而非 `disabled`）；
 *   pending 期間再次觸發**不發第二次**——以 ref 判定，因為 state 更新在同一事件迴圈內
 *   尚未生效，連點兩下兩次都會讀到舊的 `pending`。
 * - 失敗：三類文案，名稱保留、表單留在原頁。
 * - 成功：導向 `/projects/<新 id>?tab=overview`（`replace`，使建立頁不留在瀏覽歷史中）。
 */
export const ProjectCreatePage: React.FC = () => {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveMsg, setLiveMsg] = useState('');
  const inFlight = useRef(false);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!token || inFlight.current) return;
    inFlight.current = true;
    setPending(true);
    setError(null);
    objectCreateAction(token, 'project', name)
      .then((project) => {
        setLiveMsg('已建立專案');
        navigate(`/projects/${project.id}?tab=overview`, { replace: true });
      })
      .catch((err: unknown) => {
        const message = err instanceof ObjectCreateError ? err.message : '建立專案失敗，請稍後再試';
        setError(message);
        setLiveMsg(message);
      })
      .finally(() => {
        inFlight.current = false;
        setPending(false);
      });
  };

  return (
    <div className="p-6" data-testid="project-create-page">
      <LiveRegion message={liveMsg} />
      <nav aria-label="麵包屑" className="mb-2 text-sm text-gray-500">
        <Link to="/projects" className="hover:underline">
          專案
        </Link>
        <span aria-hidden="true"> / </span>
        <span>建立專案</span>
      </nav>
      <h1 className="mb-4 text-xl font-bold text-gray-900">建立專案</h1>
      <form onSubmit={handleSubmit} noValidate className="max-w-md space-y-3">
        <div>
          <label htmlFor="project-create-name" className="block text-sm font-bold text-gray-700">
            專案名稱
          </label>
          <input
            id="project-create-name"
            data-testid="project-create-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? 'project-create-error' : undefined}
            className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm"
          />
          {error && (
            <p
              id="project-create-error"
              data-testid="project-create-error"
              className="mt-1 text-sm font-bold text-red-700"
            >
              {error}
            </p>
          )}
        </div>
        <button
          type="submit"
          data-testid="project-create-submit"
          aria-disabled={pending ? true : undefined}
          className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700"
        >
          {pending ? '建立中…' : '建立'}
        </button>
      </form>
    </div>
  );
};

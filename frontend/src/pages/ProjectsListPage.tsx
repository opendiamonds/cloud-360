import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/auth-context';
import { LiveRegion } from '../components/LiveRegion';
import { createFanoutQueue, FanoutCancelled } from '../projects/fanoutQueue';
import {
  listProjects,
  listSystems,
  type ProjectOut,
  type SystemOut,
} from '../projects/projectsApi';

/**
 * ProjectsListPage — 專案清單（`US11`；`BR81.1`–`BR81.4`、`BR88.1`–`BR88.3`）
 *
 * **路由**：`/projects`，由 `App.tsx` 以 `CapabilityRoute`（`K2`／`view`）把關。
 *
 * **四個互斥的呈現**：`loading`（骨架列）／`ready`／`empty`／`error`。`empty` 只由
 * 「取得成功且為空陣列」推導，**與 `error` 不共用呈現**——讀取失敗被呈現成「還沒有
 * 任何專案」會讓使用者去建立而不是重試（`BR81.2`、`BR81.3`）。
 *
 * **每列的系統清單經扇出佇列取得**（`BR88.3`）：端點 1 完成後依專案 id 遞增入列，
 * 同時最多 4 個在途、不截斷。`systemsByProject` 中**缺鍵 ＝ 載入中**（排隊與在途對使用者
 * 沒有差別，不另設狀態）；「尚無系統」只在鍵存在且為空陣列時渲染，失敗為 `'failed'`
 * 並顯示「系統清單讀取失敗」——不得顯示為 0（`BR81.4`）。
 */

type ListStatus = 'loading' | 'ready' | 'empty' | 'error';
type RowSystems = SystemOut[] | 'failed';

function formatDate(value: string | null | undefined): string {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const ProjectListSkeleton: React.FC = () => (
  <ul data-testid="project-list-skeleton" aria-hidden="true" className="space-y-2">
    {[0, 1, 2].map((i) => (
      <li key={i} className="rounded-xl border border-gray-100 p-4">
        <div className="h-4 w-48 animate-pulse rounded bg-gray-200" />
        <div className="mt-2 h-3 w-72 animate-pulse rounded bg-gray-100" />
      </li>
    ))}
  </ul>
);

const ProjectListEmpty: React.FC<{ canCreate: boolean }> = ({ canCreate }) => (
  <div data-testid="project-list-empty" className="rounded-xl border border-gray-100 p-8 text-center">
    <p className="text-sm text-gray-700">還沒有任何專案。</p>
    <p className="mt-1 text-sm text-gray-600">
      專案是架構圖、成本估算與需求的歸屬單位——建立第一個之後，這裡會列出它們。
    </p>
    {canCreate && (
      <Link
        to="/projects/new"
        data-testid="project-list-empty-create"
        className="mt-4 inline-block rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700"
      >
        <span aria-hidden="true">+ </span>建立第一個專案
      </Link>
    )}
  </div>
);

const ProjectListError: React.FC<{ onRetry: () => void }> = ({ onRetry }) => (
  <div data-testid="project-list-error" className="rounded-xl border border-red-100 bg-red-50 p-4">
    <p className="text-sm font-bold text-red-800">
      <span aria-hidden="true">(!) </span>讀不到專案清單。
    </p>
    <p className="mt-1 text-sm text-red-800">這不是「你沒有專案」——是這次取得失敗了。</p>
    <button
      type="button"
      data-testid="project-list-retry"
      onClick={onRetry}
      className="mt-2 rounded-xl border border-red-200 bg-white px-3 py-1.5 text-sm font-bold text-red-800 hover:bg-red-100"
    >
      重試
    </button>
  </div>
);

const ProjectListRow: React.FC<{ project: ProjectOut; systems: RowSystems | undefined }> = ({
  project,
  systems,
}) => {
  let count: string;
  let second: string;
  let state: 'loading' | 'ok' | 'failed';
  if (systems === undefined) {
    state = 'loading';
    count = '';
    second = '載入系統中…';
  } else if (systems === 'failed') {
    state = 'failed';
    count = '';
    second = '系統清單讀取失敗';
  } else {
    state = 'ok';
    count = `${systems.length} 個系統`;
    second = systems.length === 0 ? '尚無系統' : systems.map((s) => s.name).join(' / ');
  }
  const created = formatDate(project.created_at);
  return (
    <li
      data-testid={`project-list-row-${project.id}`}
      className="flex items-center justify-between gap-3 rounded-xl border border-gray-100 p-4"
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <span className="max-w-xs truncate font-bold text-gray-900" title={project.name}>
            {project.name}
          </span>
          {count && (
            <span data-testid={`project-list-row-count-${project.id}`} className="text-sm text-gray-600">
              {count}
            </span>
          )}
          {created && <span className="text-sm text-gray-500">建立於 {created}</span>}
        </div>
        <p
          data-testid={`project-list-row-systems-${project.id}`}
          data-state={state}
          className={`mt-1 text-sm ${state === 'failed' ? 'text-red-700' : 'text-gray-600'}`}
        >
          {second}
        </p>
      </div>
      <Link
        to={`/projects/${project.id}?tab=overview`}
        data-testid={`project-list-open-${project.id}`}
        aria-label={`開啟專案 ${project.name}`}
        className="rounded-xl px-3 py-2 text-sm font-bold text-brand-700 hover:bg-brand-50"
      >
        <span aria-hidden="true">&gt;</span>
      </Link>
    </li>
  );
};

export const ProjectsListPage: React.FC = () => {
  const { token, can } = useAuth();
  const canCreate = can('K2', 'edit');

  const [status, setStatus] = useState<ListStatus>('loading');
  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [systemsByProject, setSystemsByProject] = useState<Map<number, RowSystems>>(
    () => new Map()
  );
  // 初始播報以初始值帶入，不在 effect body 內同步 setState（`BR88.1`）。
  const [liveMsg, setLiveMsg] = useState('正在載入專案');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    const queue = createFanoutQueue();
    listProjects(token)
      .then((list) => {
        if (cancelled) return;
        setProjects(list);
        setSystemsByProject(new Map());
        if (list.length === 0) {
          setStatus('empty');
          setLiveMsg('還沒有任何專案');
          return;
        }
        setStatus('ready');
        setLiveMsg(`已載入 ${list.length} 個專案`);
        const ordered = [...list].sort((a, b) => a.id - b.id);
        for (const project of ordered) {
          queue
            .enqueue(() => listSystems(token, project.id))
            .then((systems) => {
              if (cancelled) return;
              setSystemsByProject((prev) => new Map(prev).set(project.id, systems));
            })
            .catch((err: unknown) => {
              if (cancelled || err instanceof FanoutCancelled) return;
              setSystemsByProject((prev) => new Map(prev).set(project.id, 'failed'));
            });
        }
      })
      .catch(() => {
        if (cancelled) return;
        setStatus('error');
        setLiveMsg('讀不到專案清單');
      });
    return () => {
      cancelled = true;
      queue.cancel();
    };
  }, [token, reloadKey]);

  const handleRetry = () => {
    setStatus('loading');
    setLiveMsg('正在載入專案');
    setReloadKey((k) => k + 1);
  };

  return (
    <div className="p-6" data-testid="projects-list-page">
      <LiveRegion message={liveMsg} />
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-bold text-gray-900">專案</h1>
        {canCreate && (
          <Link
            to="/projects/new"
            data-testid="project-create-button"
            className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700"
          >
            <span aria-hidden="true">+ </span>建立專案
          </Link>
        )}
      </div>

      {status === 'loading' && <ProjectListSkeleton />}
      {status === 'error' && <ProjectListError onRetry={handleRetry} />}
      {status === 'empty' && <ProjectListEmpty canCreate={canCreate} />}
      {status === 'ready' && (
        <ul data-testid="project-list" className="space-y-2">
          {projects.map((project) => (
            <ProjectListRow
              key={project.id}
              project={project}
              systems={systemsByProject.get(project.id)}
            />
          ))}
        </ul>
      )}
    </div>
  );
};

import React, { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/auth-context';
import { LiveRegion } from '../components/LiveRegion';
import { ProjectTabs, type ProjectTabDef, type ProjectTabKey } from '../components/projects/ProjectTabs';
import { OverviewTab } from '../components/projects/OverviewTab';
import { RequirementsTab, type RequirementsInputState } from '../components/projects/RequirementsTab';
import { MemorySummaryTab } from '../components/projects/MemorySummaryTab';
import { createFanoutQueue, FanoutCancelled } from '../projects/fanoutQueue';
import {
  ApiError,
  listDiagramChanges,
  listProjects,
  listSystems,
  type DiagramChangeOut,
  type ProjectOut,
  type SystemOut,
} from '../projects/projectsApi';
import { readFields, type FieldSetView } from '../projects/requirementsApi';

/**
 * ProjectDetailPage — 專案詳情（`US11`、`AC12.1.3`／`AC12.6.3`；`BR83`、`BR85.1`、`BR88`）
 *
 * **路由**：`/projects/:projectId?tab=overview|requirements|memory`，由 `App.tsx` 以
 * `CapabilityRoute`（`K2`／`view`）把關。需求籤另需 `K4 view`（`BR83.2`）。
 *
 * **資料只有一份，由本頁持有**（`BR85.1`、不變量 `I-4`）：`fieldsBySystem` 是總覽的未填
 * 總和、待補的需求與需求籤各組 x/y 的唯一來源；三籤都只讀它，**切籤不發請求**——`tab`
 * **不在** effect 的依賴陣列內（`PPN-05`），籤以網址 `?tab=` 表達並以 `replace` 更新。
 *
 * **進頁順序**（`W3`）：端點 1（專案清單，挑出本專案；無單一專案端點）→ 端點 2（系統清單）
 * → 扇出。專案不在可見清單內、或系統清單回 404 → 同一個 not-found 態（`BR83.4`），**不得**
 * 呈現成「尚無系統」——非成員會誤以為自己有存取權。
 *
 * **扇出**（`BR88.3`、functional-design `R-04`）：一個並行上限 4 的佇列，**先**依系統 id 遞增
 * 入列全部端點 5（需求欄位，具 `K4 view` 時）、**再**依系統 id 遞增入列全部端點 7（變更紀錄）。
 * 不進佇列者：端點 1、進頁那一次端點 2、建立系統後的系統清單重讀、儲存後的端點 5 重讀、
 * `[重新整理]`——使用者按了動作不該等其他系統的扇出完成。卸載時依序 `cancelled = true`、
 * `queue.cancel()`：尚未發出者永不發出，在途者的結果被丟棄（`PPN-04`）。
 *
 * 本頁持有 `changesBySystem`（而非總覽籤自行抓取）：端點 7 必須與端點 5 共用同一個佇列並
 * 排在其後，只有頁面能決定入列順序。
 */

type DetailStatus = 'loading' | 'ready' | 'not-found' | 'error';
type FieldsEntry = FieldSetView | 'failed';
type ChangesEntry = DiagramChangeOut[] | 'failed';
type ReloadOutcome = 'ok' | 'reload-failed';

const byId = (a: { id: number }, b: { id: number }) => a.id - b.id;

const ProjectNotFound: React.FC = () => (
  <div data-testid="project-not-found" className="rounded-xl border border-gray-100 p-6">
    <h1 className="text-lg font-bold text-gray-900">查不到這個專案</h1>
    <p className="mt-1 text-sm text-gray-600">
      這個專案可能不存在，或你不是它的成員。若你需要存取，請聯絡該專案的管理者。
    </p>
    <Link to="/projects" className="mt-3 inline-block text-sm font-bold text-brand-700 hover:underline">
      回到專案清單
    </Link>
  </div>
);

const ProjectDetailHeader: React.FC<{ project: ProjectOut; canSeeMembers: boolean }> = ({
  project,
  canSeeMembers,
}) => (
  <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
    <div className="min-w-0">
      <nav aria-label="麵包屑" className="text-sm text-gray-500">
        <Link to="/projects" className="hover:underline">
          專案
        </Link>
        <span aria-hidden="true"> / </span>
      </nav>
      <h1 className="truncate text-xl font-bold text-gray-900" title={project.name}>
        {project.name}
      </h1>
    </div>
    {/* 頁首只有 [成員]；[設定] 無任何上游定義的目的地，不渲染（`BR83.3`、`OPEN-PP23-4`）。 */}
    {canSeeMembers && (
      <Link
        to={`/projects/${project.id}/members`}
        data-testid="project-members-link"
        className="rounded-xl border border-gray-200 px-3 py-1.5 text-sm font-bold text-gray-700 hover:bg-gray-50"
      >
        成員
      </Link>
    )}
  </div>
);

export const ProjectDetailPage: React.FC = () => {
  const { projectId: projectIdParam } = useParams<{ projectId: string }>();
  const projectId = Number(projectIdParam);
  // 程式審查 R-04：非正整數的網址（如 /projects/abc）不會有任何專案，直接呈現 not-found
  // （BR83.4），而不是永遠停在「正在載入」。以渲染時推導而非在 effect 內 setState
  // （react-hooks/set-state-in-effect）。
  const invalidId = !Number.isInteger(projectId) || projectId <= 0;
  const [searchParams, setSearchParams] = useSearchParams();
  const { token, user, can } = useAuth();
  const canSeeFields = can('K4', 'view');
  const canEditFields = can('K4', 'edit');

  const [status, setStatus] = useState<DetailStatus>('loading');
  const [project, setProject] = useState<ProjectOut | null>(null);
  const [systems, setSystems] = useState<SystemOut[]>([]);
  const [fieldsBySystem, setFieldsBySystem] = useState<Map<number, FieldsEntry>>(() => new Map());
  const [lastGoodFields, setLastGoodFields] = useState<Map<number, FieldSetView>>(() => new Map());
  const [changesBySystem, setChangesBySystem] = useState<Map<number, ChangesEntry>>(
    () => new Map()
  );
  const [liveMsg, setLiveMsg] = useState('正在載入專案');
  const [reloadKey, setReloadKey] = useState(0);
  // 需求籤的使用者輸入由本頁持有（程式審查 R-02）：只渲染目前籤，需求籤切走即卸載，
  // 輸入、失敗標記與「已儲存、重新整理失敗」若放在需求籤內，切籤回來就消失。
  const [reqSelected, setReqSelected] = useState<number | null>(null);
  const [reqDrafts, setReqDrafts] = useState<Map<string, string>>(() => new Map());
  const [reqErrors, setReqErrors] = useState<Map<string, string>>(() => new Map());
  const [reqStale, setReqStale] = useState<Set<string>>(() => new Set());
  const requirementsInput: RequirementsInputState = {
    selected: reqSelected,
    setSelected: setReqSelected,
    drafts: reqDrafts,
    setDrafts: setReqDrafts,
    fieldErrors: reqErrors,
    setFieldErrors: setReqErrors,
    savedStale: reqStale,
    setSavedStale: setReqStale,
  };

  useEffect(() => {
    if (!token || invalidId) return;
    let cancelled = false;
    const queue = createFanoutQueue();

    const storeFields = (systemId: number, view: FieldSetView) => {
      setFieldsBySystem((prev) => new Map(prev).set(systemId, view));
      setLastGoodFields((prev) => new Map(prev).set(systemId, view));
    };

    listProjects(token)
      .then((list) => {
        if (cancelled) return null;
        const found = list.find((p) => p.id === projectId);
        if (!found) {
          setStatus('not-found');
          setLiveMsg('查不到這個專案');
          return null;
        }
        setProject(found);
        return listSystems(token, projectId);
      })
      .then((loaded) => {
        if (cancelled || loaded === null) return;
        setSystems(loaded);
        setFieldsBySystem(new Map());
        setLastGoodFields(new Map());
        setChangesBySystem(new Map());
        // 換專案或重試時，上一份輸入不屬於這次載入的資料。
        setReqSelected(null);
        setReqDrafts(new Map());
        setReqErrors(new Map());
        setReqStale(new Set());
        setStatus('ready');
        setLiveMsg('已載入專案');
        const ordered = [...loaded].sort(byId);
        // functional-design R-04：先全部端點 5、再全部端點 7（FIFO 即順序保證）。
        if (canSeeFields) {
          for (const system of ordered) {
            queue
              .enqueue(() => readFields(token, system.id))
              .then((view) => {
                if (!cancelled) storeFields(system.id, view);
              })
              .catch((err: unknown) => {
                if (cancelled || err instanceof FanoutCancelled) return;
                setFieldsBySystem((prev) => new Map(prev).set(system.id, 'failed'));
              });
          }
        }
        for (const system of ordered) {
          queue
            .enqueue(() => listDiagramChanges(token, system.id))
            .then((changes) => {
              if (!cancelled) setChangesBySystem((prev) => new Map(prev).set(system.id, changes));
            })
            .catch((err: unknown) => {
              if (cancelled || err instanceof FanoutCancelled) return;
              setChangesBySystem((prev) => new Map(prev).set(system.id, 'failed'));
            });
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setStatus('not-found');
          setLiveMsg('查不到這個專案');
          return;
        }
        setStatus('error');
        setLiveMsg('讀不到這個專案');
      });

    return () => {
      cancelled = true;
      queue.cancel();
    };
  }, [token, projectId, invalidId, canSeeFields, reloadKey]);

  /** 建立系統成功：**直接**重讀系統清單（不經佇列），新系統各取一次欄位與變更紀錄。 */
  const handleSystemCreated = () => {
    if (!token) return;
    const known = new Set(systems.map((s) => s.id));
    listSystems(token, projectId)
      .then((next) => {
        setSystems(next);
        setLiveMsg(`已建立系統，目前共 ${next.length} 個系統`);
        for (const system of next.filter((s) => !known.has(s.id))) {
          if (canSeeFields) {
            readFields(token, system.id)
              .then((view) => {
                setFieldsBySystem((prev) => new Map(prev).set(system.id, view));
                setLastGoodFields((prev) => new Map(prev).set(system.id, view));
              })
              .catch(() => setFieldsBySystem((prev) => new Map(prev).set(system.id, 'failed')));
          }
          listDiagramChanges(token, system.id)
            .then((changes) => setChangesBySystem((prev) => new Map(prev).set(system.id, changes)))
            .catch(() => setChangesBySystem((prev) => new Map(prev).set(system.id, 'failed')));
        }
      })
      .catch(() => setLiveMsg('已建立系統，但系統清單重新讀取失敗'));
  };

  /** 儲存後與 `[重新整理]` 的重讀（`BR85.3`、`BR85.6`）：以新物件取代該系統那一筆。 */
  const handleReload = (systemId: number): Promise<ReloadOutcome> => {
    if (!token) return Promise.resolve('reload-failed');
    return readFields(token, systemId)
      .then((view): ReloadOutcome => {
        setFieldsBySystem((prev) => new Map(prev).set(systemId, view));
        setLastGoodFields((prev) => new Map(prev).set(systemId, view));
        return 'ok';
      })
      .catch((): ReloadOutcome => {
        setFieldsBySystem((prev) => new Map(prev).set(systemId, 'failed'));
        return 'reload-failed';
      });
  };

  const tabs: ProjectTabDef[] = [
    { key: 'overview', label: '總覽' },
    ...(canSeeFields ? [{ key: 'requirements' as const, label: '需求' }] : []),
    { key: 'memory', label: '記憶摘要' },
  ];
  const requested = searchParams.get('tab');
  const active: ProjectTabKey = tabs.some((t) => t.key === requested)
    ? (requested as ProjectTabKey)
    : 'overview';

  const handleSelectTab = (key: ProjectTabKey) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set('tab', key);
        return next;
      },
      { replace: true }
    );
  };

  const handleRetry = () => {
    setStatus('loading');
    setLiveMsg('正在載入專案');
    setReloadKey((k) => k + 1);
  };

  return (
    <div className="p-6" data-testid="project-detail-page">
      <LiveRegion message={invalidId ? '查不到這個專案' : liveMsg} />
      {invalidId && <ProjectNotFound />}
      {!invalidId && status === 'loading' && (
        <p className="text-sm text-gray-500">正在載入專案…</p>
      )}
      {!invalidId && status === 'not-found' && <ProjectNotFound />}
      {!invalidId && status === 'error' && (
        <div data-testid="project-detail-error" className="rounded-xl border border-red-100 bg-red-50 p-4">
          <p className="text-sm font-bold text-red-800">讀不到這個專案。這次取得失敗了。</p>
          <button
            type="button"
            onClick={handleRetry}
            className="mt-2 rounded-xl border border-red-200 bg-white px-3 py-1.5 text-sm font-bold text-red-800"
          >
            重試
          </button>
        </div>
      )}
      {!invalidId && status === 'ready' && project && token && (
        <>
          <ProjectDetailHeader project={project} canSeeMembers={can('K3', 'view')} />
          <ProjectTabs tabs={tabs} active={active} onSelect={handleSelectTab} />
          <div
            role="tabpanel"
            id={`project-panel-${active}`}
            aria-labelledby={`project-tab-${active}`}
            tabIndex={0}
          >
            {active === 'overview' && (
              <OverviewTab
                project={project}
                systems={systems}
                fieldsBySystem={fieldsBySystem}
                changesBySystem={changesBySystem}
                canSeeFields={canSeeFields}
                onSystemCreated={handleSystemCreated}
              />
            )}
            {active === 'requirements' && (
              <RequirementsTab
                token={token}
                project={project}
                systems={systems}
                fieldsBySystem={fieldsBySystem}
                lastGoodFields={lastGoodFields}
                canEdit={canEditFields}
                currentUserId={user?.id}
                onReload={handleReload}
                onSystemCreated={handleSystemCreated}
                onLiveMessage={setLiveMsg}
                input={requirementsInput}
              />
            )}
            {active === 'memory' && <MemorySummaryTab />}
          </div>
        </>
      )}
    </div>
  );
};

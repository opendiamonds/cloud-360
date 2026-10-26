import React, { useCallback, useEffect, useId, useRef, useState } from 'react';
import { useAuth } from '../../context/auth-context';
import { useBrainSession, type WorkTargetIds } from '../../brain/brainSession';
import { fetchProjects, fetchSystems } from '../../brain/objectPickerData';
import {
  currentRowKey,
  filterGroups,
  isOwnedByMe,
  normalize,
  PICKER_WIDTH_PX,
  rowKey,
  targetIdsForProject,
  targetIdsForSystem,
  type SystemsEntry,
} from '../../brain/objectPickerModel';
import { ApiError, type ProjectOut, type SystemOut } from '../../projects/projectsApi';
import { createFanoutQueue, FanoutCancelled, type FanoutQueue } from '../../projects/fanoutQueue';
import { ObjectPickerGroup } from './ObjectPickerGroup';
import { ObjectPickerCreateForm } from './ObjectPickerCreateForm';

/**
 * ObjectPicker — `ContextBar` 內的「切換作業對象」選單（`U16`；`US9.2`）
 *
 * 互動流程正本 `functional-spec.md` §五 W1–W6；規則 `rules.md` `BR11`–`BR15`；以下更正附錄優先：
 * `functional-spec-corrections.md`（F-01–F-08）、`nfr-requirements-corrections.md`（N-01–N-07）、
 * `nfr-design-corrections.md`（D-01–D-07）。
 *
 * **一次開啟＝一次掛載**（`performance-design.md` §一之一）。三組正交 state（`F-06`）：
 * - 身分：`identity` 於渲染時**衍生**（`D-04`）；`user.id` 不是數字時呼叫一次 `refreshMe()`，仍不是數字即 failed。
 * - 清單：專案清單 1 次（`N-02` 第 1 點）；目前作業對象所在專案預設展開；其餘群組展開才抓；搜尋第一次非空
 *   輸入時以 `fanoutQueue` 補抓其餘群組（同時最多 4 個、FIFO）。
 * - 表單：同時只開一張（`BR14.4`），清單重抓不關表單。
 *
 * **冪等登記簿是同步 ref**（`D-01`）：`ensureSystems` 在發出請求**之前**同步寫入 `'loading'`；補抓佇列中的工作
 * 在**執行時**才檢查登記簿，所以「已入列、尚未發出」的群組被展開時，展開那一次發出、佇列那一次跳過，同一
 * 專案在同一次開啟內至多被抓 1 次（`N-02` 第 5 點）。`systemsByProject` state 只負責畫面。
 *
 * 非同步結果寫 state 前一律檢查 `mountedRef`（`OPN-02`）；卸載時取消補抓佇列（尚未發出者永不發出）。
 *
 * **補抓的觸發對齊兩個條件的成立時點**（`review-01` `R-01`）：「清單已載入」與「搜尋字非空」誰後成立，就在
 * 那一刻起補抓——輸入事件（清單已載入時）與專案清單的 `.then`（使用者已在載入中輸入時，讀 `queryRef`）。
 * 補抓收尾只在佇列仍是目前那一輪時清忙碌旗標（`R-07`）。
 *
 * 關閉路徑：Escape、點選單外（`mousedown`）、選定、建立成功，以及**開啟期間「切換對象」鈕因捲動而移位或視窗
 * 尺寸改變**（`R-05`：座標只在點擊時量測一次，脫離錨點時關閉而非重定位）。dialog 根節點 `tabIndex=-1`：
 * 點到選單內的非控件區域時焦點落在根節點，Escape 與焦點陷阱照常經過 `onKeyDown`（`R-04`）。
 *
 * 播報（`F-04`）：開啟期間寫選單內播報區 `brain-object-picker-live`；關閉之後才發生的訊息（「已建立並切換到 X」）
 * 寫頁面的大腦 `LiveRegion`（`announce`）。
 *
 * 本檔屬選單檔案集合：不得有主控台輸出、瀏覽器儲存、`innerHTML`、`RegExp`、直接匯入建立函式或 `new WebSocket`
 * （`eslint.config.js` 末端的 U16 區塊）。
 */
/** 選單的錨定座標（viewport 座標，由 ContextBar 在點擊當下量測）。 */
export interface PickerPlacement {
  top: number;
  /** md 以上的左緣；md 以下為全寬（左右各 1rem），不使用此值。 */
  left: number;
  maxHeight: number;
}

export interface ObjectPickerProps {
  /** 關閉選單（ContextBar 清 `pickerOpen` 並把焦點還給「切換對象」鈕）。 */
  onClose: () => void;
  /** 「切換對象」鈕：點在它上面不算「點選單外」（它自己的 onClick 負責開關）。 */
  anchorRef: React.RefObject<HTMLElement | null>;
  anchor: PickerPlacement;
}

type ProjectsState =
  | { status: 'loading' }
  | { status: 'loaded'; projects: ProjectOut[] }
  | { status: 'error'; forbidden: boolean };

type OpenForm = { kind: 'project' } | { kind: 'system'; projectId: number } | null;

const FOCUSABLE = 'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** 零寬空白：螢幕報讀器不唸，但使相同文字的第二次寫入仍是一次 DOM 內容變更（review-02 R-09）。 */
const REANNOUNCE_MARK = String.fromCharCode(0x200b);

function withEntry(prev: ReadonlyMap<number, SystemsEntry>, pid: number, entry: SystemsEntry): Map<number, SystemsEntry> {
  const next = new Map(prev);
  next.set(pid, entry);
  return next;
}

export const ObjectPicker: React.FC<ObjectPickerProps> = ({ onClose, anchorRef, anchor }) => {
  const { token, user, can, refreshMe } = useAuth();
  const { target, setWorkTarget, announce } = useBrainSession();
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const mountedRef = useRef(false);
  const refreshTriedRef = useRef(false);
  const registryRef = useRef(new Map<number, 'loading' | 'loaded' | 'error'>());
  const backfillStartedRef = useRef(false);
  const queueHolder = useRef<{ queue: FanoutQueue | null }>({ queue: null });
  const targetRef = useRef(target);
  /** 最新的搜尋字（專案清單 `.then` 判斷是否補起補抓用；R-01）。 */
  const queryRef = useRef('');

  const [attempted, setAttempted] = useState(false);
  const [projectsState, setProjectsState] = useState<ProjectsState>({ status: 'loading' });
  const [reloadKey, setReloadKey] = useState(0);
  const [systemsByProject, setSystemsByProject] = useState<ReadonlyMap<number, SystemsEntry>>(() => new Map());
  const [expanded, setExpanded] = useState<ReadonlySet<number>>(() => new Set());
  const [backfillBusy, setBackfillBusy] = useState(false);
  const [query, setQuery] = useState('');
  const [openForm, setOpenForm] = useState<OpenForm>(null);
  const [switchError, setSwitchError] = useState<string | null>(null);
  const [formFailure, setFormFailure] = useState<string | null>(null);
  const [activeKey, setActiveKey] = useState<string | null>(null);

  const authToken = token ?? '';
  const userId = typeof user?.id === 'number' ? user.id : null;
  const identity: 'ok' | 'resolving' | 'failed' = userId !== null ? 'ok' : attempted ? 'failed' : 'resolving';
  const canEdit = can('K2', 'edit');

  // 掛載／卸載：mountedRef 與補抓佇列的取消（BR12.4、OPN-02）。開啟時焦點進搜尋框（BR15.1）。
  useEffect(() => {
    mountedRef.current = true;
    const holder = queueHolder.current;
    searchRef.current?.focus();
    return () => {
      mountedRef.current = false;
      holder.queue?.cancel();
    };
  }, []);

  useEffect(() => {
    targetRef.current = target;
  }, [target]);

  // 身分未決（F-03、N-01、D-04）：呼叫一次 refreshMe()；結果在 .finally 回呼（非同步）內記為已嘗試。
  useEffect(() => {
    if (typeof user?.id === 'number' || refreshTriedRef.current) return;
    refreshTriedRef.current = true;
    refreshMe()
      .catch(() => undefined)
      .finally(() => {
        if (mountedRef.current) setAttempted(true);
      });
  }, [user, refreshMe]);

  const retryIdentity = () => {
    searchRef.current?.focus();
    setAttempted(false);
    refreshMe()
      .catch(() => undefined)
      .finally(() => {
        if (mountedRef.current) setAttempted(true);
      });
  };

  /** 冪等：登記簿無此鍵、或為 error 且由重試鈕呼叫時才發請求（D-01）。 */
  const ensureSystems = useCallback(
    (pid: number, retry = false): Promise<void> => {
      const registry = registryRef.current;
      const state = registry.get(pid);
      if (state === 'loading' || state === 'loaded') return Promise.resolve();
      if (state === 'error' && !retry) return Promise.resolve();
      registry.set(pid, 'loading');
      setSystemsByProject((prev) => withEntry(prev, pid, { status: 'loading', systems: [] }));
      return fetchSystems(authToken, pid).then(
        (systems) => {
          if (!mountedRef.current) return;
          registry.set(pid, 'loaded');
          setSystemsByProject((prev) => withEntry(prev, pid, { status: 'loaded', systems }));
        },
        () => {
          if (!mountedRef.current) return;
          registry.set(pid, 'error');
          setSystemsByProject((prev) => withEntry(prev, pid, { status: 'error', systems: [] }));
        }
      );
    },
    [authToken]
  );

  /**
   * 補抓：對尚未請求的群組以 fanoutQueue 抓系統清單（N-02 第 3 點），一次開啟至多一輪。工作在執行時才檢查
   * 登記簿（D-01）。收尾以佇列物件比對：只有仍是目前這一輪時才清忙碌旗標，被取消的舊輪不會清掉新輪的（R-07）。
   */
  const startBackfill = useCallback(
    (list: readonly ProjectOut[]) => {
      backfillStartedRef.current = true;
      const pending = list.filter((p) => !registryRef.current.has(p.id));
      if (pending.length === 0) return;
      const queue = createFanoutQueue();
      queueHolder.current.queue = queue;
      setBackfillBusy(true);
      const tasks = pending.map((p) =>
        queue.enqueue(() => ensureSystems(p.id)).catch((err: unknown) => {
          if (!(err instanceof FanoutCancelled)) throw err;
        })
      );
      void Promise.allSettled(tasks).then(() => {
        if (mountedRef.current && queueHolder.current.queue === queue) setBackfillBusy(false);
      });
    },
    [ensureSystems]
  );

  // 專案清單：身分確認後抓 1 次；目前作業對象所在專案預設展開並抓其系統（N-02 第 1 點）。
  const identityOk = identity === 'ok';
  useEffect(() => {
    if (!identityOk) return;
    let cancelled = false;
    fetchProjects(authToken)
      .then((projects) => {
        if (cancelled || !mountedRef.current) return;
        setProjectsState({ status: 'loaded', projects });
        const pid = targetRef.current?.projectId ?? null;
        const current = pid === null ? undefined : projects.find((p) => String(p.id) === pid);
        if (current) {
          setExpanded((prev) => new Set(prev).add(current.id));
          void ensureSystems(current.id);
        }
        // R-01：使用者在清單回來之前已輸入非空字串——此刻才是「清單已載入且搜尋非空」成立的時點。
        if (!backfillStartedRef.current && normalize(queryRef.current) !== '') startBackfill(projects);
      })
      .catch((err: unknown) => {
        if (cancelled || !mountedRef.current) return;
        setProjectsState({ status: 'error', forbidden: err instanceof ApiError && err.status === 403 });
      });
    return () => {
      cancelled = true;
    };
  }, [identityOk, authToken, reloadKey, ensureSystems, startBackfill]);

  const retryProjects = () => {
    searchRef.current?.focus();
    registryRef.current.clear();
    backfillStartedRef.current = false;
    queueHolder.current.queue?.cancel();
    queueHolder.current.queue = null;
    setSystemsByProject(new Map());
    setExpanded(new Set());
    setBackfillBusy(false);
    setProjectsState({ status: 'loading' });
    setReloadKey((k) => k + 1);
  };

  const projects = projectsState.status === 'loaded' ? projectsState.projects : [];

  const onSearch = (value: string) => {
    queryRef.current = value;
    setQuery(value);
    setSwitchError(null);
    if (!backfillStartedRef.current && projectsState.status === 'loaded' && normalize(value) !== '') startBackfill(projects);
  };

  const toggleExpand = (pid: number) => {
    const opening = !expanded.has(pid);
    setSwitchError(null);
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(pid)) next.delete(pid);
      else next.add(pid);
      return next;
    });
    if (opening) void ensureSystems(pid);
  };

  // 選定（BR11.2／BR11.3）：不本地改脈絡列；回 true 即關閉，回 false 就地顯示並播報（D-03：不重抓）。
  const pick = (ids: WorkTargetIds) => {
    setSwitchError(null);
    if (setWorkTarget(ids)) {
      onClose();
      return;
    }
    setSwitchError('目前無法切換：與大腦的連線中斷');
  };

  const onCreated = (created: ProjectOut | SystemOut) => {
    const ids = 'project_id' in created ? targetIdsForSystem(created) : targetIdsForProject(created);
    setOpenForm(null);
    setFormFailure(null);
    if (setWorkTarget(ids)) {
      announce(`已建立並切換到 ${created.name}`);
      onClose();
      return;
    }
    setSwitchError('已建立，但目前無法切換');
  };

  const focusInDialog = (testid: string) => {
    dialogRef.current?.querySelector<HTMLElement>(`[data-testid="${testid}"]`)?.focus();
  };

  // 重試鈕在重試開始時即被移除；把焦點移到穩定的控件，避免焦點落到 body 而跳出選單（BR15.2）。
  const retrySystems = (pid: number) => {
    focusInDialog(`brain-object-expand-${pid}`);
    void ensureSystems(pid, true);
  };

  const openCreate = (form: Exclude<OpenForm, null>) => {
    setFormFailure(null);
    setOpenForm(form);
  };

  // 建立失敗寫入選單內播報區（R-06／review-02 R-09）：與目前文字相同時附一個零寬空白（再相同就拿掉），使相同錯誤
  // 連續兩次仍是一次內容變更而被重唸；不先清空，播報區因此不會在兩次失敗之間退回清單狀態文字。
  // 與 useBrainConnection 的 announceFresh 同一做法；更新式為純函式。
  const reportFormFailure = (message: string) => {
    setFormFailure((prev) => (prev === message ? `${message}${REANNOUNCE_MARK}` : message));
  };

  const cancelForm = () => {
    const form = openForm;
    setOpenForm(null);
    setFormFailure(null);
    if (form?.kind === 'project') focusInDialog('brain-object-create-project');
    else if (form?.kind === 'system') focusInDialog(`brain-object-create-system-${form.projectId}`);
  };

  // 點選單外 → 關閉（F-06：無背景遮罩，點外部等同取消）。
  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      const node = event.target as Node | null;
      if (!node) return;
      if (dialogRef.current?.contains(node)) return;
      if (anchorRef.current?.contains(node)) return;
      onClose();
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [onClose, anchorRef]);

  // R-05：座標只在點擊時量測一次。開啟期間錨點（切換鈕）因任何捲動容器捲動而移位、或視窗尺寸改變時即關閉，
  // 不做重定位。選單本身的捲動（overflow-y-auto）不算；只比對錨點位置，未移位的捲動事件不關閉。
  // 視窗只比寬度（review-02 R-09）：行動裝置的虛擬鍵盤在搜尋框聚焦時會改變 innerHeight，比高度會讓選單一打字就關。
  // 選單的捲動到底後不外溢到頁面，見對話框的 overscroll-contain。
  useEffect(() => {
    const start = anchorRef.current?.getBoundingClientRect();
    const startW = window.innerWidth;
    const onScroll = (event: Event) => {
      const node = event.target;
      if (node instanceof Node && dialogRef.current?.contains(node)) return;
      const now = anchorRef.current?.getBoundingClientRect();
      if (!start || !now) return;
      if (Math.abs(now.top - start.top) > 1 || Math.abs(now.left - start.left) > 1) onClose();
    };
    const onResize = () => {
      if (window.innerWidth !== startW) onClose();
    };
    document.addEventListener('scroll', onScroll, { capture: true, passive: true });
    window.addEventListener('resize', onResize);
    return () => {
      document.removeEventListener('scroll', onScroll, { capture: true });
      window.removeEventListener('resize', onResize);
    };
  }, [onClose, anchorRef]);

  // ---- 衍生值 ----
  const filtered = filterGroups(projects, systemsByProject, query);
  const searching = normalize(query) !== '';
  const matchedCount = filtered.filter((g) => g.matched).length;
  const noMatch = projectsState.status === 'loaded' && projects.length > 0 && searching && matchedCount === 0 && !backfillBusy;
  const currentKey = currentRowKey(target);
  // 搜尋中：命中系統的群組自動展開；補抓失敗的群組也展開，使其錯誤與重試看得到（N-02 第 3 點）。
  // 不寫回 expanded，清空搜尋即回到搜尋前的展開狀態。
  const isExpanded = (pid: number, systemHit: boolean) =>
    expanded.has(pid) || (searching && (systemHit || systemsByProject.get(pid)?.status === 'error'));

  const visibleRowKeys: string[] = [];
  for (const g of filtered) {
    visibleRowKeys.push(rowKey('p', g.project.id));
    if (isExpanded(g.project.id, g.systemHit)) for (const s of g.systems) visibleRowKeys.push(rowKey('s', s.id));
  }
  const effectiveActive = activeKey !== null && visibleRowKeys.includes(activeKey) ? activeKey : (visibleRowKeys[0] ?? null);

  let dataState: 'loading' | 'default' | 'empty' | 'error' | 'no-match';
  if (identity === 'failed' || projectsState.status === 'error') dataState = 'error';
  else if (identity === 'resolving' || projectsState.status === 'loading') dataState = 'loading';
  else if (projects.length === 0) dataState = 'empty';
  else if (noMatch) dataState = 'no-match';
  else dataState = 'default';

  let listText = '';
  if (dataState === 'no-match') listText = '沒有符合的對象';
  else if (dataState === 'default' && searching && !backfillBusy) listText = `${matchedCount} 個符合的專案`;
  else if (dataState === 'default') listText = `已載入 ${projects.length} 個專案`;
  const liveText = switchError ?? formFailure ?? listText;

  // ---- 鍵盤：焦點陷阱、Escape、方向鍵（BR15.2／BR15.3） ----
  const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      if (openForm) cancelForm();
      else onClose();
      return;
    }
    if (event.key === 'Tab') {
      const root = dialogRef.current;
      if (!root) return;
      const items = Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.tabIndex >= 0 && !el.closest('[hidden]')
      );
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      const activeEl = document.activeElement;
      // 焦點在根節點本身（點到非控件區域後，R-04）視同不在任何控件上。
      const outside = activeEl === root || !root.contains(activeEl);
      if (event.shiftKey && (activeEl === first || outside)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (activeEl === last || outside)) {
        event.preventDefault();
        first.focus();
      }
      return;
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      const key = (document.activeElement as HTMLElement | null)?.dataset?.rowKey;
      if (!key) return;
      const index = visibleRowKeys.indexOf(key);
      const nextIndex = event.key === 'ArrowDown' ? index + 1 : index - 1;
      if (index < 0 || nextIndex < 0 || nextIndex >= visibleRowKeys.length) return;
      event.preventDefault();
      const nextKey = visibleRowKeys[nextIndex];
      setActiveKey(nextKey);
      dialogRef.current?.querySelector<HTMLElement>(`[data-row-key="${nextKey}"]`)?.focus();
    }
  };

  // R-04：點到選單內的非控件區域（標題、留白、說明文字）時，把焦點收回根節點，使之後的 Escape／Tab 仍經過
  // onKeyDown。瀏覽器對 tabIndex=-1 的祖先本就會這麼做；明寫一次，不依賴預設行為。點在控件上則不干預。
  const onRootMouseDown = (event: React.MouseEvent<HTMLDivElement>) => {
    const root = dialogRef.current;
    if (!root || !(event.target instanceof Element)) return;
    const control = event.target.closest('button, input, textarea, select, a[href], label, [tabindex]');
    if (control && control !== root && root.contains(control)) return;
    event.preventDefault();
    root.focus();
  };

  const createProjectForm =
    openForm?.kind === 'project' ? (
      <ObjectPickerCreateForm
        kind="project"
        token={authToken}
        onCreated={onCreated}
        onCancel={cancelForm}
        onFailure={reportFormFailure}
      />
    ) : null;

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      data-testid="brain-object-picker"
      data-state={dataState}
      tabIndex={-1}
      onKeyDown={onKeyDown}
      onMouseDown={onRootMouseDown}
      style={{
        top: anchor.top,
        maxHeight: anchor.maxHeight,
        ['--picker-left' as string]: `${anchor.left}px`,
        ['--picker-width' as string]: `${PICKER_WIDTH_PX}px`,
      }}
      className="fixed left-4 right-4 z-50 flex flex-col gap-2 overflow-y-auto overscroll-contain rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-lg focus:outline-none md:left-(--picker-left) md:right-auto md:w-(--picker-width)"
    >
      <h2 id={titleId} className="text-sm font-semibold text-gray-900">
        切換作業對象
      </h2>
      <input
        ref={searchRef}
        type="search"
        data-testid="brain-object-search"
        aria-label="搜尋作業對象"
        placeholder="搜尋專案或系統"
        value={query}
        onChange={(e) => onSearch(e.target.value)}
        className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
      />
      <div role="status" data-testid="brain-object-picker-live" className="sr-only">
        {liveText}
      </div>

      {switchError !== null && (
        <p data-testid="brain-object-switch-error" className="text-xs text-red-700">
          {switchError}
        </p>
      )}

      {dataState === 'loading' && (
        <p data-testid="brain-object-loading" className="text-xs text-gray-600">
          正在載入…
        </p>
      )}

      {identity === 'failed' && (
        <div data-testid="brain-object-identity-error" className="flex items-center gap-2 text-xs text-red-700">
          <span>無法確認你的身分，請重新整理頁面</span>
          <button
            type="button"
            data-testid="brain-object-identity-retry"
            onClick={retryIdentity}
            className="rounded border border-red-300 px-2 py-0.5 font-semibold text-red-700 hover:bg-red-50"
          >
            重試
          </button>
        </div>
      )}

      {identity === 'ok' && projectsState.status === 'error' && (
        <div data-testid="brain-object-error" className="flex items-center gap-2 text-xs text-red-700">
          <span>{projectsState.forbidden ? '你沒有檢視專案的權限' : '無法載入清單'}</span>
          {!projectsState.forbidden && (
            <button
              type="button"
              data-testid="brain-object-retry"
              onClick={retryProjects}
              className="rounded border border-red-300 px-2 py-0.5 font-semibold text-red-700 hover:bg-red-50"
            >
              重試
            </button>
          )}
        </div>
      )}

      {dataState === 'empty' && (
        <p data-testid="brain-object-empty" className="text-xs text-gray-600">
          {canEdit
            ? '你還沒有任何專案，可以在下方建立一個。'
            : '你還沒有任何專案。需要具備建立權限的同事邀請你加入，或請管理者調整你的權限。'}
        </p>
      )}

      {dataState === 'no-match' && (
        <p data-testid="brain-object-no-match" className="text-xs text-gray-600">
          沒有符合的對象
        </p>
      )}

      {backfillBusy && (
        <p data-testid="brain-object-backfill-status" className="text-xs text-gray-600">
          正在載入系統清單
        </p>
      )}

      {identity === 'ok' && projectsState.status === 'loaded' && filtered.length > 0 && (
        <ul aria-label="專案與系統" aria-busy={backfillBusy ? 'true' : undefined} data-testid="brain-object-list">
          {filtered.map((g) => {
            const owned = userId !== null && isOwnedByMe(g.project, userId);
            const pid = g.project.id;
            return (
              <ObjectPickerGroup
                key={pid}
                group={g}
                expanded={isExpanded(pid, g.systemHit)}
                selectable={owned}
                canCreateSystem={owned && canEdit}
                currentKey={currentKey}
                activeKey={effectiveActive}
                onPickProject={(p) => pick(targetIdsForProject(p))}
                onPickSystem={(s) => pick(targetIdsForSystem(s))}
                onToggleExpand={toggleExpand}
                onRetrySystems={retrySystems}
                onOpenCreateSystem={(id) => openCreate({ kind: 'system', projectId: id })}
                onRowFocus={setActiveKey}
                form={
                  openForm?.kind === 'system' && openForm.projectId === pid ? (
                    <ObjectPickerCreateForm
                      kind="system"
                      projectId={pid}
                      token={authToken}
                      onCreated={onCreated}
                      onCancel={cancelForm}
                      onFailure={reportFormFailure}
                    />
                  ) : null
                }
              />
            );
          })}
        </ul>
      )}

      {canEdit && (
        <div className="border-t border-gray-100 pt-2">
          <button
            type="button"
            data-testid="brain-object-create-project"
            onClick={() => openCreate({ kind: 'project' })}
            className="text-xs font-semibold text-brand-700 hover:underline"
          >
            + 新增專案
          </button>
          {createProjectForm}
        </div>
      )}
    </div>
  );
};

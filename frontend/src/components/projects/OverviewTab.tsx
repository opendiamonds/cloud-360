import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/auth-context';
import type { BrainConnection } from '../../brain/brainSession';
import {
  listMyDiagrams,
  type DiagramChangeOut,
  type MyDiagram,
  type ProjectOut,
  type SystemOut,
} from '../../projects/projectsApi';
import type { FieldSetView } from '../../projects/requirementsApi';
import { RecentChanges } from './RecentChanges';
import { SystemCreateAction } from './SystemCreateAction';
import { SystemDiagrams, type MyDiagramsLoad } from './SystemDiagrams';

/**
 * OverviewTab — 專案詳情的總覽籤（`AC11.1.1`、`AC11.1.3`、`AC11.3.1`–`AC11.3.3`；
 * `BR85.2`、`BR85.4`、`BR85.5`、`BR86.1`、`BR86.2`）
 *
 * **讀的是頁面持有的同一份 `fieldsBySystem`**（`BR85.1`、不變量 `I-4`）：「未填需求欄位」
 * 與「待補的需求」是同一份狀態的兩個視圖，與需求籤也讀同一份，**切到本籤不發請求**。
 *
 * - 未填需求欄位 ＝ Σ 各系統 `unfilled_count`；任一系統失敗 → 「無法取得」，**不顯示部分和**；
 *   未到齊 → 載入中（`BR85.2`、`BR88.3`）。全部已填時顯示 0（`BR85.4`）。
 * - 無 `K4 view` 時兩區**整個不在 DOM 內**（`BR85.5`）——顯示 0 會與「全部已填」的 0 意義相反。
 * - 架構圖計數（部署後追加，2026-11-15；**本階段新增、已核可 scope／requirements 尚未涵蓋**，原為
 *   `BR86.1`／`OPEN-PP23-1` 的固定「尚無法取得」）：＝「我的圖」中 `system_id` 屬於本專案系統者的張數。
 *   資料與「系統的架構圖」區同一份（本元件持有、傳給 `SystemDiagrams`），可見範圍因此與該區一致：
 *   `GET /api/collab/diagrams` 只對自己擁有的圖給 `system_id`，故**只數得到自己的圖**，不數也不洩漏別人
 *   掛在系統上、使用者打不開的圖。缺 `A1 view`（拿不到圖清單）仍顯示「尚無法取得」；載入中／失敗各自標示，
 *   不顯示 0（0 會被讀成「沒有圖」）。
 */

/** 本專案系統下「我的圖」張數（純函式；P3 突變的鎖定點）。 */
function attachedCount(systems: SystemOut[], diagrams: MyDiagram[]): number {
  const ids = new Set(systems.map((s) => s.id));
  return diagrams.filter((d) => d.system_id !== null && ids.has(d.system_id)).length;
}

type FieldsEntry = FieldSetView | 'failed';

function fieldSummary(systems: SystemOut[], fieldsBySystem: Map<number, FieldsEntry>) {
  if (systems.some((s) => fieldsBySystem.get(s.id) === 'failed')) return 'failed' as const;
  if (!systems.every((s) => fieldsBySystem.has(s.id))) return 'loading' as const;
  return 'complete' as const;
}

const PendingRequirements: React.FC<{
  systems: SystemOut[];
  fieldsBySystem: Map<number, FieldsEntry>;
  state: 'failed' | 'loading' | 'complete';
}> = ({ systems, fieldsBySystem, state }) => {
  const lines: { key: string; text: string }[] = [];
  if (state === 'complete') {
    for (const system of [...systems].sort((a, b) => a.id - b.id)) {
      const view = fieldsBySystem.get(system.id);
      if (!view || view === 'failed') continue;
      for (const group of view.groups) {
        const labels = group.fields.filter((f) => f.filled_state !== 'filled').map((f) => f.label);
        if (labels.length > 0) {
          lines.push({
            key: `${system.id}-${group.group_key}`,
            text: `${system.name}（${group.title}）：${labels.join('、')}`,
          });
        }
      }
    }
  }
  return (
    <section data-testid="project-pending-requirements" aria-labelledby="project-pending-title">
      <h2 id="project-pending-title" className="text-sm font-bold text-gray-900">
        待補的需求
      </h2>
      {state === 'loading' && <p className="mt-2 text-sm text-gray-500">正在載入需求欄位…</p>}
      {state === 'failed' && <p className="mt-2 text-sm font-bold text-amber-800">無法取得</p>}
      {state === 'complete' && lines.length === 0 && (
        <p className="mt-2 text-sm text-gray-600">沒有待補的需求</p>
      )}
      {lines.length > 0 && (
        <ul className="mt-2 space-y-1 text-sm text-gray-700">
          {lines.map((line) => (
            <li key={line.key}>{line.text}</li>
          ))}
        </ul>
      )}
    </section>
  );
};

export const OverviewTab: React.FC<{
  project: ProjectOut;
  systems: SystemOut[];
  fieldsBySystem: Map<number, FieldsEntry>;
  changesBySystem: Map<number, DiagramChangeOut[] | 'failed'>;
  canSeeFields: boolean;
  onSystemCreated: () => void;
  /** 本頁的大腦連線；無 `K1 view` 時為 null。 */
  brain: BrainConnection | null;
}> = ({ project, systems, fieldsBySystem, changesBySystem, canSeeFields, onSystemCreated, brain }) => {
  const { token, canArch } = useAuth();
  const canSeeDiagrams = canArch('view');
  const [diagramsLoad, setDiagramsLoad] = useState<MyDiagramsLoad>({ status: 'loading' });
  const [diagramsReloadKey, setDiagramsReloadKey] = useState(0);

  useEffect(() => {
    if (!token || !canSeeDiagrams) return;
    let cancelled = false;
    listMyDiagrams(token)
      .then((diagrams) => {
        if (!cancelled) setDiagramsLoad({ status: 'ready', diagrams });
      })
      .catch(() => {
        if (!cancelled) setDiagramsLoad({ status: 'failed' });
      });
    return () => {
      cancelled = true;
    };
  }, [token, canSeeDiagrams, diagramsReloadKey]);

  let diagramCount: React.ReactNode;
  if (!canSeeDiagrams) {
    diagramCount = (
      <>
        <strong>尚無法取得</strong>
        <span className="ml-1 text-xs text-gray-500">（你沒有檢視架構圖的權限）</span>
      </>
    );
  } else if (diagramsLoad.status === 'loading') {
    diagramCount = <strong>載入中…</strong>;
  } else if (diagramsLoad.status === 'failed') {
    diagramCount = <strong>無法取得</strong>;
  } else {
    diagramCount = (
      <>
        <strong data-testid="project-count-diagrams-value">{attachedCount(systems, diagramsLoad.diagrams)}</strong>
        <span className="ml-1 text-xs text-gray-500">（你掛在這個專案各系統的架構圖）</span>
      </>
    );
  }

  const state = fieldSummary(systems, fieldsBySystem);
  let total = 0;
  for (const s of systems) {
    const view = fieldsBySystem.get(s.id);
    if (view && view !== 'failed') total += view.unfilled_count;
  }
  // 部分失敗時**不顯示部分和**（`BR85.2`）：偏小的數字會被讀成「已填了」。
  const unfilledText =
    state === 'failed' ? '無法取得' : state === 'loading' ? '載入中…' : String(total);

  return (
    <div className="space-y-6">
      <section aria-labelledby="project-counts-title">
        <h2 id="project-counts-title" className="sr-only">
          計數
        </h2>
        <ul className="flex flex-wrap items-center gap-x-8 gap-y-2 text-sm text-gray-800">
          <li className="flex items-center gap-2">
            <span id="project-count-systems-label" data-testid="project-count-systems">
              系統 <strong>{systems.length}</strong>
            </span>
            <SystemCreateAction
              project={project}
              describedById="project-count-systems-label"
              onCreated={onSystemCreated}
            />
          </li>
          <li data-testid="project-count-diagrams">架構圖 {diagramCount}</li>
          {canSeeFields && (
            <li data-testid="project-count-unfilled">
              未填需求欄位 <strong>{unfilledText}</strong>
            </li>
          )}
        </ul>
      </section>
      {/* build-and-test F1：系統的架構圖（掛載／改掛／取消）。 */}
      <SystemDiagrams
        project={project}
        systems={systems}
        state={diagramsLoad}
        onReload={() => setDiagramsReloadKey((k) => k + 1)}
        brain={brain}
      />
      <RecentChanges systems={systems} changesBySystem={changesBySystem} />
      {canSeeFields && (
        <PendingRequirements systems={systems} fieldsBySystem={fieldsBySystem} state={state} />
      )}
    </div>
  );
};

import React from 'react';
import type { DiagramChangeOut, ProjectOut, SystemOut } from '../../projects/projectsApi';
import type { FieldSetView } from '../../projects/requirementsApi';
import { RecentChanges } from './RecentChanges';
import { SystemCreateAction } from './SystemCreateAction';

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
 * - 架構圖計數**沒有資料來源**，固定渲染「尚無法取得」（`BR86.1`、`OPEN-PP23-1`）。
 */

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
}> = ({ project, systems, fieldsBySystem, changesBySystem, canSeeFields, onSystemCreated }) => {
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
          <li data-testid="project-count-diagrams">
            架構圖 <strong>尚無法取得</strong>
            <span className="ml-1 text-xs text-gray-500">（架構圖目前沒有專案歸屬可供計數）</span>
          </li>
          {canSeeFields && (
            <li data-testid="project-count-unfilled">
              未填需求欄位 <strong>{unfilledText}</strong>
            </li>
          )}
        </ul>
      </section>
      <RecentChanges systems={systems} changesBySystem={changesBySystem} />
      {canSeeFields && (
        <PendingRequirements systems={systems} fieldsBySystem={fieldsBySystem} state={state} />
      )}
    </div>
  );
};

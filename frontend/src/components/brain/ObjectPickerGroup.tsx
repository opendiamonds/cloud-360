import React, { useId } from 'react';
import { rowKey, type FilteredGroup } from '../../brain/objectPickerModel';
import type { ProjectOut, SystemOut } from '../../projects/projectsApi';

/**
 * ObjectPickerGroup — 選單內的一個專案群組（`BR13.1`–`BR13.3`、`BR14.3`；`nfr-requirements-corrections.md` `N-02`）
 *
 * 純呈現：不自行抓取、不自行判定擁有者。`selectable` 與 `canCreateSystem` 由 `ObjectPicker` 以同一個
 * `isOwnedByMe` 算好傳入（`OPN-12`），兩者因此不可能分歧（不存在「選不了卻能在底下建系統」）。
 *
 * - 專案列本身可選（零系統的專案亦可選，`BR13.1`）；展開鈕是另一個控件（`aria-expanded`／`aria-controls`），
 *   展開才觸發該群組的系統清單請求（`N-02` 第 2 點）。
 * - 不可選的列照列、`aria-disabled="true"`、可聚焦但啟用無效，並以 `aria-describedby` 連到群組下的說明
 *   （`BR13.2`、`BR15.3`）。
 * - 目前作業對象的列標文字「目前」＋ `aria-current="true"`（`BR13.3`）。
 * - 名稱一律以 React 文字節點呈現（`OPN-13`）。
 */
export interface ObjectPickerGroupProps {
  group: FilteredGroup;
  expanded: boolean;
  selectable: boolean;
  canCreateSystem: boolean;
  currentKey: string | null;
  /** roving tabIndex：此鍵的列 `tabIndex=0`，其餘 `-1`（`BR15.3`）。 */
  activeKey: string | null;
  onPickProject: (project: ProjectOut) => void;
  onPickSystem: (system: SystemOut) => void;
  onToggleExpand: (projectId: number) => void;
  onRetrySystems: (projectId: number) => void;
  onOpenCreateSystem: (projectId: number) => void;
  onRowFocus: (key: string) => void;
  /** 此群組的「新增系統」表單（僅在開啟時由父層傳入）。 */
  form: React.ReactNode;
}

const ROW_BASE =
  'flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500';

export const ObjectPickerGroup: React.FC<ObjectPickerGroupProps> = ({
  group,
  expanded,
  selectable,
  canCreateSystem,
  currentKey,
  activeKey,
  onPickProject,
  onPickSystem,
  onToggleExpand,
  onRetrySystems,
  onOpenCreateSystem,
  onRowFocus,
  form,
}) => {
  const { project, entry, systems } = group;
  const pid = project.id;
  const noteId = useId();
  const listId = useId();
  const projectKey = rowKey('p', pid);
  const describedBy = selectable ? undefined : noteId;
  const rowClass = (key: string) =>
    `${ROW_BASE} ${selectable ? 'text-gray-900 hover:bg-brand-50' : 'cursor-not-allowed text-gray-600'} ${
      currentKey === key ? 'bg-brand-50 font-semibold' : ''
    }`;

  return (
    <li data-testid={`brain-object-group-${pid}`} className="border-b border-gray-100 py-1 last:border-b-0">
      <div className="flex items-center gap-1">
        <button
          type="button"
          data-testid={`brain-object-expand-${pid}`}
          aria-expanded={expanded}
          aria-controls={listId}
          aria-label={`${expanded ? '收合' : '展開'}「${project.name}」的系統`}
          onClick={() => onToggleExpand(pid)}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded text-gray-600 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        >
          <span aria-hidden="true">{expanded ? '▾' : '▸'}</span>
        </button>
        <button
          type="button"
          data-testid={`brain-object-project-${pid}`}
          data-row-key={projectKey}
          data-selectable={selectable ? 'true' : 'false'}
          aria-disabled={selectable ? undefined : true}
          aria-describedby={describedBy}
          aria-current={currentKey === projectKey ? 'true' : undefined}
          tabIndex={activeKey === projectKey ? 0 : -1}
          onFocus={() => onRowFocus(projectKey)}
          onClick={() => {
            if (selectable) onPickProject(project);
          }}
          className={rowClass(projectKey)}
        >
          <span className="break-all">{project.name}</span>
          {currentKey === projectKey && <span className="shrink-0 text-xs text-brand-700">目前</span>}
        </button>
        {canCreateSystem && (
          <button
            type="button"
            data-testid={`brain-object-create-system-${pid}`}
            onClick={() => onOpenCreateSystem(pid)}
            className="shrink-0 rounded px-2 py-1 text-xs font-semibold text-brand-700 hover:bg-brand-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            + 新增系統
          </button>
        )}
      </div>
      {!selectable && (
        <p id={noteId} data-testid={`brain-object-not-owned-${pid}`} className="ml-8 text-xs text-gray-600">
          大腦目前只能以你建立的專案為作業對象
        </p>
      )}
      {form && <div className="ml-8">{form}</div>}
      <div id={listId} hidden={!expanded} className="ml-8">
        {expanded && entry?.status === 'loading' && (
          <p data-testid={`brain-object-group-loading-${pid}`} className="px-2 py-1 text-xs text-gray-600">
            正在載入系統…
          </p>
        )}
        {expanded && entry?.status === 'error' && (
          <div data-testid={`brain-object-group-error-${pid}`} className="flex items-center gap-2 px-2 py-1 text-xs text-red-700">
            <span>無法載入系統清單</span>
            <button
              type="button"
              data-testid={`brain-object-group-retry-${pid}`}
              onClick={() => onRetrySystems(pid)}
              className="rounded border border-red-300 px-2 py-0.5 font-semibold text-red-700 hover:bg-red-50"
            >
              重試
            </button>
          </div>
        )}
        {expanded && entry?.status === 'loaded' && entry.systems.length === 0 && (
          <p data-testid={`brain-object-group-empty-${pid}`} className="px-2 py-1 text-xs text-gray-600">
            尚無系統
          </p>
        )}
        {expanded && systems.length > 0 && (
          <ul aria-label={`「${project.name}」的系統`}>
            {systems.map((s) => {
              const key = rowKey('s', s.id);
              return (
                <li key={s.id}>
                  <button
                    type="button"
                    data-testid={`brain-object-item-${s.id}`}
                    data-row-key={key}
                    data-selectable={selectable ? 'true' : 'false'}
                    aria-disabled={selectable ? undefined : true}
                    aria-describedby={describedBy}
                    aria-current={currentKey === key ? 'true' : undefined}
                    tabIndex={activeKey === key ? 0 : -1}
                    onFocus={() => onRowFocus(key)}
                    onClick={() => {
                      if (selectable) onPickSystem(s);
                    }}
                    className={rowClass(key)}
                  >
                    <span className="break-all">{s.name}</span>
                    {currentKey === key && <span className="shrink-0 text-xs text-brand-700">目前</span>}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </li>
  );
};

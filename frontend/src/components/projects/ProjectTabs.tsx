import React, { useRef } from 'react';

/**
 * ProjectTabs — 專案詳情頁的三籤 tablist（`BR83.1`、`NFR11.102`）
 *
 * `role="tablist"`／`tab`、`aria-selected`、`aria-controls`；左右方向鍵在籤間移動、
 * Home／End 到首尾；只有目前籤 `tabIndex=0`（roving tabindex），Tab 鍵進出面板。
 * 本元件**不持有目前籤**——目前籤是網址的 `?tab=`，由頁面以 `replace` 更新
 * （切籤不新增瀏覽歷史項、不發請求，`PPN-05`）。
 */

export type ProjectTabKey = 'overview' | 'requirements' | 'memory';

export interface ProjectTabDef {
  key: ProjectTabKey;
  label: string;
}

// 籤與面板的 id 形狀：`project-tab-<key>`／`project-panel-<key>`。頁面渲染 tabpanel 時
// 以同一形狀組 id（本檔只匯出元件，`react-refresh/only-export-components`）。
const tabId = (key: ProjectTabKey) => `project-tab-${key}`;
const panelId = (key: ProjectTabKey) => `project-panel-${key}`;

export const ProjectTabs: React.FC<{
  tabs: ProjectTabDef[];
  active: ProjectTabKey;
  onSelect: (key: ProjectTabKey) => void;
}> = ({ tabs, active, onSelect }) => {
  const refs = useRef<Map<ProjectTabKey, HTMLButtonElement>>(new Map());

  const move = (key: ProjectTabKey) => {
    onSelect(key);
    refs.current.get(key)?.focus();
  };

  const handleKeyDown = (event: React.KeyboardEvent, index: number) => {
    let next: number | null = null;
    if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
    else if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = tabs.length - 1;
    if (next === null) return;
    event.preventDefault();
    move(tabs[next].key);
  };

  return (
    <div role="tablist" aria-label="專案內容" className="mb-4 flex gap-1 border-b border-gray-200">
      {tabs.map((tab, index) => {
        const selected = tab.key === active;
        return (
          <button
            key={tab.key}
            ref={(el) => {
              if (el) refs.current.set(tab.key, el);
              else refs.current.delete(tab.key);
            }}
            type="button"
            role="tab"
            id={tabId(tab.key)}
            data-testid={`project-tab-${tab.key}`}
            aria-selected={selected}
            aria-controls={panelId(tab.key)}
            tabIndex={selected ? 0 : -1}
            onClick={() => onSelect(tab.key)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-bold ${
              selected
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
};

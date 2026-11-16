import React, { useState } from 'react';
import { useBrainSession } from '../../brain/brainSession';
import { WorkItemRow } from './WorkItemList';

/**
 * WorkItemDock — 常駐區（`BR94.1`、`BR94.2`）
 *
 * 只列處理中與等待中；空集合時整區不渲染；寬度 < 768px 預設收合為一行計數。
 * 與對話流讀同一份工作項集合（INV-1）。
 */
export const WorkItemDock: React.FC = () => {
  const { workItems } = useBrainSession();
  const [collapsed, setCollapsed] = useState(() => typeof window !== 'undefined' && window.innerWidth < 768);
  const active = workItems.filter((w) => w.status === '處理中' || w.status === '等待中');
  if (active.length === 0) return null;
  return (
    <section role="region" aria-label="進行中的工作" data-testid="brain-workitem-dock" className="bg-white border-b border-gray-200 px-4 py-2 text-sm">
      <button
        type="button"
        data-testid="brain-workitem-dock-toggle"
        aria-expanded={!collapsed}
        onClick={() => setCollapsed((c) => !c)}
        className="font-semibold text-gray-700"
      >
        進行中 ({active.length})
      </button>
      {!collapsed && (
        <ul className="mt-1">
          {active.map((item) => (
            <WorkItemRow key={item.workItemId} item={item} />
          ))}
        </ul>
      )}
    </section>
  );
};

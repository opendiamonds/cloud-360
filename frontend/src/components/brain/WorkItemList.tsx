import React from 'react';
import { useBrainSession } from '../../brain/brainSession';
import type { WorkItem } from '../../brain/brainProtocol';

/** 已停掉的附帶說明（BR94.3）：unknown 不得當成 none 呈現。 */
function sideEffectText(sideEffect: string): string {
  if (sideEffect === 'none') return '沒有留下任何東西';
  if (sideEffect === 'unknown') return '不確定有沒有留下東西';
  return sideEffect;
}

const STATUS_CLASS: Record<WorkItem['status'], string> = {
  處理中: 'bg-sky-50 text-sky-700 border-sky-200',
  等待中: 'bg-amber-50 text-amber-700 border-amber-200',
  完成: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  失敗: 'bg-red-50 text-red-700 border-red-200',
  已停掉: 'bg-gray-100 text-gray-600 border-gray-200',
};

/**
 * WorkItemRow — 一個工作項（`BR94.3`、`BR94.4`、`BR94.6`）
 *
 * 徽章文字即狀態值（文字為主要載體）；label 原樣顯示（前端不另抄能力名稱表，capability 只作 data 屬性）。
 * 處理中與等待中有「不是這個」：按下送 correct_work_item，停用到下一則 work_items，不在本地改狀態。
 */
export const WorkItemRow: React.FC<{ item: WorkItem }> = ({ item }) => {
  const conn = useBrainSession();
  const open = item.status === '處理中' || item.status === '等待中';
  const pending = conn.pendingCorrections.includes(item.workItemId);
  let detail: string | null = null;
  if (item.status === '等待中' && item.waitingOn) detail = `在等：${item.waitingOn}`;
  else if (item.status === '失敗' && item.failureReason) detail = item.failureReason;
  else if (item.status === '已停掉') detail = sideEffectText(item.sideEffect);
  return (
    <li data-testid={`brain-workitem-${item.workItemId}`} data-capability={item.capability} className="flex flex-wrap items-start gap-2 py-1">
      <span
        data-testid={`brain-workitem-${item.workItemId}-status`}
        className={`px-2 py-0.5 rounded-full border text-xs font-bold shrink-0 ${STATUS_CLASS[item.status]}`}
      >
        {item.status}
      </span>
      <span className="flex-1 min-w-0 break-all">
        <span className="font-medium text-gray-900">{item.label}</span>
        {detail && <span className="block text-xs text-gray-600">{detail}</span>}
      </span>
      {open && (
        <button
          type="button"
          data-testid={`brain-workitem-${item.workItemId}-reject`}
          aria-label={`不是這個：${item.label}`}
          disabled={pending || conn.status !== 'ready'}
          onClick={() => conn.correctWorkItem(item.workItemId)}
          className="text-xs font-semibold text-red-600 hover:underline disabled:opacity-40 disabled:no-underline"
        >
          不是這個
        </button>
      )}
    </li>
  );
};

/**
 * WorkItemList — 對話流中錨定在某則大腦訊息下的工作項清單（`BR94.5`）
 *
 * 狀態一律取自連線的同一份工作項集合（INV-1，`BR94.1`）；不過濾——已停掉與更正後新建的項目同時可見。
 */
export const WorkItemList: React.FC<{ workItemIds: readonly string[] }> = ({ workItemIds }) => {
  const { workItems } = useBrainSession();
  const items = workItemIds
    .map((id) => workItems.find((w) => w.workItemId === id))
    .filter((w): w is WorkItem => w !== undefined);
  if (items.length === 0) return null;
  return (
    <ul data-testid="brain-workitem-list" className="mt-2 border-l-2 border-gray-200 pl-3 text-sm">
      {items.map((item) => (
        <WorkItemRow key={item.workItemId} item={item} />
      ))}
    </ul>
  );
};

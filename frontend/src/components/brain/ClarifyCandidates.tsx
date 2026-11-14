import React, { useRef } from 'react';
import { useBrainSession } from '../../brain/brainSession';
import type { ClarifyItem } from '../../brain/brainTranscript';

/**
 * ClarifyCandidates — 反問（`BR95.1`–`BR95.5`）
 *
 * 兩種 kind 的提示不同；只顯示 label、不顯示信心值；恆有回絕（候選只有一個時亦然）。選定只在使用者按下時
 * 送出一次，之後整組停用；回絕送 candidateId:null、焦點回輸入列、不改脈絡列。stale／resolved／dismissed 淡化停用。
 */
export const ClarifyCandidates: React.FC<{ item: ClarifyItem }> = ({ item }) => {
  const conn = useBrainSession();
  const groupRef = useRef<HTMLDivElement>(null);
  const intent = item.payload.kind === 'intent';
  const active = item.state === 'default' && conn.status === 'ready';
  const prompt = intent ? '我不確定你指的是哪一件事' : '你指的是哪一個？';

  const dismiss = () => {
    conn.selectCandidate(item.id, null);
    const input = groupRef.current
      ?.closest('[data-brain-session]')
      ?.querySelector<HTMLTextAreaElement>('[data-testid="brain-input"]');
    input?.focus();
  };

  return (
    <div
      ref={groupRef}
      role="group"
      aria-label={intent ? '請選擇你指的是哪一件事' : '請選擇你指的是哪一個'}
      data-testid="brain-clarify"
      data-kind={item.payload.kind}
      data-state={item.state}
      className={`rounded-xl border border-gray-200 bg-white p-3 text-sm ${item.state === 'default' ? '' : 'opacity-60'}`}
    >
      <p className="font-semibold text-gray-800">{prompt}</p>
      <ul className="mt-2 space-y-1">
        {item.payload.candidates.map((c) => (
          <li key={c.id} className="flex items-center gap-2">
            {intent && <span className="flex-1 break-all">{c.label}</span>}
            <button
              type="button"
              data-testid={`brain-clarify-candidate-${c.id}`}
              disabled={!active}
              aria-busy={item.state === 'picking' && item.pickedId === c.id ? true : undefined}
              onClick={() => conn.selectCandidate(item.id, c.id)}
              className="rounded-lg border border-brand-200 px-2 py-1 font-semibold text-brand-700 hover:bg-brand-50 disabled:opacity-50"
            >
              {intent ? '就是這個' : c.label}
            </button>
          </li>
        ))}
      </ul>
      <button
        type="button"
        data-testid="brain-clarify-restate"
        disabled={!active}
        onClick={dismiss}
        className="mt-2 rounded-lg border border-dashed border-gray-400 px-2 py-1 text-gray-600 disabled:opacity-50"
      >
        {intent ? '都不是，我再講一次' : '都不是'}
      </button>
    </div>
  );
};

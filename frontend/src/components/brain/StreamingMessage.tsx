import React from 'react';
import { useBrainSession } from '../../brain/brainSession';
import { useBrainTranscript, type BrainItem } from '../../brain/brainTranscript';
import { CostAnswerCard } from './CostAnswerCard';

const INTERRUPT_TEXT = {
  disconnect: '回覆中斷',
  unmount: '你在回覆完成前離開了這一頁',
} as const;

/**
 * StreamingMessage — 一則大腦訊息（以 turnId 為鍵，`BR93.1`、`BR93.2`、`BR93.6`、`BR93.7`）
 *
 * token 到達即顯示（不緩衝到 done）；串流中 `aria-busy="true"`，完成時的播報由連線在 done 的事件回呼內
 * 寫入 LiveRegion 一次（本元件不播報）。游標以 `motion-reduce:animate-none` 遵守 prefers-reduced-motion。
 * 零內容的 done → 「沒有收到回覆」＋ 重試；interrupted → 說明 ＋ 重試（不自動重送，`BR92.7`）。
 */
export const StreamingMessage: React.FC<{ item: BrainItem; children?: React.ReactNode }> = ({ item, children }) => {
  const conn = useBrainSession();
  const { dispatch } = useBrainTranscript();
  const retryable =
    (item.status === 'empty' || item.status === 'interrupted' || item.status === 'error') &&
    item.retryText !== null &&
    !item.retried;

  const retry = () => {
    if (item.retryText === null) return;
    dispatch({ type: 'retried', id: item.id });
    conn.sendUserMessage(item.retryText);
  };

  return (
    <div
      data-testid="brain-stream-message"
      data-turn-id={item.turnId}
      data-status={item.status}
      aria-busy={item.status === 'streaming' ? true : undefined}
      className="rounded-xl bg-white border border-gray-200 px-3 py-2 text-sm text-gray-900"
    >
      {item.text && <span className="whitespace-pre-wrap break-words">{item.text}</span>}
      {item.status === 'streaming' && (
        <span
          data-testid="brain-stream-cursor"
          aria-hidden="true"
          className="ml-0.5 inline-block h-4 w-1.5 align-middle bg-gray-500 animate-pulse motion-reduce:animate-none"
        />
      )}
      {item.costCard && <CostAnswerCard card={item.costCard} />}
      {item.status === 'empty' && <p className="text-gray-600">沒有收到回覆</p>}
      {item.status === 'error' && item.errorMessage && <p className="text-red-700">{item.errorMessage}</p>}
      {item.status === 'interrupted' && item.interruptReason && (
        <p className="text-amber-700">{INTERRUPT_TEXT[item.interruptReason]}</p>
      )}
      {retryable && (
        <button
          type="button"
          data-testid="brain-stream-retry"
          disabled={conn.status !== 'ready' || conn.awaitingReply}
          onClick={retry}
          className="mt-1 text-xs font-semibold text-brand-700 hover:underline disabled:opacity-40"
        >
          重試
        </button>
      )}
      {children}
    </div>
  );
};

import React from 'react';
import { useBrainSession } from '../../brain/brainSession';
import { useBrainTranscript, type NoticeItem, type UserItem } from '../../brain/brainTranscript';
import { ClarifyCandidates } from './ClarifyCandidates';
import { StreamingMessage } from './StreamingMessage';
import { WorkItemList } from './WorkItemList';

const USER_INTERRUPT_TEXT = {
  disconnect: '回覆中斷',
  unmount: '你在回覆完成前離開了這一頁',
  // 伺服器以非輪次錯誤拒絕了這句（例如頻率超限；code-generation review-02 R-08、`[EP-R2]`=A）。
  rejected: '這句沒有送達',
} as const;

const UserMessage: React.FC<{ item: UserItem }> = ({ item }) => {
  const conn = useBrainSession();
  const { dispatch } = useBrainTranscript();
  return (
    <div
      data-testid="brain-user-message"
      data-pending={item.pendingConnId !== null ? 'true' : 'false'}
      className="self-end max-w-[85%] rounded-xl bg-brand-600 px-3 py-2 text-sm text-white">
      <span className="whitespace-pre-wrap break-words">{item.text}</span>
      {item.interrupted && (
        <span className="mt-1 block text-xs text-brand-50">
          {USER_INTERRUPT_TEXT[item.interrupted]}
          {!item.retried && (
            <button
              type="button"
              data-testid="brain-stream-retry"
              disabled={conn.status !== 'ready' || conn.awaitingReply}
              onClick={() => {
                dispatch({ type: 'retried', id: item.id });
                conn.sendUserMessage(item.text);
              }}
              className="ml-2 font-semibold underline disabled:opacity-40"
            >
              重試
            </button>
          )}
        </span>
      )}
    </div>
  );
};

/**
 * 系統提示列（非輪次錯誤，`[EP-MB2]`=A）：不屬任何輪次、沿用既有錯誤文字樣式；播報由連線寫入 LiveRegion，
 * 本元件不另設 aria-live（避免重複播報）。
 */
const SystemNotice: React.FC<{ item: NoticeItem }> = ({ item }) => (
  <p
    data-testid="brain-system-notice"
    data-code={item.code}
    className="self-center max-w-[85%] rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700"
  >
    <span className="whitespace-pre-wrap break-words">{item.message}</span>
  </p>
);

/**
 * ConversationView — 本頁目前讀取段的對話紀錄（`BR93.4`、`BR94.5`、`BR97.8`）
 *
 * 讀應用程式層 store 中該段的紀錄（換頁不丟、切換共享模式即改顯示另一段）。工作項清單錨定在它首次出現時
 * 該段最後一則大腦訊息之下；無大腦訊息時列在最後。超過 500 則被截斷時頂端顯示說明（`EPN-04`）。
 * 紀錄為空而作業對象或工作項非空 → 另顯示「先前的對話大腦仍記得…」（`BR93.4`）。
 */
export const ConversationView: React.FC<{ emptyState?: React.ReactNode }> = ({ emptyState }) => {
  const conn = useBrainSession();
  const { state } = useBrainTranscript();
  const seg = state.segments[conn.readSegment];
  const anchored = (anchorId: string) =>
    Object.entries(seg.anchors)
      .filter(([, anchor]) => anchor === anchorId)
      .map(([workItemId]) => workItemId);
  const presentIds = new Set(seg.items.map((i) => i.id));
  // 錨點為空、尚待下一則大腦訊息承接、或錨點已被截斷移除者：列在最後。
  const orphanIds = Object.entries(seg.anchors)
    .filter(([, anchor]) => !presentIds.has(anchor))
    .map(([workItemId]) => workItemId);
  const targetHasLevel =
    conn.target !== null &&
    (conn.target.projectId !== null || conn.target.systemId !== null || conn.target.diagramId !== null);
  const remembered = seg.items.length === 0 && (targetHasLevel || conn.workItems.length > 0);

  return (
    <div data-testid="brain-conversation" className="flex flex-col gap-3">
      {seg.truncated && (
        <p data-testid="brain-transcript-truncated" className="text-center text-xs text-gray-500">
          較早的對話已不在畫面上
        </p>
      )}
      {seg.items.length === 0 && emptyState}
      {remembered && (
        <p data-testid="brain-transcript-remembered" className="text-xs text-gray-500">
          先前的對話大腦仍記得，只是這裡不再顯示
        </p>
      )}
      {seg.items.map((item) => {
        if (item.kind === 'user') return <UserMessage key={item.id} item={item} />;
        // 系統提示不當工作項錨點（anchorWorkItems 會略過它，code-generation review-02 R-10），其下不列工作項。
        if (item.kind === 'notice') return <SystemNotice key={item.id} item={item} />;
        if (item.kind === 'clarify') {
          return (
            <React.Fragment key={item.id}>
              <ClarifyCandidates item={item} />
              <WorkItemList workItemIds={anchored(item.id)} />
            </React.Fragment>
          );
        }
        return (
          <StreamingMessage key={item.id} item={item}>
            <WorkItemList workItemIds={anchored(item.id)} />
          </StreamingMessage>
        );
      })}
      {orphanIds.length > 0 && <WorkItemList workItemIds={orphanIds} />}
    </div>
  );
};

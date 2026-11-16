import React from 'react';
import type { TargetSync } from '../../brain/useWorkspaceTargetSync';
import { useBrainSession } from '../../brain/brainSession';
import { TARGET_NONE, targetLabel } from '../../brain/brainProtocol';

/**
 * SyncNotice — 子頁面與作業對象同步的提示（`BR97.5`、`BR97.6`；security-design §六之三、§六之四）
 *
 * 「作業對象已改為…」與「沒有自動開啟」來自同步掛點的 state（在事件回呼內設定）；「別人分享」
 * 與「未存檔」兩種說明由 render 推導（不另存 state）。「開啟這張圖」只對自有圖出現。
 */
export const SyncNotice: React.FC<{ sync: TargetSync }> = ({ sync }) => {
  const conn = useBrainSession();
  const { notice } = sync;
  const label = conn.target ? targetLabel(conn.target) : TARGET_NONE;

  let text: string | null = null;
  let canOpen = false;
  if (notice?.kind === 'list-failed') {
    text = '無法確認這張圖的擁有者，未同步作業對象';
  } else if (notice?.kind === 'hold') {
    text = `作業對象是「${notice.label}」；目前畫布有未儲存的變更，沒有自動開啟`;
    canOpen = true;
  } else if (notice?.kind === 'changed') {
    text = `作業對象已改為 ${notice.label}`;
    canOpen = notice.canOpen;
  } else if (sync.sharedDiagram) {
    text = '這張圖是別人分享的，不會成為大腦的作業對象';
  } else if (sync.unsavedCanvas) {
    text = `目前畫布未存檔，作業對象維持 ${label}`;
  }
  if (text === null) return null;
  return (
    <div data-testid="brain-sync-notice" className="flex flex-wrap items-center gap-3 bg-amber-50 border-b border-amber-100 px-4 py-2 text-sm text-amber-800">
      <span className="break-all">{text}</span>
      {canOpen && (
        <button
          type="button"
          data-testid="brain-sync-open-diagram"
          onClick={sync.openNoticeDiagram}
          className="font-semibold text-brand-700 hover:underline"
        >
          開啟這張圖
        </button>
      )}
    </div>
  );
};

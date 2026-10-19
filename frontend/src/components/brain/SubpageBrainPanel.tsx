import React, { useState } from 'react';
import { BrainInput } from './BrainInput';
import { ConnectionNotice } from './ConnectionNotice';
import { ConversationView } from './ConversationView';

/**
 * SubpageBrainPanel — 子頁面脈絡列下的「問大腦」精簡面板（`BR97.4`；`[EP1]`=A，偏離 D-1）
 *
 * 預設收合（寬窄螢幕皆然）；展開後顯示本頁目前讀取段的紀錄、反問、工作項清單與輸入列，與入口頁同一套
 * 元件。送出帶本頁 page（由連線決定）。子頁面既有的設計對話與流程不動（`AC8.1.4`）。
 */
export const SubpageBrainPanel: React.FC = () => {
  const [expanded, setExpanded] = useState(false);
  const [draft, setDraft] = useState('');
  return (
    <div data-testid="brain-subpage-panel" className="bg-gray-50 border-b border-gray-200 px-4 py-2">
      <button
        type="button"
        data-testid="brain-subpage-panel-toggle"
        aria-expanded={expanded}
        onClick={() => setExpanded((v) => !v)}
        className="text-sm font-semibold text-brand-700"
      >
        {expanded ? '收合「問大腦」' : '問大腦'}
      </button>
      {expanded && (
        <div className="mt-2 flex flex-col gap-2">
          <div className="max-h-72 overflow-y-auto">
            <ConversationView />
          </div>
          <ConnectionNotice />
          <BrainInput value={draft} onChange={setDraft} />
        </div>
      )}
    </div>
  );
};

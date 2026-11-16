import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/auth-context';
import { canSeeMemoryEntry } from '../memory/memoryEntry';
import { ContextBar } from '../components/brain/ContextBar';
import { WorkItemDock } from '../components/brain/WorkItemDock';
import { ConversationView } from '../components/brain/ConversationView';
import { EntryEmptyState } from '../components/brain/EntryEmptyState';
import { ConnectionNotice } from '../components/brain/ConnectionNotice';
import { BrainInput } from '../components/brain/BrainInput';

/**
 * EntryPage — 入口頁（路由 `/`，`K1 view`；`U14 entry-page-ui`）
 *
 * 由 `DefaultRedirect` 在 `isPending` 之後、其他權限之前渲染（`BR91.1`）。使用全站唯一的大腦連線
 * （`BrainConnectionProvider`；部署後追加「全站大腦小助手」，2026-11-15，原為本頁自己持有一條），下掛脈絡列、
 * 常駐區、對話視圖、連線提示與輸入列。與浮動小助手讀寫同一段（共享段），紀錄只有一份；入口頁不顯示小助手。本頁新增的程式不發任何 HTTP 請求
 * （`BR98.5`；4403 時對既有 `/api/auth/me` 的一次 `refreshMe()` 為唯一例外，security-design §六之二）。
 * 交辦、反問、更正與成本卡片全程不導航（`BR96.3`、`NFR11.140`）。
 */
export const EntryPage = () => {
  const { isAuthenticated } = useAuth();
  const [draft, setDraft] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const pick = (text: string) => {
    setDraft(text);
    inputRef.current?.focus();
  };

  return (
    <div data-testid="brain-entry-page" className="flex h-full flex-col bg-gray-50">
      <header className="flex items-center justify-between gap-3 border-b border-gray-200 bg-white px-4 py-3">
        <h1 className="text-xl font-bold tracking-tight text-gray-900">入口</h1>
        {/* INV-3（BR91.5）：與 Sidebar 同一判定，不另寫。 */}
        {canSeeMemoryEntry({ isAuthenticated }) && (
          <Link to="/memory" data-testid="brain-memory-shortcut" className="text-sm font-semibold text-brand-700 hover:underline">
            我的記憶
          </Link>
        )}
      </header>
      <ContextBar sharingToggle={false} />
      <WorkItemDock />
      <main className="flex-1 min-h-0 overflow-y-auto px-4 py-4">
        <div className="mx-auto flex max-w-3xl flex-col gap-3">
          <ConversationView emptyState={<EntryEmptyState onPick={pick} />} />
          <ConnectionNotice />
        </div>
      </main>
      <div className="border-t border-gray-200 bg-white px-4 py-3">
        <div className="mx-auto max-w-3xl">
          <BrainInput value={draft} onChange={setDraft} inputRef={inputRef} />
        </div>
      </div>
    </div>
  );
};

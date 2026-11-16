import React, { useEffect, useId, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useBrainSession } from '../../brain/brainSession';
import { useBrainAssistant } from '../../brain/brainAssistant';
import { isEntryPagePath, pageForPath } from '../../brain/brainRoutePage';
import { BrainInput } from './BrainInput';
import { ConnectionNotice } from './ConnectionNotice';
import { ContextBar } from './ContextBar';
import { ConversationView } from './ConversationView';

/**
 * BrainAssistant — 全站浮動的大腦小助手（部署後追加「全站大腦小助手」，2026-11-15）
 *
 * **範圍揭露**：這是部署後新增的範圍，已核可的 requirements 與 user-stories 都沒有涵蓋；它**取代**
 * `[EP1]`=A 的「子頁面收合的『問大腦』面板」（`SubpageBrainPanel`，已刪除）的形式。工作區與評估頁既有的
 * 設計／評核對話區不動（`[EP1]` 的前提仍成立）。回補項見
 * `aidlc/spaces/default/intents/260920-orchestration-brain/operation/followups/global-brain-assistant.md`。
 *
 * - 掛在 `Layout`（全站每一頁）；只在使用者有 `K1 view`（`conn.enabled`）時顯示；入口頁本身就是整頁對話，不顯示。
 * - 收合時只有右下角一個按鈕（`aria-label` 可辨識；收合期間有新回覆時帶未讀提示）。
 * - 展開時是非強制回應的對話窗：窗頂是同一條作業對象列（含「切換對象」），下面是與入口頁同一套的
 *   `ConversationView`（含反問候選與工作項）、連線提示與輸入列。讀寫的是目前頁的讀取段（工作區／評估頁在
 *   獨立模式下讀自己的段，其餘頁讀共享段，與入口頁同一段，不另存一份紀錄）。
 * - 可按關閉或 Esc 關閉；開啟時焦點移到輸入框，關閉時回到按鈕。窄螢幕（< 768px）全螢幕。
 * - 展開狀態與草稿存在路由外層（`BrainConnectionProvider`），換頁保留；不寫 localStorage。
 * - 工作區的 draw.io 畫布（`ui=min`）右下角有一條狀態列，右端是縮放比例選單；實測（1280×720、1440×900）
 *   按鈕放在 `bottom-4` 會正好蓋住它。工作區改為 `bottom-24`、對話窗跟著上移，避開畫布右下角的縮放控件。
 */
export const BrainAssistant: React.FC = () => {
  const conn = useBrainSession();
  const { open, setOpen, draft, setDraft, unread } = useBrainAssistant();
  const { pathname } = useLocation();
  const titleId = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const windowRef = useRef<HTMLDivElement>(null);
  /**
   * 只有使用者按下開啟／關閉時才移焦點：換頁後小助手重掛而仍是展開的，不搶走頁面的焦點。焦點在 commit 之後
   * 才移（窄螢幕展開時按鈕是隱藏的，關閉的同一個事件裡還無法聚焦）。
   */
  const focusRequestRef = useRef<'input' | 'button' | null>(null);

  const visible = conn.enabled && !isEntryPagePath(pathname);
  const aboveCanvasControls = pageForPath(pathname) === 'workspace';

  useEffect(() => {
    const request = focusRequestRef.current;
    focusRequestRef.current = null;
    if (request === 'button' && !open) {
      buttonRef.current?.focus();
      return;
    }
    if (request !== 'input' || !open) return;
    // 連線未就緒時輸入框停用、無法取得焦點：改落在對話窗本身（tabIndex=-1），鍵盤使用者仍在窗內。
    const input = inputRef.current;
    if (input && !input.disabled) input.focus();
    else windowRef.current?.focus();
  }, [open]);

  if (!visible) return null;

  const openWindow = () => {
    focusRequestRef.current = 'input';
    setOpen(true);
  };

  const closeWindow = () => {
    focusRequestRef.current = 'button';
    setOpen(false);
  };

  const label = open ? '收合大腦小助手' : unread ? '開啟大腦小助手（有新回覆）' : '開啟大腦小助手';

  return (
    <>
      {open && (
        <div
          ref={windowRef}
          role="dialog"
          aria-modal="false"
          aria-labelledby={titleId}
          tabIndex={-1}
          data-testid="brain-assistant-window"
          onKeyDown={(e) => {
            // 窗內元件（作業對象選單）自行處理 Escape 並停止傳遞；走到這裡的 Escape 才關閉小助手。
            if (e.key === 'Escape' && !e.defaultPrevented) {
              e.preventDefault();
              closeWindow();
            }
          }}
          className={`fixed inset-0 z-40 flex flex-col overflow-hidden bg-white shadow-2xl focus:outline-none md:inset-auto md:right-4 md:w-[26rem] md:rounded-2xl md:border md:border-gray-200 ${
            aboveCanvasControls
              ? 'md:bottom-44 md:h-[min(36rem,calc(100vh-12rem))]'
              : 'md:bottom-20 md:h-[min(36rem,calc(100vh-7rem))]'
          }`}
        >
          <div className="flex items-center justify-between gap-2 border-b border-gray-200 px-4 py-2">
            <h2 id={titleId} className="text-sm font-bold text-gray-900">
              大腦小助手
            </h2>
            <button
              type="button"
              data-testid="brain-assistant-close"
              aria-label="關閉大腦小助手"
              onClick={closeWindow}
              className="rounded-lg px-2 py-1 text-sm font-semibold text-gray-600 hover:bg-gray-100"
            >
              關閉
            </button>
          </div>
          <ContextBar sharingToggle={false} testIdPrefix="brain-assistant-context" regionLabel="小助手的作業對象" />
          <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3">
            <ConversationView />
          </div>
          <div className="flex flex-col gap-2 border-t border-gray-200 px-4 py-3">
            <ConnectionNotice />
            <BrainInput value={draft} onChange={setDraft} inputRef={inputRef} />
          </div>
        </div>
      )}
      <button
        ref={buttonRef}
        type="button"
        data-testid="brain-assistant-toggle"
        data-unread={unread ? 'true' : 'false'}
        aria-label={label}
        aria-expanded={open}
        onClick={() => (open ? closeWindow() : openWindow())}
        onKeyDown={(e) => {
          if (e.key === 'Escape' && open) {
            e.preventDefault();
            closeWindow();
          }
        }}
        data-placement={aboveCanvasControls ? 'above-canvas-controls' : 'corner'}
        className={`fixed ${aboveCanvasControls ? 'bottom-24' : 'bottom-4'} right-4 z-40 h-14 w-14 items-center justify-center rounded-full bg-brand-600 text-white shadow-lg hover:bg-brand-700 focus:outline-none focus-visible:ring-4 focus-visible:ring-brand-300 ${
          open ? 'hidden md:flex' : 'flex'
        }`}
      >
        <span aria-hidden="true" className="text-sm font-bold">
          {open ? '×' : '大腦'}
        </span>
        {unread && (
          <span
            data-testid="brain-assistant-unread"
            aria-hidden="true"
            className="absolute -right-0.5 -top-0.5 h-3.5 w-3.5 rounded-full border-2 border-white bg-red-500"
          />
        )}
      </button>
    </>
  );
};

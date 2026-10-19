import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useBrainSession } from '../../brain/brainSession';
import { TARGET_NONE, layerName } from '../../brain/brainProtocol';
import { ObjectPicker, type PickerPlacement } from './ObjectPicker';
import { PICKER_WIDTH_PX } from '../../brain/objectPickerModel';

type BarState = 'connecting' | 'no-object' | 'default' | 'independent' | 'unavailable';
type PickerAnchor = PickerPlacement;

const UNAVAILABLE_TEXT: Record<string, string> = {
  'gave-up': '無法連線到大腦',
  'needs-login': '連線已失效，請重新登入',
  forbidden: '你目前沒有使用大腦的權限',
  'version-mismatch': '版本不相容，請重新整理頁面',
};

/**
 * ContextBar — 脈絡列（`BR97.1`–`BR97.3`、`NFR2.140`）
 *
 * `data-state` 五態（connecting／no-object／default／independent／unavailable）與三個名稱節點的
 * `data-id`（識別碼字串；識別碼為 null 時該層不渲染）供 e2e 逐欄比對。名稱為 `""` 顯示「（未命名）」、
 * 識別碼有而名稱為 null 顯示「（無法顯示名稱）」。徽章與段切換只在伺服器回推 `sharing_mode` 後改變
 * （不樂觀更新，`BR97.3`）。
 *
 * 「切換對象」鈕與選單由 `U16 object-picker-ui` 實作（見 `ObjectPicker.tsx`）：鈕只在連線 `ready` 時渲染；
 * 選單以衍生值 `pickerVisible = pickerOpen && status === 'ready'` 掛載，連線離開 `ready` 時同一次渲染即卸載，
 * 並以「依前值調整 state」清掉 `pickerOpen`（重連後不會自己冒出來），焦點移到本區塊、頁面 `LiveRegion` 播報
 * 一次（`functional-spec-corrections.md` F-02、`nfr-design-corrections.md` D-05）。五態判定與名稱節點不受影響。
 */
export const ContextBar: React.FC<{ sharingToggle: boolean }> = ({ sharingToggle }) => {
  const conn = useBrainSession();
  const [expanded, setExpanded] = useState(false);
  const { target, status, sharingMode, announce } = conn;
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerAnchor, setPickerAnchor] = useState<PickerAnchor>({ top: 0, left: 0, maxHeight: 400 });
  const [prevStatus, setPrevStatus] = useState(status);
  const sectionRef = useRef<HTMLElement>(null);
  const switchRef = useRef<HTMLButtonElement>(null);
  const wasVisibleRef = useRef(false);

  // U16（F-02、D-05）：依前值調整 state——連線離開 ready 時清掉 pickerOpen，避免重連後選單自己出現。
  if (prevStatus !== status) {
    setPrevStatus(status);
    if (status !== 'ready' && pickerOpen) setPickerOpen(false);
  }
  const pickerVisible = pickerOpen && status === 'ready';

  // U16（F-02）：選單原本可見、因斷線而關閉時，焦點移到本區塊並播報一次。先清空再於下一個任務送文字，
  // 使連續兩次斷線的相同字串仍會改變 LiveRegion（D-05）。
  useEffect(() => {
    const wasVisible = wasVisibleRef.current;
    wasVisibleRef.current = pickerVisible;
    if (!wasVisible || pickerVisible || status === 'ready') return;
    sectionRef.current?.focus();
    announce('');
    // 不在 cleanup 清除計時器：斷線後 status 會連續變化（reconnecting → connecting …），清除會吞掉這次播報。
    window.setTimeout(() => announce('連線中斷，已關閉作業對象選單'), 0);
  }, [pickerVisible, status, announce]);

  // 選單以 fixed 定位錨在鈕下方：/assessment 的脈絡列外層是 overflow-hidden（AssessmentPage.tsx），
  // absolute 定位會被裁切。座標在點擊當下（事件處理函式內）量測，不在 effect 內 setState。
  // 量測只做一次：開啟期間鈕因捲動移位或視窗尺寸改變時，選單自行關閉（ObjectPicker 的監聽，review-01 R-05），
  // 不做重定位。寬度只有一個定義處 PICKER_WIDTH_PX。
  const togglePicker = () => {
    if (pickerOpen) {
      setPickerOpen(false);
      return;
    }
    const rect = switchRef.current?.getBoundingClientRect();
    const top = Math.round((rect?.bottom ?? 0) + 4);
    const left = Math.round(Math.max(16, Math.min(rect?.left ?? 16, window.innerWidth - PICKER_WIDTH_PX - 16)));
    setPickerAnchor({ top, left, maxHeight: Math.max(240, window.innerHeight - top - 16) });
    setPickerOpen(true);
  };

  const closePicker = useCallback(() => {
    setPickerOpen(false);
    switchRef.current?.focus();
  }, []);

  const unavailableText = UNAVAILABLE_TEXT[status];
  const layers = [
    { key: 'project', label: '專案', id: target?.projectId ?? null, name: layerName(target?.projectId ?? null, target?.projectName ?? null) },
    { key: 'system', label: '系統', id: target?.systemId ?? null, name: layerName(target?.systemId ?? null, target?.systemName ?? null) },
    { key: 'diagram', label: '架構圖', id: target?.diagramId ?? null, name: layerName(target?.diagramId ?? null, target?.diagramName ?? null) },
  ];
  const visible = layers.filter((l) => l.id !== null);

  let state: BarState;
  if (unavailableText) state = 'unavailable';
  else if (status !== 'ready') state = 'connecting';
  else if (sharingToggle && sharingMode === 'isolated') state = 'independent';
  else if (visible.length === 0) state = 'no-object';
  else state = 'default';

  return (
    <section
      ref={sectionRef}
      tabIndex={-1}
      role="region"
      aria-label="目前作業對象"
      data-testid="brain-context-bar"
      data-state={state}
      className="bg-white border-b border-gray-200 px-4 py-2 text-sm focus:outline-none"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-gray-500 shrink-0">作業對象</span>
        {state === 'connecting' && (
          <span className="inline-block h-4 w-40 rounded bg-gray-100 animate-pulse motion-reduce:animate-none" role="img" aria-label="連線中" />
        )}
        {state === 'unavailable' && <span className="text-red-600">無法載入作業對象（{unavailableText}）</span>}
        {(state === 'default' || state === 'independent' || state === 'no-object') && (
          <span className="flex flex-wrap items-center gap-1 text-gray-900 break-all">
            {visible.length === 0 ? (
              <span data-testid="brain-context-none">{TARGET_NONE}</span>
            ) : (
              visible.map((l, i) => (
                <React.Fragment key={l.key}>
                  {i > 0 && <span className="text-gray-400">/</span>}
                  <span data-testid={`brain-context-name-${l.key}`} data-id={l.id ?? undefined} className="font-medium">
                    {l.name}
                  </span>
                </React.Fragment>
              ))
            )}
          </span>
        )}
        {status === 'ready' && (
          <div>
            <button
              ref={switchRef}
              type="button"
              data-testid="brain-context-switch-object"
              aria-haspopup="dialog"
              aria-expanded={pickerVisible}
              onClick={togglePicker}
              className="text-xs font-semibold text-brand-700 hover:underline"
            >
              切換對象
            </button>
            {pickerVisible && <ObjectPicker onClose={closePicker} anchorRef={switchRef} anchor={pickerAnchor} />}
          </div>
        )}
        {sharingToggle && status === 'ready' && (
          <>
            <span
              data-testid="brain-context-sharing-badge"
              className={`ml-2 px-2 py-0.5 rounded-full text-xs font-bold border ${
                sharingMode === 'isolated' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-brand-50 text-brand-700 border-brand-200'
              }`}
            >
              {sharingMode === 'isolated' ? '獨立' : '共享'}
            </span>
            <button
              type="button"
              data-testid="brain-context-sharing-switch"
              onClick={() => conn.setSharingMode(sharingMode === 'isolated' ? 'shared' : 'isolated')}
              className="text-xs font-semibold text-brand-700 hover:underline"
            >
              {sharingMode === 'isolated' ? '切回共享對話' : '改為獨立對話'}
            </button>
          </>
        )}
        <button
          type="button"
          data-testid="brain-context-toggle"
          aria-expanded={expanded}
          onClick={() => setExpanded((v) => !v)}
          className="ml-auto text-xs text-gray-500 hover:text-gray-800"
        >
          {expanded ? '收合' : '詳細'}
        </button>
      </div>
      {expanded && (
        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs text-gray-600">
          {layers.map((l) => (
            <React.Fragment key={l.key}>
              <dt className="font-semibold">{l.label}</dt>
              <dd className="break-all">{l.name ?? '—'}</dd>
            </React.Fragment>
          ))}
        </dl>
      )}
    </section>
  );
};

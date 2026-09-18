import {
  useEffect,
  useRef,
  useState,
  forwardRef,
  useImperativeHandle,
  type ReactNode,
} from 'react';
import { downloadDrawioFile } from '../utils/downloadDrawio';

export type DiagramSaveStatus = 'saved' | 'unsaved' | 'saving' | 'no-file';

interface DrawioCanvasProps {
  xml: string;
  /** 架構圖標題（下載檔名等） */
  diagramTitle?: string;
  /** 儲存狀態徽章（修正先前寫死「未儲存」） */
  saveStatus?: DiagramSaveStatus;
  /** 僅檢視／審核：禁止操作畫布與儲存 */
  readOnly?: boolean;
  /** 外層版面寬度變更時遞增，觸發 draw.io iframe 重新適配 */
  layoutEpoch?: number;
  /** 標題列正中央插槽（例如歷史架構圖選單），避免浮層擋住標題 */
  headerCenter?: ReactNode;
  /** 標題列下方提示條（例如僅檢視橫幅） */
  headerBanner?: ReactNode;
  onLoadComplete?: () => void;
  onAutosave?: (xml: string) => void;
  onSaveClick?: (xml: string) => void;
  /** embed exit：髒資料確認後由父層展開 Sidebar、留在 Workspace */
  onExit?: () => void;
  onShareClick?: () => void;
  /** 有審核權時顯示（功能 stub） */
  onReviewClick?: () => void;
}

export interface DrawioCanvasRef {
  mergeXml: (xml: string) => void;
}

const SAVE_BADGE: Record<
  DiagramSaveStatus,
  { label: string; className: string }
> = {
  saved: {
    label: '已儲存',
    className: 'bg-emerald-50 text-emerald-700 border-emerald-200/60',
  },
  unsaved: {
    label: '未儲存',
    className: 'bg-amber-50 text-amber-600 border-amber-200/50',
  },
  saving: {
    label: '儲存中…',
    className: 'bg-sky-50 text-sky-700 border-sky-200/50',
  },
  'no-file': {
    label: '尚未建檔',
    className: 'bg-amber-50 text-amber-600 border-amber-200/50',
  },
};

export const DrawioCanvas = forwardRef<DrawioCanvasRef, DrawioCanvasProps>(
  (
    {
      xml,
      diagramTitle = '未命名架構圖',
      saveStatus = 'unsaved',
      readOnly = false,
      layoutEpoch = 0,
      headerCenter,
      headerBanner,
      onLoadComplete,
      onAutosave,
      onSaveClick,
      onExit,
      onShareClick,
      onReviewClick,
    },
    ref
  ) => {
    const iframeRef = useRef<HTMLIFrameElement>(null);
    const [isReady, setIsReady] = useState(false);
    /** 畫布目前 XML；autosave 回寫父層時若 xml prop 與此相同則不可 action:load */
    const latestXmlRef = useRef<string>(xml);
    const onAutosaveRef = useRef(onAutosave);
    const onSaveClickRef = useRef(onSaveClick);
    const onExitRef = useRef(onExit);
    const onLoadCompleteRef = useRef(onLoadComplete);
    const badge = SAVE_BADGE[saveStatus];

    useEffect(() => {
      onAutosaveRef.current = onAutosave;
    }, [onAutosave]);
    useEffect(() => {
      onSaveClickRef.current = onSaveClick;
    }, [onSaveClick]);
    useEffect(() => {
      onExitRef.current = onExit;
    }, [onExit]);
    useEffect(() => {
      onLoadCompleteRef.current = onLoadComplete;
    }, [onLoadComplete]);

    const postLoad = (nextXml: string) => {
      if (!iframeRef.current?.contentWindow) return;
      iframeRef.current.contentWindow.postMessage(
        JSON.stringify({
          action: 'load',
          autosave: 1,
          xml: nextXml,
        }),
        '*'
      );
      latestXmlRef.current = nextXml;
      onLoadCompleteRef.current?.();
    };

    const handleDownloadDrawio = () => {
      const current = latestXmlRef.current || xml;
      try {
        downloadDrawioFile(current, diagramTitle);
      } catch {
        // 無圖時不下載
      }
    };

    // 對話／側欄收合後，通知 embed 重新計算畫布尺寸
    useEffect(() => {
      if (!isReady || !iframeRef.current || layoutEpoch <= 0) return;
      window.dispatchEvent(new Event('resize'));
      try {
        iframeRef.current.contentWindow?.postMessage(
          JSON.stringify({ action: 'status', messageKey: 'resize', modified: false }),
          '*'
        );
      } catch {
        /* ignore */
      }
    }, [layoutEpoch, isReady]);

    useImperativeHandle(
      ref,
      () => ({
        mergeXml: (mergeData: string) => {
          if (iframeRef.current && isReady) {
            iframeRef.current.contentWindow?.postMessage(
              JSON.stringify({ action: 'merge', xml: mergeData }),
              '*'
            );
            // merge 後以合併結果為最新；父層接著 setXml 時勿再無謂 load
            latestXmlRef.current = mergeData;
          }
        },
      }),
      [isReady]
    );

    // 僅在真實外部換圖時 load（避免 autosave echo 清空 Undo）
    useEffect(() => {
      if (!isReady || !iframeRef.current || !xml) return;
      if (xml === latestXmlRef.current) return;
      postLoad(xml);
    }, [xml, isReady]);

    useEffect(() => {
      const handleMessage = (event: MessageEvent) => {
        if (!event.origin.includes('diagrams.net')) return;
        if (!iframeRef.current || event.source !== iframeRef.current.contentWindow)
          return;

        try {
          const data =
            typeof event.data === 'string' ? JSON.parse(event.data) : event.data;

          if (data.event === 'init') {
            setIsReady(true);
            if (xml) {
              postLoad(xml);
            }
          } else if (data.event === 'autosave' && data.xml) {
            latestXmlRef.current = data.xml;
            onAutosaveRef.current?.(data.xml);
          } else if (data.event === 'save') {
            const savedXml =
              (typeof data.xml === 'string' && data.xml) || latestXmlRef.current;
            if (savedXml) {
              latestXmlRef.current = savedXml;
            }
            onSaveClickRef.current?.(savedXml);
          } else if (data.event === 'exit') {
            onExitRef.current?.();
          }
        } catch {
          // 忽略非 JSON 的訊息
        }
      };

      window.addEventListener('message', handleMessage);
      return () => {
        window.removeEventListener('message', handleMessage);
      };
    }, [xml]);

    return (
      <div className="flex-1 flex flex-col h-full bg-[#f1f5f9] relative min-w-0">
        <div className="min-h-14 bg-white/80 backdrop-blur-md border-b border-gray-200/60 flex items-center justify-between gap-3 px-6 py-2.5 shrink-0 z-10 shadow-sm">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            {headerCenter}
            <span
              className={`px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase rounded-full border shrink-0 ${badge.className}`}
              title={
                saveStatus === 'saved'
                  ? '已同步至資料庫'
                  : saveStatus === 'saving'
                    ? '正在寫入資料庫…'
                    : saveStatus === 'no-file'
                      ? '產圖後請按「儲存架構圖」建檔'
                      : '有未寫入資料庫的變更'
              }
            >
              {badge.label}
            </span>
          </div>

          <div className="flex items-center justify-end gap-3 shrink-0">
            {onReviewClick && (
              <button
                onClick={onReviewClick}
                className="px-4 py-2.5 bg-violet-50 hover:bg-violet-100 text-violet-700 text-sm font-semibold rounded-xl border border-violet-200/80 transition-all"
                title="審核架構圖"
              >
                審核
              </button>
            )}
            <button
              type="button"
              onClick={handleDownloadDrawio}
              disabled={!xml}
              className="flex items-center gap-1.5 px-3 py-2.5 text-sm font-semibold text-gray-600 hover:text-brand-700 hover:bg-brand-50 rounded-xl border border-gray-200/80 transition-all disabled:opacity-40 disabled:pointer-events-none"
              title="下載為 .drawio 檔（可用 diagrams.net 開啟）"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
              下載 .drawio
            </button>
            {onShareClick && (
              <button
                onClick={onShareClick}
                className="flex items-center justify-center w-10 h-10 text-gray-400 hover:text-brand-600 hover:bg-brand-50 rounded-xl transition-all duration-200"
                title="與團隊分享"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
                  />
                </svg>
              </button>
            )}
            {onSaveClick && (
              <>
                <div className="w-px h-6 bg-gray-200 mx-2"></div>
                <button
                  onClick={() => onSaveClick(latestXmlRef.current)}
                  className="px-5 py-2.5 bg-gray-900 hover:bg-black text-white text-sm font-semibold rounded-xl shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300"
                >
                  儲存架構圖
                </button>
              </>
            )}
            {readOnly && !onReviewClick && (
              <span className="px-3 py-1.5 text-xs font-bold text-slate-500 bg-slate-100 rounded-xl border border-slate-200">
                唯讀
              </span>
            )}
          </div>
        </div>
        {headerBanner}

        <div className="flex-1 p-8 overflow-hidden">
          <div className="w-full h-full bg-white rounded-3xl shadow-[0_12px_60px_-15px_rgba(0,0,0,0.05)] border border-gray-200/50 overflow-hidden relative group">
            <div
              className={`absolute inset-0 flex items-center justify-center bg-gray-50/90 backdrop-blur-sm flex-col gap-6 z-20 transition-all duration-500 ${xml ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
            >
              <div className="relative">
                <div className="absolute inset-0 bg-brand-200 rounded-full blur-xl opacity-50 animate-pulse"></div>
                <div className="w-20 h-20 bg-white rounded-3xl shadow-lg border border-gray-100 flex items-center justify-center relative z-10">
                  <svg
                    className="w-10 h-10 text-brand-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  </svg>
                </div>
              </div>
              <p className="text-gray-500 font-medium text-sm tracking-wide">
                請在左側輸入需求以生成架構草圖
              </p>
            </div>

            <iframe
              ref={iframeRef}
              className={`w-full h-full border-0 absolute inset-0 z-10 ${readOnly ? 'pointer-events-none' : ''}`}
              src="https://embed.diagrams.net/?embed=1&ui=min&spin=1&modified=unsaved&proto=json&libraries=1"
              title="draw.io diagram"
            />
            {readOnly && xml && (
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30 px-3 py-1.5 rounded-full bg-slate-900/70 text-white text-[11px] font-semibold pointer-events-none">
                唯讀預覽（無法編輯畫布）
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }
);

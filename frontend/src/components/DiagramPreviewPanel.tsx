import { useMemo } from 'react';
import { buildDiagramViewerUrl } from '../utils/diagramViewer';

type Props = {
  xml: string | null;
  title?: string;
  /** 較矮的預覽列高度 */
  heightClass?: string;
  emptyHint?: string;
};

/**
 * 評估儀表板用：以 diagrams.net viewer 唯讀預覽架構圖。
 */
export function DiagramPreviewPanel({
  xml,
  title = '架構圖預覽',
  heightClass = 'h-64',
  emptyHint = '選擇或上傳架構圖後，將在此預覽',
}: Props) {
  const src = useMemo(() => {
    if (!xml?.trim()) return null;
    try {
      return buildDiagramViewerUrl(xml, title);
    } catch {
      return null;
    }
  }, [xml, title]);

  if (!src) {
    return (
      <div
        className={`${heightClass} rounded-2xl border border-dashed border-gray-200 bg-gray-50 flex items-center justify-center px-4`}
      >
        <p className="text-sm text-gray-400 text-center">{emptyHint}</p>
      </div>
    );
  }

  return (
    <div className={`${heightClass} rounded-2xl border border-gray-200 overflow-hidden bg-white shadow-sm relative`}>
      <div className="absolute top-2 left-3 z-10 px-2 py-0.5 rounded-md bg-white/90 border border-gray-100 text-[10px] font-bold text-gray-500">
        架構圖預覽
      </div>
      <iframe
        title={title}
        src={src}
        className="w-full h-full border-0"
        sandbox="allow-scripts allow-same-origin allow-popups"
      />
    </div>
  );
}

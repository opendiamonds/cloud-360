/**
 * 以 diagrams.net embed + postMessage 在瀏覽器內匯出 PNG（不依賴後端轉圖 API）。
 */
import { ensureMxfile } from './diagramViewer';

export function exportDiagramToPngDataUrl(
  xml: string,
  opts?: { timeoutMs?: number; width?: number; height?: number }
): Promise<string> {
  const timeoutMs = opts?.timeoutMs ?? 60000;
  const width = opts?.width ?? 960;
  const height = opts?.height ?? 720;
  const wrapped = ensureMxfile(xml);

  return new Promise((resolve, reject) => {
    const iframe = document.createElement('iframe');
    iframe.setAttribute('title', 'drawio-export');
    iframe.style.cssText = `position:fixed;left:-10000px;top:0;width:${width}px;height:${height}px;opacity:0;pointer-events:none;border:0`;
    iframe.src =
      'https://embed.diagrams.net/?embed=1&proto=json&spin=1&ui=min&libraries=0&configure=0';
    document.body.appendChild(iframe);

    let settled = false;
    let loadSent = false;
    let exportSent = false;

    const cleanup = () => {
      window.clearTimeout(timer);
      window.removeEventListener('message', onMessage);
      iframe.remove();
    };

    const fail = (err: Error) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(err);
    };

    const ok = (dataUrl: string) => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(dataUrl);
    };

    const timer = window.setTimeout(
      () => fail(new Error('架構圖匯出逾時')),
      timeoutMs
    );

    const post = (payload: Record<string, unknown>) => {
      iframe.contentWindow?.postMessage(JSON.stringify(payload), '*');
    };

    const onMessage = (evt: MessageEvent) => {
      if (evt.source !== iframe.contentWindow) return;
      let msg: Record<string, unknown>;
      try {
        msg =
          typeof evt.data === 'string'
            ? (JSON.parse(evt.data) as Record<string, unknown>)
            : (evt.data as Record<string, unknown>);
      } catch {
        return;
      }
      const event = String(msg.event || '');
      if (event === 'init' && !loadSent) {
        loadSent = true;
        post({
          action: 'load',
          xml: wrapped,
          autosave: 0,
        });
        return;
      }
      if ((event === 'load' || event === 'configure') && loadSent && !exportSent) {
        exportSent = true;
        // 稍等一幀讓圖載入完成再 export
        window.setTimeout(() => {
          post({
            action: 'export',
            format: 'png',
            spin: 'Exporting',
            embedImages: 1,
            scale: 2,
            border: 10,
          });
        }, 400);
        return;
      }
      if (event === 'export') {
        const data = msg.data;
        if (typeof data === 'string' && data.length > 0) {
          ok(data.startsWith('data:') ? data : `data:image/png;base64,${data}`);
        } else {
          fail(new Error('架構圖匯出結果為空'));
        }
      }
    };

    window.addEventListener('message', onMessage);
    iframe.onerror = () => fail(new Error('無法載入 diagrams.net embed'));
  });
}

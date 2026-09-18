/**
 * draw.io 預覽／匯出輔助：viewer URL、mxfile 包裝。
 */

export function ensureMxfile(xml: string, title = 'Diagram'): string {
  const raw = (xml || '').trim();
  if (!raw) return '';
  if (/<mxfile[\s>]/i.test(raw)) return raw;
  const page = title
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  const inner = /<mxGraphModel[\s>]/i.test(raw)
    ? raw
    : `<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>${raw}</root></mxGraphModel>`;
  return `<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="Cloud-360" modified="${new Date().toISOString()}" agent="Cloud-360" version="22.1.0" type="device">
  <diagram id="preview-1" name="${page}">
    ${inner}
  </diagram>
</mxfile>`;
}

/** diagrams.net lightbox viewer（唯讀預覽） */
export function buildDiagramViewerUrl(xml: string, title = '架構圖預覽'): string {
  const wrapped = ensureMxfile(xml, title);
  const params = new URLSearchParams({
    lightbox: '1',
    highlight: '0000ff',
    layers: '1',
    nav: '1',
    chrome: '0',
    title,
  });
  return `https://viewer.diagrams.net/?${params.toString()}#R${encodeURIComponent(wrapped)}`;
}

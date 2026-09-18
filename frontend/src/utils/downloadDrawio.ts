/**
 * 將 mxGraph／既有內容包成 diagrams.net 可開啟的 .drawio（mxfile）並觸發下載。
 */
export function downloadDrawioFile(xml: string, title = '架構圖'): void {
  const raw = (xml || '').trim();
  if (!raw) {
    throw new Error('目前沒有可下載的架構圖');
  }

  const safeName = title.replace(/[\\/:*?"<>|]/g, '_').trim() || '架構圖';
  let content = raw;
  if (!/<mxfile[\s>]/i.test(raw)) {
    const pageName = escapeXmlAttr(safeName);
    const inner = /<mxGraphModel[\s>]/i.test(raw)
      ? raw
      : `<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>${raw}</root></mxGraphModel>`;
    content = `<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="Cloud-360" modified="${new Date().toISOString()}" agent="Cloud-360" version="22.1.0" type="device">
  <diagram id="cloud360-1" name="${pageName}">
    ${inner}
  </diagram>
</mxfile>
`;
  }

  const blob = new Blob([content], {
    type: 'application/vnd.jgraph.mxfile',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${safeName}.drawio`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function escapeXmlAttr(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

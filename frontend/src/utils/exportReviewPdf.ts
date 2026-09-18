/**
 * Client-side WA review PDF export (html2canvas + jsPDF).
 * Renders an off-DOM HTML report so CJK text renders correctly as images.
 */
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';

export type PdfFinding = {
  code: string;
  pillar: string;
  severity: string;
  title: string;
  message: string;
  recommendation_hint?: string;
  lens_risk?: string;
};

export type PdfReviewExport = {
  id: number;
  diagramTitle?: string;
  status: string;
  overall_score: number | null;
  created_at?: string | null;
  provider?: string;
  lensName?: string;
  findings_source?: string;
  pillar_scores?: Record<string, number>;
  risk_counts?: {
    HIGH_RISK?: number;
    MEDIUM_RISK?: number;
    NO_RISK?: number;
  };
  findings?: PdfFinding[];
  suggestions_text?: string | null;
  /** data:image/png;base64,... 架構圖預覽（可選） */
  diagramImageDataUrl?: string | null;
};

const PILLAR_LABELS: Record<string, string> = {
  operational_excellence: 'Operational Excellence',
  security: 'Security',
  reliability: 'Reliability',
  performance_efficiency: 'Performance Efficiency',
  cost_optimization: 'Cost Optimization',
};

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Inline: **bold**, *italic*, `code` — after escape. */
function inlineHtml(text: string): string {
  const escaped = escapeHtml(text);
  return escaped
    .replace(/\*\*([^*]+)\*\*/g, '<strong style="font-weight:700;color:#111827">$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, '$1<em style="font-style:italic">$2</em>')
    .replace(
      /`([^`]+)`/g,
      '<code style="background:#f3f4f6;padding:1px 4px;border-radius:4px;font-size:12px;font-family:ui-monospace,monospace;color:#1e40af">$1</code>'
    );
}

type MdBlock =
  | { type: 'h'; level: number; text: string }
  | { type: 'p'; text: string }
  | { type: 'quote'; text: string }
  | { type: 'ul'; items: string[] }
  | { type: 'ol'; items: string[] }
  | { type: 'hr' };

function parseMdBlocks(src: string): MdBlock[] {
  const lines = src.replace(/\r\n/g, '\n').split('\n');
  const blocks: MdBlock[] = [];
  let i = 0;
  while (i < lines.length) {
    const trimmed = lines[i].trim();
    if (!trimmed) {
      i += 1;
      continue;
    }
    if (/^---+$/.test(trimmed) || /^\*\*\*+$/.test(trimmed)) {
      blocks.push({ type: 'hr' });
      i += 1;
      continue;
    }
    const h = /^(#{1,4})\s+(.+)$/.exec(trimmed);
    if (h) {
      blocks.push({ type: 'h', level: h[1].length, text: h[2].trim() });
      i += 1;
      continue;
    }
    if (trimmed.startsWith('>')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ''));
        i += 1;
      }
      blocks.push({ type: 'quote', text: quoteLines.join(' ') });
      continue;
    }
    if (/^[-*]\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ''));
        i += 1;
      }
      blocks.push({ type: 'ul', items });
      continue;
    }
    if (/^\d+\.\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ''));
        i += 1;
      }
      blocks.push({ type: 'ol', items });
      continue;
    }
    const para: string[] = [trimmed];
    i += 1;
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^(#{1,4})\s+/.test(lines[i].trim()) &&
      !/^[-*]\s+/.test(lines[i].trim()) &&
      !/^\d+\.\s+/.test(lines[i].trim()) &&
      !lines[i].trim().startsWith('>') &&
      !/^---+$/.test(lines[i].trim())
    ) {
      para.push(lines[i].trim());
      i += 1;
    }
    blocks.push({ type: 'p', text: para.join(' ') });
  }
  return blocks;
}

/** Convert suggestion markdown to styled HTML (no raw # / ** visible). */
function markdownToStyledHtml(src: string): string {
  const trimmed = src.trim();
  if (!trimmed) {
    return '<p style="color:#9ca3af;font-size:13px">（本次無改善建議文字）</p>';
  }
  const hStyle: Record<number, string> = {
    1: 'margin:16px 0 8px;font-size:16px;font-weight:800;color:#111827',
    2: 'margin:14px 0 6px;font-size:15px;font-weight:800;color:#111827',
    3: 'margin:12px 0 4px;font-size:14px;font-weight:700;color:#1f2937',
    4: 'margin:10px 0 4px;font-size:13px;font-weight:700;color:#374151',
  };
  return parseMdBlocks(trimmed)
    .map((b) => {
      if (b.type === 'h') {
        const tag = `h${Math.min(b.level, 4)}`;
        return `<${tag} style="${hStyle[b.level] || hStyle[3]}">${inlineHtml(b.text)}</${tag}>`;
      }
      if (b.type === 'quote') {
        return `<blockquote style="margin:8px 0;padding:8px 12px;border-left:4px solid #fbbf24;background:#fffbeb;color:#78350f;font-size:12px;border-radius:0 8px 8px 0">${inlineHtml(b.text)}</blockquote>`;
      }
      if (b.type === 'ul') {
        const items = b.items
          .map(
            (it) =>
              `<li style="margin:4px 0">${inlineHtml(it)}</li>`
          )
          .join('');
        return `<ul style="margin:8px 0 8px 1.25rem;padding:0;list-style:disc;font-size:13px;line-height:1.6;color:#374151">${items}</ul>`;
      }
      if (b.type === 'ol') {
        const items = b.items
          .map(
            (it) =>
              `<li style="margin:4px 0">${inlineHtml(it)}</li>`
          )
          .join('');
        return `<ol style="margin:8px 0 8px 1.25rem;padding:0;list-style:decimal;font-size:13px;line-height:1.6;color:#374151">${items}</ol>`;
      }
      if (b.type === 'hr') {
        return '<hr style="border:none;border-top:1px solid #e5e7eb;margin:12px 0"/>';
      }
      return `<p style="margin:6px 0;font-size:13px;line-height:1.65;color:#374151">${inlineHtml(b.text)}</p>`;
    })
    .join('');
}

function buildReportHtml(data: PdfReviewExport): string {
  const pillars = Object.keys(PILLAR_LABELS)
    .map((k) => {
      const v = data.pillar_scores?.[k];
      const score = v != null ? Math.round(v) : '—';
      return `<tr><td>${escapeHtml(PILLAR_LABELS[k])}</td><td style="text-align:right;font-weight:700">${score}</td></tr>`;
    })
    .join('');

  const rc = data.risk_counts || {};
  const findings = (data.findings || [])
    .map(
      (f) => `
      <div style="border:1px solid #e5e7eb;border-radius:8px;padding:10px 12px;margin:8px 0">
        <div style="font-size:11px;color:#6b7280;margin-bottom:4px">
          ${escapeHtml(f.pillar)} · ${escapeHtml(f.lens_risk || f.severity)} · ${escapeHtml(f.code)}
        </div>
        <div style="font-weight:700;color:#111827">${escapeHtml(f.title)}</div>
        <div style="margin-top:4px;color:#374151;font-size:13px">${escapeHtml(f.message)}</div>
        ${
          f.recommendation_hint
            ? `<div style="margin-top:6px;color:#1d4ed8;font-size:12px">提示：${escapeHtml(f.recommendation_hint)}</div>`
            : ''
        }
      </div>`
    )
    .join('');

  const suggestions = markdownToStyledHtml(data.suggestions_text || '');

  const when = data.created_at
    ? new Date(data.created_at).toLocaleString()
    : '—';

  return `
  <div style="width:760px;padding:32px;font-family:system-ui,-apple-system,'Segoe UI','Noto Sans TC','PingFang TC','Microsoft JhengHei',sans-serif;background:#fff;color:#111827">
    <div style="font-size:22px;font-weight:800;letter-spacing:-0.02em">Cloud-360 Well-Architected 評核報告</div>
    <div style="margin-top:8px;font-size:12px;color:#6b7280;line-height:1.6">
      評核 #${data.id}
      · 狀態 ${escapeHtml(data.status)}
      · Provider ${escapeHtml(data.provider || 'aws')}
      · ${escapeHtml(when)}
      ${data.diagramTitle ? `<br/>架構圖：${escapeHtml(data.diagramTitle)}` : ''}
      ${data.lensName ? `<br/>Lens：${escapeHtml(data.lensName)}` : ''}
      ${data.findings_source ? `<br/>發現來源：${escapeHtml(data.findings_source)}` : ''}
    </div>

    <div style="margin-top:24px;display:flex;gap:24px;align-items:flex-end">
      <div>
        <div style="font-size:12px;color:#6b7280;font-weight:600">Lens 總分</div>
        <div style="font-size:40px;font-weight:800;line-height:1">${data.overall_score ?? '—'}</div>
      </div>
      <div style="flex:1">
        <div style="font-size:12px;color:#6b7280;font-weight:600;margin-bottom:6px">RiskCounts</div>
        <div style="display:flex;gap:8px;font-size:12px;font-weight:700">
          <span style="background:#fee2e2;color:#991b1b;padding:6px 10px;border-radius:8px">高風險 ${rc.HIGH_RISK ?? 0}</span>
          <span style="background:#fef3c7;color:#92400e;padding:6px 10px;border-radius:8px">中風險 ${rc.MEDIUM_RISK ?? 0}</span>
          <span style="background:#d1fae5;color:#065f46;padding:6px 10px;border-radius:8px">無風險 ${rc.NO_RISK ?? 0}</span>
        </div>
      </div>
    </div>

    ${
      data.diagramImageDataUrl
        ? `<p style="margin:20px 0 0;font-size:12px;color:#6b7280">架構圖對照頁見下一頁（或報告後附頁）。</p>`
        : ''
    }

    <h2 style="margin:28px 0 10px;font-size:15px;font-weight:800">支柱分數</h2>
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <tbody>${pillars}</tbody>
    </table>

    <h2 style="margin:28px 0 10px;font-size:15px;font-weight:800">發現</h2>
    ${findings || '<div style="color:#9ca3af;font-size:13px">尚無中／高風險發現</div>'}

    <h2 style="margin:28px 0 10px;font-size:15px;font-weight:800">改善建議</h2>
    <div style="font-size:13px;line-height:1.65;color:#374151">${suggestions}</div>

    <div style="margin-top:36px;padding-top:12px;border-top:1px solid #e5e7eb;font-size:10px;color:#9ca3af">
      Generated by Cloud-360 · Offline Custom Lens scoring · Not an official AWS WA Tool export
    </div>
  </div>`;
}

export async function downloadReviewPdf(data: PdfReviewExport): Promise<void> {
  const host = document.createElement('div');
  host.style.position = 'fixed';
  host.style.left = '-10000px';
  host.style.top = '0';
  host.style.zIndex = '-1';
  host.innerHTML = buildReportHtml(data);
  document.body.appendChild(host);

  try {
    const target = host.firstElementChild as HTMLElement;
    const canvas = await html2canvas(target, {
      scale: 2,
      useCORS: true,
      backgroundColor: '#ffffff',
      logging: false,
    });

    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const marginX = 14;
    const marginTop = 16;
    const marginBottom = 16;
    const usableW = pageW - marginX * 2;
    const usableH = pageH - marginTop - marginBottom;

    const fullImgH = (canvas.height * usableW) / canvas.width;
    const pageCount = Math.max(1, Math.ceil(fullImgH / usableH));

    for (let page = 0; page < pageCount; page++) {
      if (page > 0) pdf.addPage();

      const srcY = (page * usableH * canvas.height) / fullImgH;
      const srcH = Math.min(
        (usableH * canvas.height) / fullImgH,
        canvas.height - srcY
      );
      if (srcH <= 0) break;

      const sliceCanvas = document.createElement('canvas');
      sliceCanvas.width = canvas.width;
      sliceCanvas.height = Math.max(1, Math.ceil(srcH));
      const ctx = sliceCanvas.getContext('2d');
      if (!ctx) throw new Error('無法建立 PDF 分頁畫布');
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, sliceCanvas.width, sliceCanvas.height);
      ctx.drawImage(
        canvas,
        0,
        srcY,
        canvas.width,
        srcH,
        0,
        0,
        canvas.width,
        srcH
      );

      const sliceImg = sliceCanvas.toDataURL('image/png');
      const sliceH = (sliceCanvas.height * usableW) / sliceCanvas.width;
      pdf.addImage(sliceImg, 'PNG', marginX, marginTop, usableW, sliceH);
    }

    // 架構圖獨立一頁（標題用 Canvas 畫中文，避免 jsPDF 預設字型亂碼）
    if (data.diagramImageDataUrl) {
      pdf.addPage();
      const maxLabelPx = Math.round((usableW / 25.4) * 96); // mm → css px
      const heading = renderCjkLabel('架構圖（對照）', {
        fontSizePx: 16,
        color: '#111827',
        maxWidthPx: maxLabelPx,
        fontWeight: '800',
      });
      let cursorY = marginTop;
      pdf.addImage(
        heading.dataUrl,
        'PNG',
        marginX,
        cursorY,
        pxToMm(heading.widthPx),
        pxToMm(heading.heightPx)
      );
      cursorY += pxToMm(heading.heightPx) + 2;

      if (data.diagramTitle) {
        const sub = renderCjkLabel(String(data.diagramTitle).slice(0, 80), {
          fontSizePx: 12,
          color: '#6b7280',
          maxWidthPx: maxLabelPx,
          fontWeight: '500',
        });
        pdf.addImage(
          sub.dataUrl,
          'PNG',
          marginX,
          cursorY,
          pxToMm(sub.widthPx),
          pxToMm(sub.heightPx)
        );
        cursorY += pxToMm(sub.heightPx) + 4;
      } else {
        cursorY += 2;
      }

      const img = await loadImage(data.diagramImageDataUrl);
      const maxW = usableW;
      const maxH = pageH - cursorY - marginBottom;
      const ratio = Math.min(maxW / img.width, maxH / img.height, 1);
      const drawW = img.width * ratio;
      const drawH = img.height * ratio;
      const x = marginX + (usableW - drawW) / 2;
      const fmt = data.diagramImageDataUrl.includes('image/jpeg') ? 'JPEG' : 'PNG';
      pdf.addImage(data.diagramImageDataUrl, fmt, x, cursorY, drawW, drawH);
    }

    pdf.save(`cloud360-wa-review-${data.id}.pdf`);
  } finally {
    document.body.removeChild(host);
  }
}

function pxToMm(px: number): number {
  return (px * 25.4) / 96;
}

/** 用瀏覽器 Canvas 畫中文標籤（jsPDF 內建字型不支援 CJK） */
function renderCjkLabel(
  text: string,
  opts: {
    fontSizePx: number;
    color: string;
    maxWidthPx: number;
    fontWeight?: string;
  }
): { dataUrl: string; widthPx: number; heightPx: number } {
  const scale = 2;
  const font = `${opts.fontWeight || '700'} ${opts.fontSizePx * scale}px system-ui,-apple-system,"Segoe UI","Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif`;
  const probe = document.createElement('canvas');
  const probeCtx = probe.getContext('2d');
  if (!probeCtx) {
    return { dataUrl: '', widthPx: 0, heightPx: 0 };
  }
  probeCtx.font = font;
  const measured = Math.ceil(probeCtx.measureText(text).width) + 16;
  const w = Math.max(1, Math.min(opts.maxWidthPx * scale, measured));
  const h = Math.max(1, Math.ceil(opts.fontSizePx * scale * 1.55));
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const ctx = c.getContext('2d');
  if (!ctx) {
    return { dataUrl: '', widthPx: 0, heightPx: 0 };
  }
  ctx.font = font;
  ctx.fillStyle = opts.color;
  ctx.textBaseline = 'top';
  ctx.fillText(text, 4, 4, w - 8);
  return {
    dataUrl: c.toDataURL('image/png'),
    widthPx: w / scale,
    heightPx: h / scale,
  };
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('無法載入架構圖影像'));
    img.src = src;
  });
}

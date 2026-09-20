import { useEffect, useRef, useState } from 'react';
import { apiUrl } from '../../config/api';
import { authHeaders } from './types';

export type AdviceSnapshot = {
  status?: string | null;
  saving_text?: string | null;
  comparison_text?: string | null;
  quality_text?: string | null;
  unavailable_reasons?: Record<string, unknown> | null;
};

type Phase = 'pending' | 'complete' | 'failed';

type Props = {
  estimateSetId: number;
  adviceStatus: string | null | undefined;
};

function reasonText(reasons: Record<string, unknown> | null | undefined, key: string): string | null {
  if (!reasons) return null;
  const v = reasons[key];
  if (v == null) return null;
  if (key === 'timed_out' || v === true || v === 'timed_out') return '產生逾時（超過約 5 分鐘）';
  if (typeof v === 'string' && v.trim()) return v;
  return String(v);
}

function categoryBody(
  text: string | null | undefined,
  reasons: Record<string, unknown> | null | undefined,
  reasonKey: string,
  emptyHint: string
): string {
  if (text && text.trim()) return text.trim();
  const r = reasonText(reasons, reasonKey);
  if (r) return r;
  if (reasons && Object.keys(reasons).length > 0 && reasonKey === 'comparison') {
    const v = reasons[reasonKey];
    if (v != null) return typeof v === 'string' ? v : emptyHint;
  }
  return emptyHint;
}

function formatAdviceParagraphs(text: string): string[] {
  return text
    .replace(/\r\n/g, '\n')
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean);
}

function AdvicePlainText({ text }: { text: string }) {
  const blocks = formatAdviceParagraphs(text);
  if (blocks.length === 0) {
    return <p className="text-gray-500">本期未提供</p>;
  }
  return (
    <div className="space-y-3">
      {blocks.map((block, i) => {
        const lines = block.split('\n').map((l) => l.trim()).filter(Boolean);
        if (lines.length <= 1) {
          return (
            <p key={i} className="leading-relaxed text-gray-800">
              {lines[0] || block}
            </p>
          );
        }
        return (
          <ul key={i} className="space-y-1.5 pl-0">
            {lines.map((line, j) => (
              <li key={j} className="list-none leading-relaxed text-gray-800">
                {line}
              </li>
            ))}
          </ul>
        );
      })}
    </div>
  );
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds} 秒`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m} 分 ${s} 秒`;
}

function progressLabel(content: Record<string, unknown>): string {
  const message =
    typeof content.message === 'string' && content.message.trim()
      ? content.message.trim()
      : '正在分析估價內容';
  const elapsed =
    typeof content.elapsed_seconds === 'number' ? content.elapsed_seconds : null;
  const lines =
    typeof content.line_count === 'number' ? content.line_count : null;
  const parts = [message];
  if (lines != null) parts.push(`（${lines} 筆明細）`);
  if (elapsed != null) parts.push(`· 已進行 ${formatElapsed(elapsed)}`);
  return parts.join(' ');
}

async function readAdviceStream(
  setId: number,
  signal: AbortSignal,
  onProgress: (msg: string) => void,
  onSnapshot: (snap: AdviceSnapshot, terminal: 'complete' | 'failed') => void
): Promise<void> {
  const res = await fetch(apiUrl(`/api/cost/v1/sets/${setId}/advice/stream`), {
    headers: authHeaders(),
    signal,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(typeof data.detail === 'string' ? data.detail : '無法訂閱建議串流');
  }
  const reader = res.body?.getReader();
  if (!reader) throw new Error('瀏覽器不支援串流');
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      let data: Record<string, unknown>;
      try {
        data = JSON.parse(line.slice(6));
      } catch {
        continue;
      }
      const type = String(data.type || '');
      if (type === 'progress' || type === 'heartbeat') {
        const content = data.content;
        if (typeof content === 'string') onProgress(content);
        else if (content && typeof content === 'object') {
          onProgress(progressLabel(content as Record<string, unknown>));
        }
      } else if (type === 'completed') {
        onSnapshot((data.advice as AdviceSnapshot) || {}, 'complete');
        return;
      } else if (type === 'failed' || type === 'timeout') {
        onSnapshot((data.advice as AdviceSnapshot) || {}, 'failed');
        return;
      }
    }
  }
}

async function fetchAdviceSnapshot(setId: number, signal?: AbortSignal): Promise<AdviceSnapshot> {
  const res = await fetch(apiUrl(`/api/cost/v1/sets/${setId}/advice`), {
    headers: authHeaders(),
    signal,
  });
  if (res.status === 404) return { status: 'none' };
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(typeof data.detail === 'string' ? data.detail : '載入建議失敗');
  }
  return (await res.json()) as AdviceSnapshot;
}

export function EstimateAdvicePanel({ estimateSetId, adviceStatus }: Props) {
  const [phase, setPhase] = useState<Phase>('pending');
  const [progress, setProgress] = useState('正在連線並開始分析…');
  const [snap, setSnap] = useState<AdviceSnapshot | null>(null);
  const [error, setError] = useState('');
  const [liveMsg, setLiveMsg] = useState('');
  const abortRef = useRef<AbortController | null>(null);
  const titleId = 'estimate-advice-title';

  const applyTerminal = (s: AdviceSnapshot, terminal: Phase) => {
    setSnap(s);
    setPhase(terminal);
    if (terminal === 'complete') setLiveMsg('建議已產生');
    if (terminal === 'failed') setLiveMsg('建議產生失敗');
  };

  const startStream = (setId: number, signal: AbortSignal) => {
    setPhase('pending');
    setProgress('正在連線並開始分析…');
    setError('');
    setLiveMsg('');
    return readAdviceStream(
      setId,
      signal,
      (msg) => setProgress(msg),
      (s, terminal) => applyTerminal(s, terminal),
    );
  };

  const retry = () => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    const status = adviceStatus || 'none';
    if (status === 'completed' || status === 'failed') {
      fetchAdviceSnapshot(estimateSetId, ac.signal)
        .then((s) => {
          if (ac.signal.aborted) return;
          applyTerminal(
            s,
            s.status === 'failed' || status === 'failed' ? 'failed' : 'complete',
          );
        })
        .catch((e) => {
          if (ac.signal.aborted) return;
          setError(e instanceof Error ? e.message : '建議載入失敗');
          setPhase('failed');
        });
      return;
    }
    startStream(estimateSetId, ac.signal).catch((e) => {
      if (ac.signal.aborted) return;
      setError(e instanceof Error ? e.message : '建議載入失敗');
      setPhase('failed');
    });
  };

  useEffect(() => {
    const ac = new AbortController();
    abortRef.current = ac;
    const status = adviceStatus || 'none';
    // 純抓取函式不含 setState；落地只在 .then／.catch（與 AdminPage 同型）。
    if (status === 'completed' || status === 'failed') {
      fetchAdviceSnapshot(estimateSetId, ac.signal)
        .then((s) => {
          if (ac.signal.aborted) return;
          applyTerminal(
            s,
            s.status === 'failed' || status === 'failed' ? 'failed' : 'complete',
          );
        })
        .catch((e) => {
          if (ac.signal.aborted) return;
          setError(e instanceof Error ? e.message : '建議載入失敗');
          setPhase('failed');
        });
    } else {
      // startStream 含 setState，不可由 effect 同步呼叫；排入 microtask。
      Promise.resolve()
        .then(() => {
          if (ac.signal.aborted) return;
          return startStream(estimateSetId, ac.signal);
        })
        .catch((e) => {
          if (ac.signal.aborted) return;
          setError(e instanceof Error ? e.message : '建議載入失敗');
          setPhase('failed');
        });
    }
    return () => {
      ac.abort();
      if (abortRef.current === ac) abortRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload when set / status changes
  }, [estimateSetId, adviceStatus]);

  const reasons = snap?.unavailable_reasons || null;

  return (
    <section
      data-testid="advice-slot"
      aria-labelledby={titleId}
      className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm space-y-3"
    >
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 id={titleId} className="text-base font-bold text-gray-900">
          AI 建議
        </h2>
        <p className="text-xs text-amber-800">由 AI 產生，請自行核對</p>
      </div>
      <div className="sr-only" aria-live="polite">
        {liveMsg}
      </div>

      {phase === 'pending' && (
        <div data-testid="advice-pending" className="space-y-3">
          <div className="flex items-start gap-3">
            <span
              className="mt-0.5 inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-gray-700"
              aria-hidden
            />
            <div>
              <p className="text-sm font-medium text-gray-800">分析進行中</p>
              <p className="mt-1 text-sm text-gray-600" aria-live="polite">
                {progress}
              </p>
              <p className="mt-1 text-xs text-gray-400">
                通常約 30 秒～2 分鐘；進度會持續更新
              </p>
            </div>
          </div>
          <div className="space-y-2 animate-pulse">
            <div className="h-3 w-3/4 rounded bg-gray-100" />
            <div className="h-3 w-1/2 rounded bg-gray-100" />
            <div className="h-3 w-2/3 rounded bg-gray-100" />
          </div>
        </div>
      )}

      {phase === 'failed' && (
        <div data-testid="advice-failed" className="space-y-3">
          <p className="text-sm text-red-700">
            {error ||
              reasonText(reasons, 'timed_out') ||
              reasonText(reasons, 'llm') ||
              '建議產生失敗'}
          </p>
          <p className="text-xs text-gray-500">
            明細與檢查結果仍可使用。若需再產生建議，請重新上傳估價表（目前後端不會從失敗狀態自動重跑）。
          </p>
          <button
            type="button"
            className="rounded-xl border border-gray-200 bg-white px-3 py-1.5 text-sm font-semibold"
            onClick={retry}
          >
            重試連線
          </button>
        </div>
      )}

      {phase === 'complete' && snap && (
        <div className="space-y-5 text-sm">
          <div data-testid="advice-category-saving">
            <h3 className="mb-2 text-sm font-semibold text-gray-900">省錢建議</h3>
            <AdvicePlainText
              text={categoryBody(snap.saving_text, reasons, 'saving', '本期未提供')}
            />
          </div>
          <div data-testid="advice-category-comparison">
            <h3 className="mb-2 text-sm font-semibold text-gray-900">跨雲比較</h3>
            <AdvicePlainText
              text={categoryBody(
                snap.comparison_text,
                reasons,
                'comparison',
                '本期未提供（或資料不足）'
              )}
            />
          </div>
          <div data-testid="advice-category-quality">
            <h3 className="mb-2 text-sm font-semibold text-gray-900">品質檢查</h3>
            <AdvicePlainText
              text={categoryBody(snap.quality_text, reasons, 'quality', '本期未提供')}
            />
          </div>
        </div>
      )}
    </section>
  );
}

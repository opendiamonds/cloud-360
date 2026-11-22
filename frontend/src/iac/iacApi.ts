import { apiUrl } from '../config/api';
import type {
  DiagramReadiness,
  DraftSummary,
  RewriteResult,
  ScanReport,
  SessionSnapshot,
} from './iacTypes';

/**
 * Client timeouts. Floors are not lowered:
 * D1 generate ≥ 90s; session / rewrite > 2s; download > 5s.
 * Scan waits past the Checkov hard limit (10s) so a finished report is not dropped.
 */
export const IAC_TIMEOUT_MS = {
  generate: 90_000,
  session: 10_000,
  scan: 20_000,
  rewrite: 10_000,
  download: 15_000,
} as const;

export class IacHttpError extends Error {
  readonly status: number;
  readonly code: string;
  readonly reason: string | null;

  constructor(status: number, code: string, reason: string | null = null) {
    super(code);
    this.name = 'IacHttpError';
    this.status = status;
    this.code = code;
    this.reason = reason;
  }
}

export class IacTimeoutError extends Error {
  constructor() {
    super('timeout');
    this.name = 'IacTimeoutError';
  }
}

interface LinkedAbort {
  signal: AbortSignal;
  timedOut: () => boolean;
  dispose: () => void;
}

/** Parent abort stays an abort. Only the timer becomes a timeout. */
function linkAbort(parent: AbortSignal, ms: number): LinkedAbort {
  const controller = new AbortController();
  let timeout = false;
  const timer = setTimeout(() => {
    timeout = true;
    controller.abort();
  }, ms);
  const onParent = () => controller.abort();
  if (parent.aborted) controller.abort();
  else parent.addEventListener('abort', onParent);
  return {
    signal: controller.signal,
    timedOut: () => timeout && !parent.aborted,
    dispose: () => {
      clearTimeout(timer);
      parent.removeEventListener('abort', onParent);
    },
  };
}

function authHeaders(token: string, json: boolean): HeadersInit {
  if (!json) return { Authorization: `Bearer ${token}` };
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

async function errorCode(res: Response): Promise<{ code: string; reason: string | null }> {
  if (res.status === 401) return { code: 'unauthorized', reason: null };
  if (res.status === 403) return { code: 'forbidden', reason: null };
  try {
    const body: unknown = await res.json();
    if (body && typeof body === 'object' && 'error' in body) {
      const error = (body as { error?: { code?: unknown; reason?: unknown } }).error;
      const code = error && typeof error.code === 'string' && error.code ? error.code : 'unknown';
      const reason = error && typeof error.reason === 'string' && error.reason ? error.reason : null;
      return { code, reason };
    }
  } catch {
    return { code: 'unknown', reason: null };
  }
  return { code: 'unknown', reason: null };
}

async function requestJson<T>(
  token: string,
  path: string,
  method: 'GET' | 'POST',
  body: string | undefined,
  timeoutMs: number,
  parent: AbortSignal,
): Promise<T> {
  const linked = linkAbort(parent, timeoutMs);
  try {
    const res = await fetch(apiUrl(path), {
      method,
      headers: authHeaders(token, body !== undefined),
      body,
      signal: linked.signal,
    });
    if (linked.timedOut()) throw new IacTimeoutError();
    if (!res.ok) {
      const detail = await errorCode(res);
      throw new IacHttpError(res.status, detail.code, detail.reason);
    }
    return (await res.json()) as T;
  } catch (err) {
    if (linked.timedOut()) throw new IacTimeoutError();
    throw err;
  } finally {
    linked.dispose();
  }
}

export function getReadiness(token: string, signal: AbortSignal): Promise<DiagramReadiness[]> {
  return requestJson<{ diagrams?: unknown }>(
    token,
    '/api/iac/readiness',
    'GET',
    undefined,
    IAC_TIMEOUT_MS.session,
    signal,
  ).then((body) => {
    if (!Array.isArray(body.diagrams)) return [];
    return body.diagrams.flatMap((item) => {
      if (!item || typeof item !== 'object') return [];
      const row = item as {
        diagram_id?: unknown;
        title?: unknown;
        status?: unknown;
        node_count?: unknown;
      };
      if (typeof row.diagram_id !== 'number') return [];
      if (row.status !== 'ready' && row.status !== 'empty' && row.status !== 'unreadable') return [];
      const title = typeof row.title === 'string' && row.title.trim() ? row.title : '未命名架構圖';
      const nodeCount = typeof row.node_count === 'number' ? row.node_count : 0;
      return [{ diagram_id: row.diagram_id, title, status: row.status, node_count: nodeCount }];
    });
  });
}

export function getSession(
  token: string,
  diagramId: number,
  signal: AbortSignal,
): Promise<SessionSnapshot> {
  const path = `/api/iac/session?diagram_id=${encodeURIComponent(String(diagramId))}`;
  return requestJson(token, path, 'GET', undefined, IAC_TIMEOUT_MS.session, signal);
}

/** The draft is JSON so the files can render before the advice stream starts. */
export async function postGenerate(
  token: string,
  diagramId: number,
  signal: AbortSignal,
): Promise<{ draft: DraftSummary }> {
  const linked = linkAbort(signal, IAC_TIMEOUT_MS.generate);
  try {
    const res = await fetch(apiUrl('/api/iac/generate'), {
      method: 'POST',
      headers: authHeaders(token, true),
      body: JSON.stringify({ diagram_id: diagramId }),
      signal: linked.signal,
    });
    const text = await res.text();
    if (linked.timedOut()) throw new IacTimeoutError();
    if (!res.ok) throw new IacHttpError(res.status, 'generate_failed');
    return JSON.parse(text) as { draft: DraftSummary };
  } catch (err) {
    if (linked.timedOut()) throw new IacTimeoutError();
    throw err;
  } finally {
    linked.dispose();
  }
}

/** Tokens for the draft already stored on this diagram. Failure does not remove that draft. */
export function streamAdvice(
  token: string,
  diagramId: number,
  signal: AbortSignal,
  onText: (text: string) => void,
): Promise<void> {
  return streamSse('/api/iac/advice', token, diagramId, signal, onText);
}

/** Tokens about the latest scan. Failure does not remove the scan result. */
export function streamScanAdvice(
  token: string,
  diagramId: number,
  signal: AbortSignal,
  onText: (text: string) => void,
): Promise<void> {
  return streamSse('/api/iac/scan-advice', token, diagramId, signal, onText);
}

async function streamSse(
  path: string,
  token: string,
  diagramId: number,
  signal: AbortSignal,
  onText: (text: string) => void,
): Promise<void> {
  const linked = linkAbort(signal, 30_000);
  try {
    const res = await fetch(apiUrl(path), {
      method: 'POST',
      headers: {
        ...authHeaders(token, true),
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({ diagram_id: diagramId }),
      signal: linked.signal,
    });
    if (linked.timedOut()) throw new IacTimeoutError();
    if (!res.ok || !res.body) return;
    const reader = res.body.getReader();
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
        try {
          const event = JSON.parse(line.slice(6)) as { type?: string; content?: string; code?: string };
          if (event.type === 'error') throw new IacHttpError(422, event.code || 'generate_failed');
          if (event.type === 'message' && event.content) onText(event.content);
        } catch {
          /* ignore a partial line */
        }
      }
    }
  } catch (err) {
    if (linked.timedOut()) throw new IacTimeoutError();
    throw err;
  } finally {
    linked.dispose();
  }
}

export function postDraftFiles(
  token: string,
  diagramId: number,
  files: { path: string; content: string }[],
  signal: AbortSignal,
): Promise<{ draft: DraftSummary }> {
  return requestJson(
    token,
    '/api/iac/files',
    'POST',
    JSON.stringify({ diagram_id: diagramId, files }),
    IAC_TIMEOUT_MS.session,
    signal,
  );
}

export function postSave(
  token: string,
  diagramId: number,
  signal: AbortSignal,
  advice?: string,
): Promise<{ diagram_id: number; draft_id: string; saved_at: string }> {
  const body: { diagram_id: number; advice?: string } = { diagram_id: diagramId };
  const note = advice?.trim();
  if (note) body.advice = note;
  return requestJson(
    token,
    '/api/iac/save',
    'POST',
    JSON.stringify(body),
    IAC_TIMEOUT_MS.session,
    signal,
  );
}

export function postScan(
  token: string,
  diagramId: number,
  signal: AbortSignal,
): Promise<{ report: ScanReport }> {
  return requestJson(
    token,
    '/api/iac/scan',
    'POST',
    JSON.stringify({ diagram_id: diagramId }),
    IAC_TIMEOUT_MS.scan,
    signal,
  );
}

export function postScanFiles(
  token: string,
  files: { path: string; content: string }[],
  signal: AbortSignal,
): Promise<{ report: ScanReport }> {
  return requestJson(
    token,
    '/api/iac/scan',
    'POST',
    JSON.stringify({ files }),
    IAC_TIMEOUT_MS.scan,
    signal,
  );
}

export function postRewrite(
  token: string,
  diagramId: number,
  signal: AbortSignal,
): Promise<{ rewrite: RewriteResult; draft: DraftSummary }> {
  return requestJson(
    token,
    '/api/iac/secrets/rewrite',
    'POST',
    JSON.stringify({ diagram_id: diagramId }),
    IAC_TIMEOUT_MS.rewrite,
    signal,
  );
}

export async function getDownloadBlob(
  token: string,
  diagramId: number,
  signal: AbortSignal,
): Promise<Blob> {
  const linked = linkAbort(signal, IAC_TIMEOUT_MS.download);
  try {
    const path = `/api/iac/download?diagram_id=${encodeURIComponent(String(diagramId))}`;
    const res = await fetch(apiUrl(path), {
      method: 'GET',
      headers: authHeaders(token, false),
      signal: linked.signal,
    });
    if (linked.timedOut()) throw new IacTimeoutError();
    if (!res.ok) {
      const detail = await errorCode(res);
      throw new IacHttpError(res.status, detail.code, detail.reason);
    }
    return await res.blob();
  } catch (err) {
    if (linked.timedOut()) throw new IacTimeoutError();
    throw err;
  } finally {
    linked.dispose();
  }
}

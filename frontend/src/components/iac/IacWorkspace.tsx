import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../../context/auth-context';
import { createDiagramFromFile, DiagramUploadError } from '../../iac/diagramUpload';
import {
  getDownloadBlob,
  getReadiness,
  getSession,
  IacHttpError,
  IacTimeoutError,
  postDraftFiles,
  postGenerate,
  streamAdvice,
  streamScanAdvice,
  postRewrite,
  postSave,
  postScan,
  postScanFiles,
} from '../../iac/iacApi';
import { mapIacErrorCode } from '../../iac/mapIacErrorCode';
import type {
  DiagramOption,
  DiagramReadiness,
  DraftSummary,
  Finding,
  IacAction,
  IacFileEntry,
  IacStep,
  IacUiError,
  RewriteResult,
  ScanReport,
} from '../../iac/iacTypes';
import { iacNavItem } from '../../iac/iacNav';
import { IacDownloadConfirm } from './IacDownloadConfirm';

const DIAGRAM_STORAGE_KEY = 'iac-diagram-id';

const BUSY_TEXT: Record<Exclude<IacAction, 'session'>, string> = {
  generate: '正在產生 IaC 草稿',
  scan: '正在掃描草稿',
  rewrite: '正在改寫引用',
  download: '正在準備下載',
};

const EXPERIMENTAL = /google_|azurerm_|azapi_/;

type Props = {
  initialDiagramId: number | null;
  diagrams: DiagramOption[];
  onClose: () => void;
  onDiagramCreated: (diagram: DiagramOption) => void;
  initialStep?: IacStep;
};

type BarState = 'idle' | 'run' | 'done' | 'failed';

function useBar(state: BarState): number {
  const [tracked, setTracked] = useState<BarState>('idle');
  const [value, setValue] = useState(0);
  if (tracked !== state) {
    setTracked(state);
    setValue(state === 'run' ? 8 : 0);
  }
  useEffect(() => {
    if (state !== 'run') return;
    const timer = window.setInterval(() => {
      setValue((current) => (current >= 90 ? 90 : Math.min(90, current + Math.max(0.8, (90 - current) * 0.12))));
    }, 200);
    return () => window.clearInterval(timer);
  }, [state]);
  if (state === 'done' || state === 'failed') return 100;
  if (state === 'idle') return 0;
  return value;
}

function barLabel(kind: 'parse' | 'draft', state: BarState): string {
  if (kind === 'parse') {
    if (state === 'run') return '解析中';
    if (state === 'done') return '解析成功';
    if (state === 'failed') return '解析未通過';
    return '解析';
  }
  if (state === 'run') return '正在產生草稿';
  if (state === 'done') return '草稿已完成';
  return '產生草稿';
}

function ProgressMeter({
  label,
  value,
  state,
  testId,
}: {
  label: string;
  value: number;
  state: BarState;
  testId: string;
}) {
  const width = state === 'done' || state === 'failed' ? 100 : Math.max(0, Math.min(100, value));
  const fill = state === 'failed' ? 'bg-amber-500' : state === 'done' ? 'bg-emerald-600' : 'bg-brand-600';
  return (
    <div className="space-y-1">
      <p className="text-xs font-bold text-gray-700">{label}</p>
      <div
        data-testid={testId}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(width)}
        aria-label={label}
        className="h-2 overflow-hidden rounded-full bg-gray-200"
      >
        <div className={`h-full rounded-full transition-[width] duration-200 ${fill}`} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function isAbortError(err: unknown): boolean {
  return err instanceof Error && err.name === 'AbortError';
}

function tokenExpired(token: string): boolean {
  const part = token.split('.')[1];
  if (!part) return false;
  try {
    const payload = JSON.parse(atob(part.replace(/-/g, '+').replace(/_/g, '/'))) as { exp?: unknown };
    return typeof payload.exp === 'number' && payload.exp * 1000 <= Date.now();
  } catch {
    return false;
  }
}

function readinessCopy(status: DiagramReadiness['status']): string {
  if (status === 'unreadable') return '這張圖的內容無法解析，不能產生 IaC。';
  return '這張圖沒有可轉成 IaC 的節點。';
}

function optionLabel(item: DiagramOption, row: DiagramReadiness | undefined): string {
  if (!row || row.status === 'ready') return item.title;
  if (row.status === 'unreadable') return `${item.title}（無法解析）`;
  return `${item.title}（沒有節點）`;
}

function readStoredDiagram(): number | null {
  try {
    const raw = sessionStorage.getItem(DIAGRAM_STORAGE_KEY);
    const id = Number(raw);
    return Number.isInteger(id) && id > 0 ? id : null;
  } catch {
    return null;
  }
}

function rememberDiagram(id: number) {
  try {
    sessionStorage.setItem(DIAGRAM_STORAGE_KEY, String(id));
  } catch {
    /* the selection still applies for this view */
  }
}

function mergeOptions(diagrams: DiagramOption[], diagramId: number | null): DiagramOption[] {
  if (diagramId == null || diagrams.some((item) => item.id === diagramId)) return diagrams;
  return [...diagrams, { id: diagramId, title: `架構圖 #${diagramId}` }];
}

function checkStatusLabel(status: string): string {
  if (status === 'passed') return '通過';
  if (status === 'failed') return '未通過';
  if (status === 'skipped') return '略過';
  return status;
}

function severityCounts(report: ScanReport | null): { high: number; critical: number } {
  if (!report || report.status !== 'succeeded') return { high: 0, critical: 0 };
  const count = (severity: Finding['severity']) =>
    report.findings.filter((item) => item.severity === severity).length;
  const high = count('HIGH');
  const critical = count('CRITICAL');
  if (high + critical > 0) return { high, critical };
  if (report.max_severity === 'HIGH') return { high: 1, critical: 0 };
  if (report.max_severity === 'CRITICAL') return { high: 0, critical: 1 };
  return { high: 0, critical: 0 };
}

const ADVICE_HEADINGS = new Set(['資源摘要', '資源說明', '使用前注意', '注意事項']);

function plainAdviceLines(raw: string): string[] {
  const lines: string[] = [];
  for (const source of raw.replace(/\r\n/g, '\n').split('\n')) {
    if (/^[ \t]*([-*_])\1{2,}[ \t]*$/.test(source)) {
      lines.push('');
      continue;
    }
    const pipeCount = (source.match(/\|/g) ?? []).length;
    if (pipeCount >= 2) {
      const firstPipe = source.indexOf('|');
      const prose = readableLine(source.slice(0, firstPipe));
      if (prose) lines.push(prose);
      lines.push(...tableLabels(source.slice(firstPipe)));
      continue;
    }
    const text = readableLine(source);
    lines.push(text ? text : '');
  }
  return lines;
}

function stripMarkdown(value: string): string {
  return value
    .replace(/!\[[^\]]*]\([^)]*\)/g, '')
    .replace(/\[([^\]]+)]\([^)]*\)/g, '$1')
    .replace(/^[ \t]{0,3}#{1,6}[ \t]*/, '')
    .replace(/^[ \t]*[-*+][ \t]+/, '')
    .replace(/^[ \t]*\d+[.)][ \t]+/, '')
    .replace(/\*\*|__|`/g, '')
    .replace(/^[\p{Extended_Pictographic}\uFE0F\s]+/u, '')
    .replace(/[ \t]+/g, ' ')
    .trim();
}

function readableLine(value: string): string {
  const text = stripMarkdown(value);
  if (!text || ADVICE_HEADINGS.has(text)) return '';
  const splitAt = text.search(/[：:]/);
  if (splitAt > 0 && /[._]/.test(text.slice(0, splitAt))) {
    const label = text
      .slice(splitAt + 1)
      .replace(/^標籤\s*/, '')
      .trim();
    if (label) return label;
  }
  return text;
}

function isHeaderCell(cell: string): boolean {
  return ADVICE_HEADINGS.has(cell) || /^(標籤|說明|名稱|資源識別碼|資源名稱)(\s*[（(][^）)]*[）)])?$/.test(cell);
}

function tableLabels(fragment: string): string[] {
  const cells = fragment
    .split('|')
    .map((cell) => stripMarkdown(cell))
    .filter((cell) => cell && !/^:?-{3,}:?$/.test(cell));
  const start = cells.length >= 2 && isHeaderCell(cells[0]) && isHeaderCell(cells[1]) ? 2 : 0;
  const body = cells.slice(start).filter((cell) => !isHeaderCell(cell));
  if (body.length < 2 || body.length % 2 !== 0) return body;
  const rows: string[] = [];
  for (let index = 0; index < body.length; index += 2) {
    const left = body[index];
    const right = body[index + 1];
    rows.push(left === right ? left : `${left}：${right}`);
  }
  return rows;
}

function adviceParagraphs(raw: string): string[][] {
  const paragraphs: string[][] = [];
  let current: string[] = [];
  for (const line of plainAdviceLines(raw)) {
    if (!line) {
      if (current.length > 0) paragraphs.push(current);
      current = [];
      continue;
    }
    current.push(line);
  }
  if (current.length > 0) paragraphs.push(current);
  return paragraphs;
}

function AdviceCaret() {
  return <span className="ml-0.5 inline-block h-4 w-2 align-middle rounded-sm bg-brand-600 animate-pulse" />;
}

function AdviceLines({
  lines,
  advising,
  showCaret,
}: {
  lines: string[];
  advising: boolean;
  showCaret: boolean;
}) {
  const rest = lines.slice(1);
  const prose = (line: string) => /[。！？]$/.test(line) || /[：:]$/.test(line) || line.length > 48;
  const leadIsSentence = prose(lines[0] ?? '');
  const restAreLabels = rest.length > 0 && rest.every((line) => !prose(line));
  const labels = leadIsSentence && restAreLabels ? rest : lines.length > 1 && lines.every((line) => !prose(line)) ? lines : [];
  if (lines.length === 1 && !prose(lines[0])) {
    return (
      <p className="text-xs font-bold tracking-wide text-gray-500">
        {lines[0]}
        {advising && showCaret && <AdviceCaret />}
      </p>
    );
  }
  if (labels.length === 0) {
    return (
      <div className="space-y-2">
        {lines.map((line, index) => (
            <p key={index} className="text-sm leading-relaxed text-gray-800">
            {line}
            {advising && showCaret && index === lines.length - 1 && <AdviceCaret />}
          </p>
        ))}
      </div>
    );
  }
  return (
    <div className="space-y-2">
      {leadIsSentence && <p className="text-sm leading-relaxed text-gray-800">{lines[0]}</p>}
      <ul className="space-y-1 border-l-2 border-brand-100 pl-3">
        {labels.map((line, index) => (
          <li key={index} className="text-sm leading-6 text-gray-700">
            {line}
            {advising && showCaret && index === labels.length - 1 && <AdviceCaret />}
          </li>
        ))}
      </ul>
    </div>
  );
}

function AdviceCopy({ text, advising, compact }: { text: string; advising: boolean; compact?: boolean }) {
  const paragraphs = adviceParagraphs(text);
  if (paragraphs.length === 0) {
    return <p className="text-sm leading-6 text-gray-500">{advising ? '正在撰寫建議…' : ''}</p>;
  }
  const last = paragraphs[paragraphs.length - 1];
  const caution =
    paragraphs.length > 1 && last.some((line) => line.includes('注意') || line.startsWith('使用前')) ? last : null;
  const body = caution ? paragraphs.slice(0, -1) : paragraphs;
  return (
    <div className={compact ? 'space-y-2' : 'mt-3 space-y-3'}>
      {body.map((lines, index) => (
        <AdviceLines
          key={index}
          lines={lines}
          advising={advising}
          showCaret={!caution && index === body.length - 1}
        />
      ))}
      {caution && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2">
          <AdviceLines lines={caution} advising={advising} showCaret />
        </div>
      )}
    </div>
  );
}

function needsDownloadConfirm(report: ScanReport | null): boolean {
  const counts = severityCounts(report);
  return counts.high + counts.critical > 0;
}

export function IacWorkspace(props: Props) {
  const [pickedId, setPickedId] = useState<number | null | undefined>(undefined);
  const diagramId =
    pickedId === undefined ? (props.initialDiagramId ?? readStoredDiagram()) : pickedId;

  const pickDiagram = (nextId: number) => {
    if (nextId === diagramId) return;
    rememberDiagram(nextId);
    setPickedId(nextId);
  };

  return (
    <IacWorkspaceBody
      key={diagramId ?? 'none'}
      diagramId={diagramId}
      diagrams={props.diagrams}
      onClose={props.onClose}
      onPickDiagram={pickDiagram}
      onDiagramCreated={props.onDiagramCreated}
      initialStep={props.initialStep}
    />
  );
}

type BodyProps = {
  diagramId: number | null;
  diagrams: DiagramOption[];
  onClose: () => void;
  onPickDiagram: (id: number) => void;
  onDiagramCreated: (diagram: DiagramOption) => void;
  initialStep?: IacStep;
};

function IacWorkspaceBody({
  diagramId,
  diagrams,
  onClose,
  onPickDiagram,
  onDiagramCreated,
  initialStep = 'generate',
}: BodyProps) {
  const { token, can } = useAuth();
  const canEditD1 = can('D1', 'edit');
  const canEditD2 = can('D2', 'edit');
  const canEditD3 = can('D3', 'edit');

  const step = initialStep;
  const [draft, setDraft] = useState<DraftSummary | null>(null);
  const [scan, setScan] = useState<ScanReport | null>(null);
  const [rewrite, setRewrite] = useState<RewriteResult | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [draftEdits, setDraftEdits] = useState<Record<string, string>>({});
  const [editingPath, setEditingPath] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [editNotice, setEditNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<Exclude<IacAction, 'session'> | null>(null);
  const [error, setError] = useState<IacUiError | null>(null);
  const [copyNotice, setCopyNotice] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);
  const [generateNotice, setGenerateNotice] = useState<string | null>(null);
  const [uploadFiles, setUploadFiles] = useState<{ path: string; content: string }[]>([]);
  const [liveText, setLiveText] = useState('');
  const [advising, setAdvising] = useState(false);
  const [scanAdvice, setScanAdvice] = useState('');
  const [scanAdvising, setScanAdvising] = useState(false);
  const [readiness, setReadiness] = useState<DiagramReadiness[] | null>(null);
  const [loadedReadinessKey, setLoadedReadinessKey] = useState<string | null>(null);
  const diagramKey = diagrams.map((item) => item.id).join(',');
  const readinessLoading = Boolean(token) && loadedReadinessKey !== diagramKey;
  const selectedReadiness = readiness?.find((item) => item.diagram_id === diagramId) ?? null;
  const parsing = diagramId != null && readinessLoading && busy !== 'generate';
  const parseState: BarState =
    diagramId == null ? 'idle' : parsing ? 'run' : selectedReadiness?.status === 'ready' ? 'done' : selectedReadiness ? 'failed' : 'idle';
  const draftState: BarState = busy === 'generate' ? 'run' : draft?.status === 'succeeded' ? 'done' : 'idle';
  const parseValue = useBar(parseState);
  const draftValue = useBar(draftState);
  const epochRef = useRef(0);
  const draftStampRef = useRef(0);
  const scanKindRef = useRef<'diagram' | 'upload'>('diagram');
  const disposedRef = useRef(false);
  const mutationRef = useRef<AbortController | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  const downloadButtonRef = useRef<HTMLButtonElement>(null);

  const options = mergeOptions(diagrams, diagramId);
  const active = options.find((item) => item.id === diagramId) ?? null;
  const files = draft?.status === 'succeeded' ? draft.module_tree.files : [];
  const selected = files.find((file) => file.path === selectedPath) ?? null;
  const editorValue =
    selected && draftEdits[selected.path] !== undefined ? draftEdits[selected.path] : selected?.content ?? '';
  const draftDirty = files.some(
    (file) => draftEdits[file.path] !== undefined && draftEdits[file.path] !== file.content,
  );
  const hasDraft = draft?.status === 'succeeded';
  const hasScan = scan?.status === 'succeeded';
  const counts = severityCounts(scan);

  useEffect(() => {
    disposedRef.current = false;
    return () => {
      disposedRef.current = true;
      mutationRef.current?.abort();
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (diagramId == null || !token) return;
    const epoch = epochRef.current;
    const stamp = draftStampRef.current;
    const controller = new AbortController();
    let cancelled = false;
    getSession(token, diagramId, controller.signal)
      .then((snap) => {
        if (cancelled || disposedRef.current || epoch !== epochRef.current || stamp !== draftStampRef.current) return;
        if (snap.diagram_id !== diagramId) return;
        const nextDraft = snap.draft?.status === 'succeeded' ? snap.draft : null;
        setDraft(nextDraft);
        if (nextDraft) setGenerateNotice('已載入先前儲存的草稿');
        setLiveText(typeof snap.advice === 'string' ? snap.advice : '');
        setAdvising(false);
        setScanAdvice(typeof snap.scan_advice === 'string' ? snap.scan_advice : '');
        setScanAdvising(false);
        setScan(snap.latest_scan?.status === 'succeeded' ? snap.latest_scan : null);
        setRewrite(snap.latest_rewrite?.status === 'succeeded' ? snap.latest_rewrite : null);
        setSelectedPath(nextDraft?.module_tree.files[0]?.path ?? null);
      })
      .catch((err: unknown) => {
        if (cancelled || disposedRef.current || epoch !== epochRef.current || isAbortError(err)) {
          return;
        }
        const code = err instanceof IacTimeoutError ? 'timeout' : err instanceof IacHttpError ? err.code : 'unknown';
        setError({ action: 'session', code, text: mapIacErrorCode(code, 'session') });
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [diagramId, token]);

  useEffect(() => {
    if (diagramId != null) rememberDiagram(diagramId);
  }, [diagramId]);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    getReadiness(token, controller.signal)
      .then((rows) => {
        if (!disposedRef.current) setReadiness(rows);
      })
      .catch((err: unknown) => {
        if (isAbortError(err) || disposedRef.current) return;
        setReadiness(null);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadedReadinessKey(diagramKey);
      });
    return () => controller.abort();
  }, [token, diagramKey]);

  const beginMutation = () => {
    mutationRef.current?.abort();
    const controller = new AbortController();
    mutationRef.current = controller;
    epochRef.current += 1;
    return { epoch: epochRef.current, signal: controller.signal };
  };

  const fail = (action: IacAction, epoch: number, err: unknown) => {
    if (disposedRef.current || epoch !== epochRef.current || isAbortError(err)) return;
    const code =
      err instanceof IacTimeoutError
        ? 'timeout'
        : err instanceof IacHttpError
          ? err.code
          : 'unknown';
    const reason = err instanceof IacHttpError ? err.reason : null;
    setLiveText('');
    setError({ action, code, text: mapIacErrorCode(code, action, reason) });
  };

  const finish = (action: Exclude<IacAction, 'session'>, epoch: number) => {
    if (disposedRef.current || epoch !== epochRef.current) return;
    setBusy((current) => (current === action ? null : current));
  };

  const rememberDraft = (next: DraftSummary) => {
    draftStampRef.current += 1;
    setDraft(next);
    setSelectedPath((current) => {
      if (current && next.module_tree.files.some((file) => file.path === current)) return current;
      return next.module_tree.files[0]?.path ?? null;
    });
  };

  const readinessReason =
    selectedReadiness && selectedReadiness.status !== 'ready' ? readinessCopy(selectedReadiness.status) : null;
  const readyAlternatives = (readiness ?? []).filter(
    (item) => item.status === 'ready' && item.diagram_id !== diagramId,
  );

  const runGenerate = () => {
    if (diagramId == null || !token || !canEditD1 || busy || readinessReason) return;
    if (tokenExpired(token)) {
      setLiveText('');
      setError({
        action: 'generate',
        code: 'unauthorized',
        text: mapIacErrorCode('unauthorized', 'generate'),
      });
      return;
    }
    const requested = diagramId;
    const { epoch, signal } = beginMutation();
    setBusy('generate');
    setError(null);
    setSaveNotice(null);
    setGenerateNotice(null);
    setLiveText('');
    setAdvising(false);
    postGenerate(token, requested, signal)
      .then(async (body) => {
        if (body.draft?.status === 'succeeded') {
          rememberDraft(body.draft);
          setScan(null);
          setRewrite(null);
          setScanAdvice('');
          setGenerateNotice('產生完成');
        }
        setBusy((current) => (current === 'generate' ? null : current));
        if (disposedRef.current) return;
        const adviceController = new AbortController();
        mutationRef.current = adviceController;
        setAdvising(true);
        try {
          await streamAdvice(token, requested, adviceController.signal, (text) => {
            if (disposedRef.current || adviceController.signal.aborted) return;
            setLiveText((current) => current + text);
          });
        } catch {
          if (disposedRef.current || adviceController.signal.aborted) return;
          setLiveText((current) => current || 'AI 建議暫時無法產生。草稿已完成，不受影響。');
        }
      })
      .catch(async (err: unknown) => {
        if (!disposedRef.current && epoch === epochRef.current) {
          try {
            const snap = await getSession(token, requested, signal);
            if (snap.draft?.status === 'succeeded') {
              rememberDraft(snap.draft);
              setGenerateNotice('產生完成');
              setError(null);
              setLiveText((current) => current || 'AI 建議逾時。草稿已完成，不受影響。');
              return;
            }
          } catch {
            /* keep the original generate error */
          }
        }
        fail('generate', epoch, err);
      })
      .finally(() => {
        if (!disposedRef.current) setAdvising(false);
        finish('generate', epoch);
      });
  };

  const runApplyEdit = () => {
    if (diagramId == null || !token || !canEditD1 || !hasDraft || busy || applying || !draftDirty) return;
    const requested = diagramId;
    const nextFiles = files.map((file) => ({
      path: file.path,
      content: draftEdits[file.path] !== undefined ? draftEdits[file.path] : file.content,
    }));
    const { epoch, signal } = beginMutation();
    setApplying(true);
    setEditNotice(null);
    setError(null);
    postDraftFiles(token, requested, nextFiles, signal)
      .then((body) => {
        if (disposedRef.current || epoch !== epochRef.current) return;
        if (body.draft?.status === 'succeeded') rememberDraft(body.draft);
        setDraftEdits({});
        setEditingPath(null);
        setScan(null);
        setRewrite(null);
        setScanAdvice('');
        setEditNotice('已套用修改。請重新掃描。');
      })
      .catch((err: unknown) => {
        if (disposedRef.current || epoch !== epochRef.current) return;
        const code =
          err instanceof IacTimeoutError ? 'timeout' : err instanceof IacHttpError ? err.code : 'unknown';
        const reason = err instanceof IacHttpError ? err.reason : null;
        setEditNotice(mapIacErrorCode(code, 'generate', reason));
      })
      .finally(() => {
        if (!disposedRef.current) setApplying(false);
      });
  };

  const runSave = () => {
    if (diagramId == null || !token || !canEditD1 || !hasDraft || busy || saving) return;
    const requested = diagramId;
    const note = liveText.trim();
    const { epoch, signal } = beginMutation();
    setSaving(true);
    setSaveNotice(null);
    setError(null);
    postSave(token, requested, signal, note)
      .then(() => {
        if (disposedRef.current || epoch !== epochRef.current) return;
        const keptAdvice = Boolean(note || scanAdvice.trim());
        if (scan && keptAdvice) setSaveNotice('草稿、掃描結果與 AI 建議已存到資料庫');
        else if (scan) setSaveNotice('草稿與掃描結果已存到資料庫');
        else if (note) setSaveNotice('草稿與 AI 建議已存到資料庫');
        else setSaveNotice('已存到資料庫');
      })
      .catch((err: unknown) => fail('generate', epoch, err))
      .finally(() => {
        if (!disposedRef.current) setSaving(false);
      });
  };

  const runScan = () => {
    if (diagramId == null || !token || !canEditD2 || !hasDraft || busy) return;
    const requested = diagramId;
    scanKindRef.current = 'diagram';
    const { epoch, signal } = beginMutation();
    setBusy('scan');
    setError(null);
    postScan(token, requested, signal)
      .then((body) => {
        if (disposedRef.current || epoch !== epochRef.current) return;
        if (body.report?.status !== 'succeeded') return;
        setScan(body.report);
        setScanAdvice('');
        setBusy((current) => (current === 'scan' ? null : current));
        const adviceController = new AbortController();
        mutationRef.current = adviceController;
        setScanAdvising(true);
        return streamScanAdvice(token, requested, adviceController.signal, (text) => {
          if (disposedRef.current || adviceController.signal.aborted) return;
          setScanAdvice((current) => current + text);
        }).catch((err: unknown) => {
          if (disposedRef.current || adviceController.signal.aborted) return;
          const fallback =
            err instanceof IacTimeoutError
              ? 'AI 建議逾時。掃描結果不受影響。'
              : 'AI 建議暫時無法產生。掃描結果不受影響。';
          setScanAdvice((current) => current || fallback);
        }).finally(() => {
          if (!disposedRef.current) setScanAdvising(false);
        });
      })
      .catch((err: unknown) => fail('scan', epoch, err))
      .finally(() => finish('scan', epoch));
  };

  const onTfUpload = (list: FileList | null) => {
    const chosen = Array.from(list ?? []);
    if (!chosen.length) return;
    const accepted = chosen.filter((file) => file.name.toLowerCase().endsWith('.tf'));
    if (!accepted.length) {
      setUploadFiles([]);
      setUploadError('只接受 .tf 檔。');
      return;
    }
    Promise.all(
      accepted.map(async (file) => ({
        path: file.name.replace(/\\/g, '/').split('/').pop() || file.name,
        content: await file.text(),
      })),
    )
      .then((files) => {
        if (disposedRef.current) return;
        setUploadError(null);
        setUploadFiles(files);
      })
      .catch(() => {
        if (!disposedRef.current) setUploadError('上傳失敗，尚未掃描。');
      });
  };

  const runUploadScan = () => {
    if (!token || !canEditD2 || !uploadFiles.length || busy) return;
    scanKindRef.current = 'upload';
    const { epoch, signal } = beginMutation();
    setBusy('scan');
    setError(null);
    postScanFiles(token, uploadFiles, signal)
      .then((body) => {
        if (disposedRef.current || epoch !== epochRef.current) return;
        if (body.report?.status === 'succeeded') setScan(body.report);
      })
      .catch((err: unknown) => fail('scan', epoch, err))
      .finally(() => finish('scan', epoch));
  };

  const runRewrite = () => {
    if (diagramId == null || !token || !canEditD3 || !hasScan || busy) return;
    const requested = diagramId;
    const { epoch, signal } = beginMutation();
    setBusy('rewrite');
    setError(null);
    postRewrite(token, requested, signal)
      .then((body) => {
        if (disposedRef.current || epoch !== epochRef.current) return;
        if (body.rewrite?.status === 'succeeded') {
          const paths = Array.isArray(body.rewrite.rewritten_paths) ? body.rewrite.rewritten_paths : [];
          setRewrite({ ...body.rewrite, rewritten_paths: [...paths] });
        }
        if (body.draft?.status === 'succeeded') rememberDraft(body.draft);
      })
      .catch((err: unknown) => fail('rewrite', epoch, err))
      .finally(() => finish('rewrite', epoch));
  };

  const runDownload = () => {
    if (diagramId == null || !token || !canEditD1 || !hasDraft || busy) return;
    const requested = diagramId;
    const { epoch, signal } = beginMutation();
    setBusy('download');
    setError(null);
    getDownloadBlob(token, requested, signal)
      .then((blob) => {
        if (disposedRef.current || epoch !== epochRef.current) return;
        const objectUrl = URL.createObjectURL(blob);
        if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = objectUrl;
        const anchor = document.createElement('a');
        anchor.href = objectUrl;
        anchor.download = `iac-diagram-${requested}.zip`;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.setTimeout(() => {
          if (objectUrlRef.current === objectUrl) {
            URL.revokeObjectURL(objectUrl);
            objectUrlRef.current = null;
          }
        }, 0);
      })
      .catch((err: unknown) => fail('download', epoch, err))
      .finally(() => finish('download', epoch));
  };

  const requestDownload = () => {
    if (!hasDraft || busy) return;
    if (needsDownloadConfirm(scan)) {
      setConfirmOpen(true);
      return;
    }
    runDownload();
  };

  const closeConfirm = useCallback(() => setConfirmOpen(false), []);

  const retry = () => {
    if (!error) return;
    if (error.action === 'generate') runGenerate();
    else if (error.action === 'scan') {
      if (scanKindRef.current === 'upload') runUploadScan();
      else runScan();
    }
    else if (error.action === 'rewrite') runRewrite();
    else if (error.action === 'download') requestDownload();
  };

  const onUpload = (file: File | null) => {
    if (!file || !token) return;
    setUploadError(null);
    createDiagramFromFile(token, file)
      .then((created) => {
        if (disposedRef.current) return;
        onDiagramCreated(created);
        onPickDiagram(created.id);
      })
      .catch((err: unknown) => {
        if (disposedRef.current) return;
        if (err instanceof DiagramUploadError && err.reason === 'type') {
          setUploadError('只接受 .drawio 或 .xml，架構圖未變更。');
          return;
        }
        setUploadError('上傳失敗，架構圖未變更。');
      });
  };

  const copyCurrent = () => {
    if (!selected) return;
    navigator.clipboard
      .writeText(editorValue)
      .then(() => {
        if (!disposedRef.current) setCopyNotice('已複製目前檔案');
      })
      .catch(() => {
        if (!disposedRef.current) setCopyNotice('無法複製目前檔案');
      });
  };

  const d1Reason =
    diagramId == null ? '需要先選擇架構圖。' : !canEditD1 ? '缺少 D1 edit 權限。' : readinessReason;
  const d2Reason = !hasDraft ? '尚無草稿，無法掃描。' : !canEditD2 ? '缺少 D2 edit 權限。' : null;
  const d3Reason = !hasScan ? '需要已完成的掃描報告，才能改寫。' : !canEditD3 ? '缺少 D3 edit 權限。' : null;
  const downloadReason = !hasDraft ? '尚無草稿，無法下載。' : !canEditD1 ? '缺少 D1 edit 權限。' : null;
  const runReason = step === 'generate' ? d1Reason : step === 'scan' ? d2Reason : d3Reason;
  const permissionNotice =
    step === 'generate' && !canEditD1
      ? {
          title: '無法產生 IaC 草稿',
          detail:
            '這個帳號可以檢視本頁，但沒有 D1 編輯權限。「產生 IaC」不會送出請求，畫面上也不會出現新的 main.tf。請改用有編輯權限的帳號，或請管理員開啟 D1 編輯。',
        }
      : step === 'scan' && !canEditD2
        ? {
            title: '無法執行掃描',
            detail: '這個帳號可以檢視本頁，但沒有 D2 編輯權限。「執行掃描」不會送出請求。',
          }
        : step === 'secrets' && !canEditD3
          ? {
              title: '無法執行改寫',
              detail: '這個帳號可以檢視本頁，但沒有 D3 編輯權限。「執行改寫」不會送出請求。',
            }
          : null;
  const experimental = files.some((file) => EXPERIMENTAL.test(file.content));
  const pageTitle = iacNavItem(step)?.label ?? '基礎建設';

  const uploadReason = !canEditD2
    ? '缺少 D2 edit 權限。'
    : uploadFiles.length === 0
      ? '請先選擇 .tf 檔。'
      : null;

  return (
    <div
      data-testid="iac-workspace"
      className="absolute inset-0 z-20 flex flex-col overflow-hidden bg-slate-50 text-gray-900"
      aria-busy={busy ? true : undefined}
    >
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 bg-white px-4 py-3">
        <div className="min-w-0">
          <h1 className="text-lg font-bold tracking-tight text-gray-900">{pageTitle}</h1>
          <p className="truncate text-sm text-gray-500">{active ? active.title : '尚無架構圖'}</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs font-bold text-gray-600" htmlFor="iac-diagram-select">
            選擇架構圖
            <select
              id="iac-diagram-select"
              data-testid="iac-diagram-select"
              className="mt-1 block rounded-xl border border-gray-200 bg-gray-50 px-2 py-2 text-sm font-semibold"
              value={diagramId == null ? '' : String(diagramId)}
              onChange={(event) => {
                const next = Number(event.target.value);
                if (!Number.isInteger(next) || next < 1) return;
                onPickDiagram(next);
              }}
            >
              <option value="" disabled>
                尚無架構圖
              </option>
              {options.map((item) => (
                <option key={item.id} value={item.id}>
                  {optionLabel(item, readiness?.find((row) => row.diagram_id === item.id))}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-bold text-gray-600">
            上傳 .drawio／.xml
            <input
              data-testid="iac-diagram-upload"
              type="file"
              accept=".drawio,.xml,application/xml,text/xml"
              className="mt-1 block w-full text-xs font-normal"
              onChange={(event) => {
                const file = event.target.files?.[0] ?? null;
                event.target.value = '';
                onUpload(file);
              }}
            />
          </label>
        </div>
      </header>
      {uploadError && (
        <p className="border-b border-red-100 bg-red-50 px-4 py-2 text-sm text-red-700">{uploadError}</p>
      )}

      <main className="flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 overflow-auto p-4">
          {readinessReason && (
            <div
              data-testid="iac-readiness-notice"
              role="status"
              className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 p-4"
            >
              <p className="text-sm font-semibold text-amber-950">{readinessReason}</p>
              {readyAlternatives.length > 0 ? (
                <div className="mt-3">
                  <p className="text-sm text-amber-900">可以改用這些架構圖：</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {readyAlternatives.map((item) => (
                      <button
                        key={item.diagram_id}
                        type="button"
                        data-testid="iac-ready-diagram"
                        onClick={() => onPickDiagram(item.diagram_id)}
                        className="rounded-xl border border-amber-300 bg-white px-3 py-2 text-sm font-bold text-amber-950"
                      >
                        {item.title}（{item.node_count} 個節點）
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="mt-2 text-sm text-amber-900">目前沒有其他可產生 IaC 的架構圖。</p>
              )}
            </div>
          )}
          {permissionNotice && (
            <div
              data-testid="iac-permission-notice"
              role="status"
              className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 p-4"
            >
              <p className="text-sm font-semibold text-amber-950">{permissionNotice.title}</p>
              <p className="mt-1 text-sm text-amber-900">{permissionNotice.detail}</p>
            </div>
          )}
          {diagramId == null ? (
            <div data-testid="iac-no-diagram" className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
              <p className="text-sm font-semibold text-amber-950">尚無架構圖，無法產生 IaC。</p>
              <button
                type="button"
                data-testid="iac-back-workspace"
                onClick={onClose}
                className="mt-4 rounded-xl bg-white px-4 py-2 text-sm font-bold text-gray-800 border border-gray-200"
              >
                回到 Workspace
              </button>
            </div>
          ) : (
            <>
            {step === 'generate' && generateNotice && (
              <p className="mb-4 text-sm text-gray-700" role="status">
                {generateNotice}
              </p>
            )}
            <StepBody
              step={step}
              files={files}
              selectedPath={selectedPath}
              selected={selected}
              experimental={experimental}
              scan={scan}
              scanAdvice={scanAdvice}
              scanAdvising={scanAdvising}
              rewrite={rewrite}
              busy={busy}
              liveText={liveText}
              advising={advising}
              generateError={error?.action === 'generate' ? error.text : ''}
              scanError={error?.action === 'scan' ? error.text : ''}
              stages={
                step === 'generate'
                  ? [
                      { id: 'parse', label: barLabel('parse', parseState), value: parseValue, state: parseState },
                      { id: 'draft', label: barLabel('draft', draftState), value: draftValue, state: draftState },
                    ]
                  : []
              }
              uploadNames={uploadFiles.map((file) => file.path)}
              onTfUpload={onTfUpload}
              onSelect={(path) => {
                setSelectedPath(path);
                setEditingPath(null);
              }}
              canEditDraft={canEditD1}
              editing={editingPath === selectedPath && selectedPath != null}
              editorValue={editorValue}
              draftDirty={draftDirty}
              applying={applying}
              editNotice={editNotice}
              onStartEdit={() => {
                if (!selected) return;
                setEditingPath(selected.path);
                setEditNotice(null);
              }}
              onEdit={(value) => {
                if (!selected) return;
                setDraftEdits((current) => ({ ...current, [selected.path]: value }));
              }}
              onCancelEdit={() => {
                if (selected) {
                  setDraftEdits((current) => {
                    const next = { ...current };
                    delete next[selected.path];
                    return next;
                  });
                }
                setEditingPath(null);
              }}
              onApplyEdit={runApplyEdit}
            />
            </>
          )}
        </div>

        <div className="border-t border-gray-200 bg-white px-4 py-3 flex flex-wrap items-center gap-2">
          {step === 'generate' && (
            <button
              type="button"
              data-testid="iac-run-d1"
              disabled={Boolean(d1Reason) || Boolean(busy)}
              aria-describedby={d1Reason ? 'iac-run-reason' : undefined}
              onClick={runGenerate}
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-40"
            >
              產生 IaC
            </button>
          )}
          {step === 'generate' && (
            <button
              type="button"
              data-testid="iac-save"
              disabled={!hasDraft || !canEditD1 || Boolean(busy) || saving || scanAdvising}
              onClick={runSave}
              className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-bold text-gray-800 disabled:opacity-40"
            >
              {saving ? '儲存中' : '儲存 IaC'}
            </button>
          )}
          {(step === 'generate' || step === 'scan') && saveNotice && (
            <p data-testid="iac-save-notice" className="text-sm text-gray-700" role="status">
              {saveNotice}
            </p>
          )}
          {step === 'generate' && !hasDraft && canEditD1 && (
            <p className="text-sm text-gray-600">產生完成後才能儲存。</p>
          )}
          {step === 'scan' && (
            <button
              type="button"
              data-testid="iac-save"
              disabled={!hasDraft || !canEditD1 || Boolean(busy) || saving || scanAdvising}
              onClick={runSave}
              className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-bold text-gray-800 disabled:opacity-40"
            >
              {saving ? '儲存中' : '儲存掃描結果'}
            </button>
          )}
          {step === 'scan' && (
            <button
              type="button"
              data-testid="iac-run-d2"
              disabled={Boolean(d2Reason) || Boolean(busy)}
              aria-describedby={d2Reason ? 'iac-run-reason' : undefined}
              onClick={runScan}
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-40"
            >
              掃描此架構圖的 IaC
            </button>
          )}
          {step === 'scan' && (
            <button
              type="button"
              data-testid="iac-scan-upload"
              disabled={Boolean(uploadReason) || Boolean(busy)}
              onClick={runUploadScan}
              className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-bold text-gray-800 disabled:opacity-40"
            >
              掃描上傳的檔案
            </button>
          )}
          {step === 'secrets' && (
            <button
              type="button"
              data-testid="iac-run-d3"
              disabled={Boolean(d3Reason) || Boolean(busy)}
              aria-describedby={d3Reason ? 'iac-run-reason' : undefined}
              onClick={runRewrite}
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-40"
            >
              執行改寫
            </button>
          )}
          {runReason && step !== 'scan' && (
            <p id="iac-run-reason" className="text-sm text-gray-600">
              {runReason}
            </p>
          )}
          {step === 'scan' && d2Reason && (
            <p id="iac-run-reason" className="text-sm text-gray-600">
              {d2Reason}
            </p>
          )}
          {step === 'scan' && uploadReason && uploadReason !== d2Reason && (
            <p className="text-sm text-gray-600">{uploadReason}</p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-gray-200 bg-white px-4 py-3">
          <button
            type="button"
            ref={downloadButtonRef}
            data-testid="iac-download"
            disabled={Boolean(downloadReason) || Boolean(busy)}
            onClick={requestDownload}
            className="rounded-xl bg-gray-900 px-4 py-2 text-sm font-bold text-white disabled:opacity-40"
          >
            下載
          </button>
          {downloadReason && <p className="text-sm text-gray-600">{downloadReason}</p>}
          <button
            type="button"
            data-testid="iac-copy"
            disabled={!selected || Boolean(busy)}
            onClick={copyCurrent}
            className="rounded-xl border border-gray-200 px-4 py-2 text-sm font-bold text-gray-800 disabled:opacity-40"
          >
            複製目前檔
          </button>
          {copyNotice && <p className="text-sm text-gray-600">{copyNotice}</p>}
          {busy && busy !== 'generate' && <p className="text-sm text-gray-600">{BUSY_TEXT[busy]}</p>}
          {error && !busy && error.action !== 'session' && (
            <button
              type="button"
              data-testid="iac-retry"
              onClick={retry}
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm font-bold text-gray-800"
            >
              重試
            </button>
          )}
          <button type="button" onClick={onClose} className="ml-auto text-sm font-bold text-brand-700">
            回到 Workspace
          </button>
        </div>
      </main>

      {confirmOpen && (
        <IacDownloadConfirm
          highCount={counts.high}
          criticalCount={counts.critical}
          onCancel={closeConfirm}
          onConfirm={() => {
            setConfirmOpen(false);
            runDownload();
          }}
          returnFocusRef={downloadButtonRef}
        />
      )}
    </div>
  );
}

function ScanChecks({ scan }: { scan: ScanReport }) {
  const checks = scan.checks ?? [];
  if (checks.length > 0) {
    const failed = checks.some((item) => item.status === 'failed');
    return (
      <div className="space-y-3">
        {!failed && (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
            <p className="text-sm font-semibold text-emerald-950">安全</p>
            <p className="mt-1 text-sm leading-6 text-emerald-950">列出的檢查都通過。</p>
          </div>
        )}
        <ul data-testid="iac-findings" className="space-y-2">
          {checks.map((item, index) => (
            <li
              key={`${item.id}-${item.resource ?? ''}-${item.path ?? ''}-${index}`}
              className="flex items-start justify-between gap-3 rounded-xl border border-gray-200 bg-white p-3 text-sm"
            >
              <span>
                <span className="font-medium text-gray-900">{item.title}</span>
                {(item.resource || item.path) && (
                  <span className="mt-1 block font-mono text-xs text-gray-500">
                    {[item.resource, item.path].filter(Boolean).join(' · ')}
                  </span>
                )}
              </span>
              <span
                className={
                  item.status === 'failed'
                    ? 'shrink-0 font-semibold text-amber-800'
                    : item.status === 'passed'
                      ? 'shrink-0 font-semibold text-emerald-800'
                      : 'shrink-0 font-semibold text-gray-500'
                }
              >
                {checkStatusLabel(item.status)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    );
  }
  if (scan.findings.length === 0) {
    return (
      <p data-testid="iac-findings" className="text-sm text-gray-700">
        這份草稿沒有 Checkov 認得的檢查項目。
      </p>
    );
  }
  return (
    <ul data-testid="iac-findings" className="space-y-2">
      {scan.findings.map((finding) => (
        <li key={finding.id} className="rounded-xl border border-gray-200 bg-white p-3 text-sm">
          <span className="font-bold">{finding.severity}</span>
          <span className="mx-2 text-gray-400">·</span>
          <span>{finding.title}</span>
          {finding.path && <span className="ml-2 text-gray-500">{finding.path}</span>}
        </li>
      ))}
    </ul>
  );
}

function StepBody({
  step,
  files,
  selectedPath,
  selected,
  experimental,
  scan,
  scanAdvice,
  scanAdvising,
  rewrite,
  busy,
  liveText,
  advising,
  generateError,
  scanError,
  stages,
  uploadNames,
  onTfUpload,
  onSelect,
  canEditDraft,
  editing,
  editorValue,
  draftDirty,
  applying,
  editNotice,
  onStartEdit,
  onEdit,
  onCancelEdit,
  onApplyEdit,
}: {
  step: IacStep;
  files: IacFileEntry[];
  selectedPath: string | null;
  selected: IacFileEntry | null;
  experimental: boolean;
  scan: ScanReport | null;
  scanAdvice: string;
  scanAdvising: boolean;
  rewrite: RewriteResult | null;
  busy: Exclude<IacAction, 'session'> | null;
  liveText: string;
  advising: boolean;
  generateError: string;
  scanError: string;
  stages: { id: string; label: string; value: number; state: BarState }[];
  uploadNames: string[];
  onTfUpload: (list: FileList | null) => void;
  onSelect: (path: string) => void;
  canEditDraft: boolean;
  editing: boolean;
  editorValue: string;
  draftDirty: boolean;
  applying: boolean;
  editNotice: string | null;
  onStartEdit: () => void;
  onEdit: (value: string) => void;
  onCancelEdit: () => void;
  onApplyEdit: () => void;
}) {
  if (step === 'scan') {
    return (
      <section className="space-y-4">
        <div className="rounded-2xl border border-gray-200 bg-white p-4">
          <p className="text-sm font-semibold text-gray-900">此架構圖已儲存的 IaC</p>
          {files.length === 0 ? (
            <p className="mt-1 text-sm text-gray-600">
              這張架構圖還沒有儲存的 IaC。可先到 Terraform 產出儲存，或在下面上傳 .tf 檔。
            </p>
          ) : (
            <ul className="mt-2 space-y-1">
              {files.map((file) => (
                <li key={file.path} className="font-mono text-sm text-gray-800">
                  {file.path}
                </li>
              ))}
            </ul>
          )}
        </div>
        <label className="block text-sm font-semibold text-gray-900">
          上傳 .tf 檔
          <input
            data-testid="iac-tf-upload"
            type="file"
            accept=".tf,text/plain"
            multiple
            className="mt-1 block w-full text-xs font-normal"
            onChange={(event) => {
              onTfUpload(event.target.files);
              event.target.value = '';
            }}
          />
        </label>
        {uploadNames.length > 0 && (
          <ul className="space-y-1">
            {uploadNames.map((path) => (
              <li key={path} className="font-mono text-sm text-gray-700">
                {path}
              </li>
            ))}
          </ul>
        )}
        {scanError && (
          <div
            data-testid="iac-scan-error"
            role="alert"
            className="rounded-2xl border border-amber-200 bg-amber-50 p-4"
          >
            <p className="text-sm font-semibold text-amber-950">掃描沒有完成</p>
            <p className="mt-1 text-sm leading-6 text-amber-950">{scanError}</p>
          </div>
        )}
        {(scanAdvice || scanAdvising) && (
          <div data-testid="iac-scan-advice" className="rounded-2xl border border-gray-200 bg-white p-4">
            <p className="text-sm font-semibold text-gray-900">AI 建議</p>
            <AdviceCopy text={scanAdvice} advising={scanAdvising} />
          </div>
        )}
        {!scan && !scanError ? (
          <p className="text-sm text-gray-600">尚未掃描。</p>
        ) : scan ? (
          <ScanChecks scan={scan} />
        ) : null}
      </section>
    );
  }

  if (step === 'secrets') {
    const paths = rewrite?.status === 'succeeded' ? rewrite.rewritten_paths : [];
    return (
      <section>
        {!scan ? (
          <p className="text-sm text-gray-600">此步驟可先查看。執行改寫需要已完成的掃描報告。</p>
        ) : (
          <ul data-testid="iac-rewrite-list" className="space-y-2">
            {paths.length === 0 ? (
              <li className="text-sm text-gray-700">無可改寫項</li>
            ) : (
              paths.map((path) => (
                <li key={path} className="rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-mono">
                  {path}
                </li>
              ))
            )}
          </ul>
        )}
      </section>
    );
  }

  return (
    <section className="grid min-h-64 grid-cols-1 gap-3 lg:grid-cols-[12rem_minmax(0,1fr)]">
      {stages.length > 0 && (
        <div className="col-span-full rounded-2xl border border-gray-200 bg-white p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            {stages.map((item) => (
              <ProgressMeter
                key={item.id}
                testId={`iac-progress-${item.id}`}
                label={item.label}
                value={item.value}
                state={item.state}
              />
            ))}
          </div>
        </div>
      )}
      {(liveText || advising) && (
        <section
          data-testid="iac-ai-advice"
          className="col-span-full rounded-2xl border border-brand-100 bg-white p-4"
          aria-live="polite"
        >
          <p className="text-sm font-bold text-brand-700">AI 建議</p>
          <AdviceCopy text={liveText} advising={advising} />
        </section>
      )}
      {generateError && !busy && (
        <p className="col-span-full text-sm font-semibold text-amber-950">{generateError}</p>
      )}
      <ul data-testid="iac-file-tree" className="rounded-2xl border border-gray-200 bg-white p-2">
        {files.length === 0 ? (
          <li className="px-2 py-1 text-sm text-gray-500">尚未產生草稿</li>
        ) : (
          files.map((file) => (
            <li key={file.path}>
              <button
                type="button"
                onClick={() => onSelect(file.path)}
                className={`w-full rounded-lg px-2 py-1 text-left text-sm font-mono ${
                  file.path === selectedPath ? 'bg-brand-50 text-brand-800' : 'hover:bg-gray-50'
                }`}
              >
                {file.path}
              </button>
            </li>
          ))
        )}
      </ul>
      <div className="min-w-0">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <p className="text-xs text-gray-500">HCL 草稿，不限定單一發行版。</p>
          {canEditDraft && selected && !editing && (
            <button
              type="button"
              data-testid="iac-edit-tf"
              onClick={onStartEdit}
              className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs font-bold text-gray-800"
            >
              編輯此檔
            </button>
          )}
          {canEditDraft && draftDirty && (
            <button
              type="button"
              data-testid="iac-apply-edit"
              disabled={applying || Boolean(busy)}
              onClick={onApplyEdit}
              className="rounded-lg bg-brand-600 px-2 py-1 text-xs font-bold text-white disabled:opacity-40"
            >
              {applying ? '套用中' : '套用修改'}
            </button>
          )}
          {editing && (
            <button
              type="button"
              onClick={onCancelEdit}
              disabled={applying}
              className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs font-bold text-gray-800 disabled:opacity-40"
            >
              取消
            </button>
          )}
        </div>
        {experimental && <p className="mb-2 text-sm font-bold text-amber-800">實驗性</p>}
        {editNotice && (
          <p data-testid="iac-edit-notice" className="mb-2 text-sm text-gray-700" role="status">
            {editNotice}
          </p>
        )}
        {editing ? (
          <textarea
            data-testid="iac-hcl-preview"
            value={editorValue}
            spellCheck={false}
            onChange={(event) => onEdit(event.target.value)}
            className="h-80 w-full resize-y overflow-auto rounded-2xl border border-gray-200 bg-white p-3 font-mono text-xs leading-5 text-gray-800"
          />
        ) : (
          <pre
            data-testid="iac-hcl-preview"
            className="overflow-auto rounded-2xl border border-gray-200 bg-white p-3 text-xs leading-5 text-gray-800"
          >
            {selected?.content ?? ''}
          </pre>
        )}
      </div>
    </section>
  );
}

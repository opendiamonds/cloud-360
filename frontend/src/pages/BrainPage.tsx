/**
 * 大腦入口頁 —— **DEMO SCOPE，非 U14 entry-page-ui 的正式交付**。
 *
 * 它刻意實作 `brain-ws-contract` functional-design 已定案的契約：
 *   - 封包 `{v, type, turnId, payload}`，`v` 為字面值 1
 *   - token 走 `Sec-WebSocket-Protocol`（**不是** query string，`AC8.1.3`）
 *   - `hello` → `ready` 版本協商；`protocolVersion` 必須被驗證（`BR3.5`）
 *   - 未知 `type` 安全忽略並記錄異常（`BR3.2`）
 *   - 零內容的 `done` 視為**契約違規**：顯示備援提示並記錄異常（`BR3.3`）
 *   - `error.code` 四值窮盡處理（`BR3.1`）
 *   - 未收到終止事件時標為未完成，**不自動重試**（`BR3.4`）
 *
 * 它刻意沒有：脈絡列的三層選擇器（`U7`）、記憶檢視（`U8`）、成本卡片、
 * 多連線扇出、無障礙完整處理。`U14` 落地時整支取代本檔。
 *
 * 資料抓取形狀沿用 `team.md ## Code Style` 的 lint 約束：不在 effect 內直接 setState，
 * 卸載以 flag 防護，state 更新一律回傳新物件。
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { wsUrl } from '../config/api';

const PROTOCOL_VERSION = 1;

type Candidate = {
  id: string;
  label: string;
  capability: string;
  confidence: number | null;
};

type WorkItem = {
  workItemId: string;
  label: string;
  status: string;
  capability: string;
  waitingOn: string | null;
  failureReason: string | null;
  sideEffect: string;
};

type Turn = {
  turnId: string;
  text: string;
  /** 'streaming' 尚未收到終止事件；其餘為終止後的結果 */
  state: 'streaming' | 'done' | 'error' | 'incomplete' | 'contract-violation';
  errorCode?: string;
  errorMessage?: string;
};

type ConnState = 'idle' | 'connecting' | 'ready' | 'closed' | 'version-mismatch' | 'unauthorized';

export function BrainPage() {
  // token 在 render 期讀一次即可（本頁生命週期內不會換人）。放在 useState 初始值裡而非
  // effect 內做 setState，是 react-hooks/set-state-in-effect（error 級）的要求。
  // 正本在 sessionStorage（AuthContext 的 TOKEN_STORAGE_KEY），localStorage 是相容備援
  // ——沿用 components/cost/types.ts:62 既有的雙讀形狀，不自創第三種。
  const [token] = useState<string | null>(
    () => sessionStorage.getItem('token') || localStorage.getItem('token')
  );
  const [conn, setConn] = useState<ConnState>(token ? 'connecting' : 'unauthorized');
  const [closeReason, setCloseReason] = useState<string>(
    token ? '' : '沒有登入憑證，請先登入'
  );
  const [input, setInput] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [workItems, setWorkItems] = useState<WorkItem[]>([]);
  const [anomalies, setAnomalies] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const noteAnomaly = useCallback((what: string) => {
    // BR3.2／BR3.3 都要求「記錄異常」——這裡讓它在畫面上看得見，而非只進 console
    console.warn('[brain][契約異常]', what);
    setAnomalies((prev) => [...prev, `${new Date().toLocaleTimeString()} ${what}`]);
  }, []);

  useEffect(() => {
    if (!token) return;

    let cancelled = false;

    // token 走 subprotocol，不進 query string（AC8.1.3）
    const ws = new WebSocket(wsUrl('/api/brain/ws'), [`bearer.${token}`]);
    wsRef.current = ws;

    ws.onopen = () => {
      if (cancelled) return;
      ws.send(
        JSON.stringify({ v: PROTOCOL_VERSION, type: 'hello', payload: { v: PROTOCOL_VERSION } })
      );
    };

    ws.onmessage = (ev) => {
      if (cancelled) return;
      let msg: { v?: number; type?: string; turnId?: string | null; payload?: Record<string, unknown> };
      try {
        msg = JSON.parse(ev.data as string);
      } catch {
        noteAnomaly('收到非 JSON 訊息');
        return;
      }

      const { type, turnId, payload = {} } = msg;

      switch (type) {
        case 'ready': {
          // BR3.5：必須驗證 protocolVersion，不符即視為協商失敗
          const got = payload.protocolVersion;
          if (got !== PROTOCOL_VERSION) {
            noteAnomaly(`ready 的 protocolVersion=${String(got)}，預期 ${PROTOCOL_VERSION}`);
            setConn('version-mismatch');
            setCloseReason(`協定版本不符：收到 ${String(got)}，預期 ${PROTOCOL_VERSION}`);
            ws.close();
            return;
          }
          setConn('ready');
          return;
        }

        case 'work_target':
          // 本 DEMO 不顯示脈絡列（U7／U14 的範圍），僅確認訊息到達
          return;

        case 'work_items':
          setWorkItems((payload.items as WorkItem[]) ?? []);
          return;

        case 'clarify':
          // AC1.2.1：信心不足 → 不建立工作項，列候選反問
          setCandidates((payload.candidates as Candidate[]) ?? []);
          return;

        case 'token': {
          const text = String(payload.text ?? '');
          if (!turnId) {
            noteAnomaly('token 缺少 turnId');
            return;
          }
          setTurns((prev) => {
            const idx = prev.findIndex((t) => t.turnId === turnId);
            if (idx === -1) {
              return [...prev, { turnId, text, state: 'streaming' }];
            }
            return prev.map((t, i) => (i === idx ? { ...t, text: t.text + text } : t));
          });
          return;
        }

        case 'done': {
          if (!turnId) {
            noteAnomaly('done 缺少 turnId');
            return;
          }
          setTurns((prev) => {
            const existing = prev.find((t) => t.turnId === turnId);
            // BR3.3：零內容的 done 是契約違規——顯示備援提示並記錄異常，不呈現空白成功態
            if (!existing || existing.text.trim() === '') {
              noteAnomaly(`收到零內容的 done（turnId=${turnId}）——契約違規，伺服器應送 error(EMPTY_RESPONSE)`);
              const violated: Turn = {
                turnId,
                text: existing?.text ?? '',
                state: 'contract-violation',
              };
              return existing
                ? prev.map((t) => (t.turnId === turnId ? violated : t))
                : [...prev, violated];
            }
            return prev.map((t) => (t.turnId === turnId ? { ...t, state: 'done' } : t));
          });
          return;
        }

        case 'error': {
          const code = String(payload.code ?? 'UNKNOWN');
          const message = String(payload.message ?? '');
          const id = String(payload.turnId ?? turnId ?? 'unknown');
          // BR3.1：四個 code 窮盡處理
          const known = ['EMPTY_RESPONSE', 'INTERNAL_ERROR', 'UNAUTHORIZED', 'INVALID_REQUEST'];
          if (!known.includes(code)) {
            noteAnomaly(`收到未知的 error.code=${code}（封閉列舉外）`);
          }
          setTurns((prev) => {
            const existing = prev.find((t) => t.turnId === id);
            const next: Turn = {
              turnId: id,
              text: existing?.text ?? '',
              state: 'error',
              errorCode: code,
              errorMessage: message,
            };
            return existing ? prev.map((t) => (t.turnId === id ? next : t)) : [...prev, next];
          });
          return;
        }

        default:
          // BR3.2：未知 type 安全忽略並記錄異常，不崩潰、不中斷該輪其餘訊息
          noteAnomaly(`收到未知的訊息型別：${String(type)}`);
          return;
      }
    };

    ws.onclose = (ev) => {
      if (cancelled) return;
      if (ev.code === 4400) {
        setConn('version-mismatch');
        setCloseReason(ev.reason || '協定版本不相容');
      } else if (ev.code === 4401 || ev.code === 4403) {
        setConn('unauthorized');
        setCloseReason(ev.reason || '認證或權限不足');
      } else {
        setConn('closed');
        setCloseReason(ev.reason || `連線關閉（code ${ev.code}）`);
      }
      // BR3.4：未收到終止事件的那一輪標為未完成，**不自動重試**
      setTurns((prev) =>
        prev.map((t) => (t.state === 'streaming' ? { ...t, state: 'incomplete' } : t))
      );
    };

    return () => {
      cancelled = true;
      ws.close();
    };
  }, [token, noteAnomaly]);

  const send = useCallback((obj: Record<string, unknown>) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    // 客戶端封包不含 turnId（BR2.13），不含任何身分欄位（BR2.12）
    ws.send(JSON.stringify({ v: PROTOCOL_VERSION, ...obj }));
  }, []);

  const submit = useCallback(() => {
    const text = input.trim();
    if (!text) return;
    setCandidates([]);
    send({ type: 'user_message', payload: { text } });
    setInput('');
  }, [input, send]);

  const pick = useCallback(
    (candidateId: string | null) => {
      setCandidates([]);
      send({ type: 'select_clarify_candidate', payload: { candidateId } });
    },
    [send]
  );

  const statusLine: Record<ConnState, string> = {
    idle: '準備中',
    connecting: '連線中…',
    ready: `已連線（協定 v${PROTOCOL_VERSION}）`,
    closed: `連線已關閉：${closeReason}`,
    'version-mismatch': `協定版本不相容：${closeReason}`,
    unauthorized: `無法連線：${closeReason}`,
  };

  return (
    <div className="mx-auto max-w-3xl p-6" data-testid="brain-page">
      <h1 className="text-2xl font-semibold">Cloud-360 大腦</h1>
      <p className="mt-1 text-sm text-gray-500">
        統一入口。DEMO 切片：意圖識別、逐字串流、信心不足時反問。
      </p>

      <div
        className={`mt-4 rounded px-3 py-2 text-sm ${
          conn === 'ready' ? 'bg-green-50 text-green-800' : 'bg-amber-50 text-amber-900'
        }`}
        data-testid="brain-conn-status"
      >
        {statusLine[conn]}
      </div>

      <div className="mt-4 flex gap-2">
        <input
          className="flex-1 rounded border px-3 py-2"
          placeholder="例：幫我畫一張訂單系統的架構圖"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') submit();
          }}
          disabled={conn !== 'ready'}
          data-testid="brain-input"
        />
        <button
          className="rounded bg-blue-600 px-4 py-2 text-white disabled:bg-gray-300"
          onClick={submit}
          disabled={conn !== 'ready' || !input.trim()}
          data-testid="brain-submit"
        >
          送出
        </button>
      </div>

      {candidates.length > 0 && (
        <div className="mt-4 rounded border border-amber-300 bg-amber-50 p-3" data-testid="brain-clarify">
          <p className="text-sm font-medium">我不太確定你要哪一個，請選一個：</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {candidates.map((c) => (
              <button
                key={c.id}
                className="rounded border bg-white px-3 py-1 text-sm"
                onClick={() => pick(c.id)}
                data-testid={`brain-candidate-${c.capability}`}
              >
                {c.label}
                {c.confidence !== null && (
                  <span className="ml-1 text-gray-400">{c.confidence.toFixed(2)}</span>
                )}
              </button>
            ))}
            <button
              className="rounded border border-gray-300 px-3 py-1 text-sm text-gray-600"
              onClick={() => pick(null)}
              data-testid="brain-candidate-none"
            >
              都不是，我再講一次
            </button>
          </div>
        </div>
      )}

      {workItems.length > 0 && (
        <div className="mt-4" data-testid="brain-work-items">
          <h2 className="text-sm font-medium text-gray-700">工作項</h2>
          <ul className="mt-1 space-y-1">
            {workItems.map((w) => (
              <li key={w.workItemId} className="rounded bg-gray-50 px-3 py-1 text-sm">
                <span className="font-medium">{w.status}</span> · {w.label}
                {w.failureReason && <span className="text-red-600"> · {w.failureReason}</span>}
                {w.sideEffect === 'unknown' && (
                  <span className="text-amber-700"> · 副作用未知</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 space-y-3" data-testid="brain-turns">
        {turns.map((t) => (
          <div key={t.turnId} className="rounded border p-3">
            <p className="whitespace-pre-wrap text-sm">{t.text}</p>
            {t.state === 'streaming' && (
              <p className="mt-1 text-xs text-blue-600" aria-busy="true">
                回覆中…
              </p>
            )}
            {t.state === 'error' && (
              <p className="mt-1 text-xs text-red-600">
                {t.errorCode === 'EMPTY_RESPONSE'
                  ? '這一輪沒有產出可呈現的回覆，請重新描述需求。'
                  : `錯誤（${t.errorCode}）：${t.errorMessage}`}
              </p>
            )}
            {t.state === 'incomplete' && (
              <p className="mt-1 text-xs text-amber-700">
                回覆未完成（連線中斷）。系統不會自動重試，請自行重問。
              </p>
            )}
            {t.state === 'contract-violation' && (
              <p className="mt-1 text-xs text-red-700">
                沒有收到回覆內容。這是伺服器端的契約違規，已記錄異常。
              </p>
            )}
          </div>
        ))}
      </div>

      {anomalies.length > 0 && (
        <details className="mt-6 rounded border border-red-200 bg-red-50 p-3" data-testid="brain-anomalies">
          <summary className="cursor-pointer text-sm font-medium text-red-800">
            契約異常記錄（{anomalies.length}）
          </summary>
          <ul className="mt-2 space-y-1 text-xs text-red-700">
            {anomalies.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

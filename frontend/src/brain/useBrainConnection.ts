/**
 * useBrainConnection — 一個頁面的大腦 WebSocket 連線（`BR92.x`；performance-design §一）
 *
 * **每頁一條**（`EPN-01`）：連線在**一個** effect 內建立；`WebSocket`、退避計時器、首次失敗時刻、
 * 連線 id 放在 `useRef`，只在 effect 的 setup／cleanup 與事件回呼內讀寫（render 期間不讀 ref）。
 *
 * cleanup 依序：清除退避計時器 → 把本連線未終止的輪次轉 interrupted（`BR93.7`）→ `ws.close(1000)` → ref 歸 null。
 * **不以 ref 去重**（`if (wsRef.current) return` 會讓 StrictMode 第二次 setup 沿用已被 cleanup 關閉的物件）；
 * 沒有任何在 effect 外建立連線的路徑（「重新連線」鈕只遞增 attempt 讓 effect 重跑）。
 *
 * 關閉碼（`BR92.5`，4403 依 security-design §六之二）：4401 → 需重新登入；4403 → 至多一次 `refreshMe()`、
 * **不導航**；4400 或 ready 版本不符 → 版本不相容；其他 → 退避重連，自第一次失敗起累計 60 秒放棄。
 * 三種終止碼都不排退避（`EPN-03`）。
 *
 * 重連成功後，伺服器推送的作業對象、工作項與共享模式**逐項取代**畫面上的值（`NFR4.140`）；對話紀錄保留。
 * console 只記 type、code、關閉碼（`BR92.8`、`EPN-14`）。
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { wsUrl } from '../config/api';
import { useAuth } from '../context/auth-context';
import {
  PROTOCOL_VERSION,
  classifyClose,
  clientFrame,
  delayFor,
  parseInbound,
  segmentFor,
  shouldGiveUp,
  subprotocols,
  type BrainPage,
  type SegmentId,
  type SharingMode,
  type WorkItem,
  type WorkTargetPayload,
} from './brainProtocol';
import { nextLocalId, useBrainTranscript, type TranscriptAction } from './brainTranscript';
import type {
  BrainConnection,
  ConnectionListeners,
  ConnectionStatus,
  WorkTargetIds,
} from './brainSession';
import type { components } from '../types/ws-contract';

type Schemas = components['schemas'];

const BRAIN_WS_PATH = '/api/brain/ws';

interface Options {
  enabled: boolean;
}

/**
 * 本連線**最後一次成功送出**的客戶端請求（code-generation review-02 R-08／R-09、`[EP-R2]`=A）。
 *
 * 非輪次錯誤（turnId=null）沒有可歸屬的識別，前端以「最後送出的是什麼」判斷它拒絕了誰：
 * - `user_message` 且之後本連線尚未收到任何輪次訊息（token／cost_card／clarify／done／帶 turnId 的 error）
 *   → 被拒的是那句原句：解除等待、標為未送達。
 * - `select_clarify_candidate` → 被拒的是反問選擇：本段 picking 的反問回 default。
 * - 其他 → 只插入系統提示。
 * 判定用過一次即歸為 `other`，後續無關的非輪次錯誤不再動到原句或反問。
 *
 * **非輪次請求不覆寫待決的標記**（object-picker-ui code-generation review-02 R-08，`[EP-R2]` 的細化）：
 * `set_work_target`／`set_sharing_mode`／`correct_work_item` 送出時，若標記仍是**尚未收到任何輪次訊息**的
 * `user_message` 或 `select_clarify_candidate`，標記保留；否則才歸為 `other`。依據：閘道對同一連線的訊框依序處理
 * （`brain_gateway.py` `_receive_loop` 逐則 await），被拒的原句或反問選擇，其 turnId=null 的 error 必然先於
 * 之後任何請求的回應到達；受理者則先送出該輪訊息（標記因此轉為已回應）。標記只在「該請求收到第一則輪次訊息」
 * 或「被一次非輪次錯誤的判定用掉」時解除，連線重建時歸零。
 */
type SentKind = 'user_message' | 'select_clarify_candidate' | 'other';

interface LastSent {
  kind: SentKind;
  /** kind 為 user_message 時，該則使用者原句的本地 id。 */
  userItemId: string | null;
  /** 送出後本連線是否已收到任何輪次訊息。 */
  answered: boolean;
}

const NOTHING_SENT: LastSent = { kind: 'other', userItemId: null, answered: true };

/** 非輪次請求送出後的標記：待決的 user_message／反問選擇保留，其餘歸為 `other`（R-08）。 */
function afterNonTurnSend(last: LastSent): LastSent {
  return !last.answered && last.kind !== 'other' ? last : NOTHING_SENT;
}

/** 零寬空白：螢幕閱讀器不念，但使相同文字的第二次播報仍是一次 DOM 內容變更（R-12）。 */
const REANNOUNCE_MARK = String.fromCharCode(0x200b);

export function useBrainConnection(page: BrainPage, { enabled }: Options): BrainConnection {
  const { token, refreshMe } = useAuth();
  const { dispatch } = useBrainTranscript();

  const [status, setStatus] = useState<ConnectionStatus>(() => (enabled ? 'connecting' : 'idle'));
  const [sharingMode, setSharingModeState] = useState<SharingMode | null>(null);
  const [target, setTarget] = useState<WorkTargetPayload | null>(null);
  const [workItems, setWorkItems] = useState<WorkItem[]>([]);
  const [pendingCorrections, setPendingCorrections] = useState<string[]>([]);
  const [awaitingReply, setAwaitingReply] = useState(false);
  const [announcement, setAnnouncement] = useState('');
  const [attempt, setAttempt] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const connIdRef = useRef<string | null>(null);
  const readySentRef = useRef(false);
  const readSegmentRef = useRef<SegmentId>(segmentFor(page, null));
  const targetsRef = useRef<Partial<Record<SegmentId, WorkTargetPayload>>>({});
  const turnTextRef = useRef<Map<string, string>>(new Map());
  const costTurnsRef = useRef<Set<string>>(new Set());
  const forbiddenRefreshedRef = useRef(false);
  const lastSentRef = useRef<LastSent>(NOTHING_SENT);
  const listenersRef = useRef<ConnectionListeners>({});
  const latestRef = useRef({ refreshMe, dispatch });

  useEffect(() => {
    latestRef.current = { refreshMe, dispatch };
  });

  useEffect(() => {
    if (!enabled || !token) return undefined;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let failures = 0;
    let firstFailureAt: number | null = null;
    let terminal = false;
    let connId = '';
    const accessToken = token;

    const act = (action: TranscriptAction) => latestRef.current.dispatch(action);

    // 錯誤播報：與目前播報文字相同時附一個不可見的零寬字元（再相同就拿掉），使連續兩則相同文字的錯誤
    // （例如重複被頻率限制）也會改變 LiveRegion 的 DOM 內容而被重新朗讀（code-generation review-02 R-12）。
    // 不用「先清空、下一個任務再寫入」：兩則錯誤若在計時器觸發前接連到達，清空會被合併掉，第二次仍無聲。
    // LiveRegion 元件簽章不動（其檔頭契約）；更新式為純函式，不就地修改任何物件。
    const announceFresh = (text: string) => {
      setAnnouncement((prev) => (prev === text ? `${text}${REANNOUNCE_MARK}` : text));
    };

    // 本連線收到任何輪次訊息：最後送出的 user_message 已被受理（不再視為可被非輪次錯誤拒絕）。
    const markAnswered = () => {
      if (!lastSentRef.current.answered) lastSentRef.current = { ...lastSentRef.current, answered: true };
    };

    const connect = () => {
      if (disposed) return;
      connId = nextLocalId('conn');
      readySentRef.current = false;
      lastSentRef.current = NOTHING_SENT;
      const ws = new WebSocket(wsUrl(BRAIN_WS_PATH), subprotocols(accessToken));
      wsRef.current = ws;
      connIdRef.current = connId;
      const myConnId = connId;

      ws.onopen = () => {
        if (disposed || wsRef.current !== ws) return;
        setStatus('awaiting-ready');
        ws.send(clientFrame('hello', { v: PROTOCOL_VERSION }));
      };

      ws.onmessage = (event: MessageEvent) => {
        if (disposed || wsRef.current !== ws) return;
        const parsed = parseInbound(event.data);
        if (parsed.kind === 'malformed') {
          console.warn('[brain] ignored malformed frame');
          return;
        }
        if (parsed.kind === 'unknown-type') {
          console.warn('[brain] ignored message type', parsed.type);
          return;
        }
        const env = parsed.envelope;
        const segment = readSegmentRef.current;
        switch (env.type) {
          case 'ready': {
            const payload = env.payload as Schemas['ReadyPayload'];
            if (payload.protocolVersion !== PROTOCOL_VERSION) {
              terminal = true;
              setStatus('version-mismatch');
              ws.close(1000);
              return;
            }
            failures = 0;
            firstFailureAt = null;
            readySentRef.current = true;
            // 重連後以伺服器推送覆蓋（NFR4.140）：快照緊接在 ready 之後到達。
            targetsRef.current = {};
            setTarget(null);
            setWorkItems([]);
            setPendingCorrections([]);
            setStatus('ready');
            listenersRef.current.onReady?.();
            return;
          }
          case 'token': {
            const payload = env.payload as Schemas['TokenPayload'];
            const turnId: unknown = env.turnId;
            // 輪次訊息缺 turnId 是契約違規：丟棄並記 type，不建空字串輪次（code-generation review-02 R-11）。
            if (typeof turnId !== 'string' || turnId === '') {
              console.warn('[brain] dropped frame without turnId', env.type);
              return;
            }
            markAnswered();
            turnTextRef.current.set(turnId, (turnTextRef.current.get(turnId) ?? '') + payload.text);
            act({ type: 'token', turnId, text: payload.text, segment, connId: myConnId, id: nextLocalId('brain') });
            return;
          }
          case 'cost_card': {
            const payload = env.payload as Schemas['CostCardPayload'];
            const turnId: unknown = env.turnId;
            if (typeof turnId !== 'string' || turnId === '') {
              console.warn('[brain] dropped frame without turnId', env.type);
              return;
            }
            markAnswered();
            costTurnsRef.current.add(turnId);
            act({ type: 'costCard', turnId, card: payload, segment, connId: myConnId, id: nextLocalId('brain') });
            return;
          }
          case 'done': {
            markAnswered();
            const turnId = env.turnId ?? (env.payload as Schemas['DonePayload']).turnId;
            act({ type: 'done', turnId, segment, connId: myConnId, id: nextLocalId('brain') });
            setAwaitingReply(false);
            // 完成時把整段寫入 LiveRegion 一次（BR93.6；寫入點只有這裡與 error）。
            const text = turnTextRef.current.get(turnId);
            const hadCard = costTurnsRef.current.delete(turnId);
            turnTextRef.current.delete(turnId);
            if (text && text.trim()) setAnnouncement(text);
            // 零內容的 done 是契約違規（BR93.2）：記一筆，只含 turnId。
            else if (!hadCard) console.warn('[brain] empty turn', turnId);
            return;
          }
          case 'error': {
            const payload = env.payload as Schemas['ErrorPayload'];
            // envelope 與 payload 都缺 turnId（undefined）一律視同 null（code-generation review-02 R-11）。
            const turnId: string | null | undefined = env.turnId ?? payload.turnId;
            if (turnId == null) {
              // 非輪次錯誤（合併前必修第 2 項(b)、`[EP-MB2]`=A）：一律在對話插入一則系統提示並播報，
              // 不清任何輪次的暫存文字。另依本連線「最後送出的請求」判斷它拒絕了誰（`[EP-R2]`=A）：
              // 未獲任何輪次訊息的 user_message → 解除等待、原句標為未送達；反問選擇 → 反問回 default；
              // 其他 → 只有提示，不動輪次、反問與等待狀態。
              const last = lastSentRef.current;
              const undeliveredUserId = last.kind === 'user_message' && !last.answered ? last.userItemId : null;
              const reopenPicking = last.kind === 'select_clarify_candidate';
              act({
                type: 'systemNotice',
                code: payload.code,
                message: payload.message,
                segment,
                id: nextLocalId('notice'),
                connId: myConnId,
                undeliveredUserId,
                reopenPicking,
              });
              if (undeliveredUserId !== null) setAwaitingReply(false);
              if (undeliveredUserId !== null || reopenPicking) lastSentRef.current = NOTHING_SENT;
              announceFresh(payload.message);
              return;
            }
            markAnswered();
            act({
              type: 'error',
              turnId,
              code: payload.code,
              message: payload.message,
              segment,
              connId: myConnId,
              id: nextLocalId('brain'),
            });
            setAwaitingReply(false);
            turnTextRef.current.delete(turnId);
            announceFresh(payload.message);
            return;
          }
          case 'clarify': {
            markAnswered();
            const payload = env.payload as Schemas['ClarifyPayload'];
            act({ type: 'clarify', turnId: env.turnId, payload, segment, connId: myConnId, id: nextLocalId('clarify') });
            // 反問後該輪等使用者選擇，伺服器此時不送 done：解除等待，讓使用者可回答或改說新句（BR95.5）。
            setAwaitingReply(false);
            return;
          }
          case 'work_items': {
            const payload = env.payload as Schemas['WorkItemsPayload'];
            setWorkItems(payload.items);
            setPendingCorrections([]);
            act({ type: 'anchorWorkItems', segment, workItemIds: payload.items.map((i) => i.workItemId) });
            act({ type: 'resolvePicking' });
            return;
          }
          case 'sharing_mode': {
            const payload = env.payload as Schemas['SharingModePayload'];
            // 入口頁忽略全部 sharing_mode；子頁面只套用 scope 相符者（BR92.4）。
            if (page === 'entry' || payload.scope !== page) return;
            const nextSegment = segmentFor(page, payload.mode);
            readSegmentRef.current = nextSegment;
            setSharingModeState(payload.mode);
            setTarget(targetsRef.current[nextSegment] ?? null);
            return;
          }
          case 'work_target': {
            const payload = env.payload as Schemas['WorkTargetPayload'];
            targetsRef.current = { ...targetsRef.current, [payload.segment]: payload };
            if (payload.segment !== readSegmentRef.current) return;
            setTarget(payload);
            listenersRef.current.onWorkTarget?.(payload);
            return;
          }
          default: {
            const exhaustive: never = env.type;
            console.warn('[brain] ignored message type', exhaustive);
          }
        }
      };

      ws.onclose = (event: CloseEvent) => {
        if (disposed || wsRef.current !== ws) return;
        wsRef.current = null;
        readySentRef.current = false;
        act({ type: 'interruptOpenTurns', connId: myConnId, reason: 'disconnect' });
        setAwaitingReply(false);
        if (terminal) return;
        const decision = classifyClose(event.code);
        if (decision === 'needs-login') {
          terminal = true;
          setStatus('needs-login');
          return;
        }
        if (decision === 'version-mismatch') {
          terminal = true;
          setStatus('version-mismatch');
          return;
        }
        if (decision === 'forbidden') {
          terminal = true;
          setStatus('forbidden');
          if (!forbiddenRefreshedRef.current) {
            forbiddenRefreshedRef.current = true;
            // 至多一次、失敗吞下；入口頁由 DefaultRedirect 依新權限重判，子頁面的掛點依 K1 卸載。
            latestRef.current.refreshMe().catch(() => undefined);
          }
          return;
        }
        console.warn('[brain] connection closed', event.code);
        const now = Date.now();
        if (firstFailureAt === null) firstFailureAt = now;
        if (shouldGiveUp(firstFailureAt, now)) {
          setStatus('gave-up');
          return;
        }
        const wait = delayFor(failures);
        failures += 1;
        setStatus('reconnecting');
        timer = setTimeout(() => {
          timer = null;
          setStatus('connecting');
          connect();
        }, wait);
      };
    };

    connect();

    return () => {
      disposed = true;
      if (timer !== null) clearTimeout(timer);
      timer = null;
      latestRef.current.dispatch({ type: 'interruptOpenTurns', connId, reason: 'unmount' });
      const ws = wsRef.current;
      wsRef.current = null;
      connIdRef.current = null;
      readySentRef.current = false;
      if (ws) ws.close(1000);
    };
  }, [enabled, token, page, attempt]);

  const sendFrame = useCallback((frame: string): boolean => {
    const ws = wsRef.current;
    if (!ws || !readySentRef.current || ws.readyState !== WebSocket.OPEN) return false;
    ws.send(frame);
    return true;
  }, []);

  const sendUserMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;
      const connId = connIdRef.current;
      if (!connId || !sendFrame(clientFrame('user_message', { text, page }))) return;
      const id = nextLocalId('user');
      lastSentRef.current = { kind: 'user_message', userItemId: id, answered: false };
      // 使用者輪次打上連線 id，供卸載或斷線時轉 interrupted（BR93.7、BR92.7）。
      dispatch({ type: 'appendUser', segment: readSegmentRef.current, id, text, connId });
      setAwaitingReply(true);
    },
    [dispatch, page, sendFrame],
  );

  const selectCandidate = useCallback(
    (groupId: string, candidateId: string | null) => {
      if (!sendFrame(clientFrame('select_clarify_candidate', { candidateId }))) return;
      lastSentRef.current = { kind: 'select_clarify_candidate', userItemId: null, answered: false };
      dispatch({ type: 'clarifyState', id: groupId, state: candidateId === null ? 'dismissed' : 'picking', pickedId: candidateId });
    },
    [dispatch, sendFrame],
  );

  const correctWorkItem = useCallback(
    (workItemId: string) => {
      if (!sendFrame(clientFrame('correct_work_item', { workItemId }))) return;
      lastSentRef.current = afterNonTurnSend(lastSentRef.current);
      setPendingCorrections((prev) => (prev.includes(workItemId) ? prev : [...prev, workItemId]));
    },
    [sendFrame],
  );

  const setSharingMode = useCallback(
    (mode: SharingMode) => {
      if (page === 'entry') return; // 入口頁不送 set_sharing_mode（BR92.3）
      if (sendFrame(clientFrame('set_sharing_mode', { mode, scope: page }))) {
        lastSentRef.current = afterNonTurnSend(lastSentRef.current);
      }
    },
    [page, sendFrame],
  );

  const setWorkTarget = useCallback((ids: WorkTargetIds): boolean => {
    const sent = sendFrame(clientFrame('set_work_target', { ...ids, segment: readSegmentRef.current }));
    if (sent) lastSentRef.current = afterNonTurnSend(lastSentRef.current);
    return sent;
  }, [sendFrame]);

  const announce = useCallback((text: string) => setAnnouncement(text), []);

  const subscribe = useCallback((listeners: ConnectionListeners) => {
    listenersRef.current = listeners;
    return () => {
      if (listenersRef.current === listeners) listenersRef.current = {};
    };
  }, []);

  const reconnect = useCallback(() => {
    setStatus('connecting');
    setAttempt((n) => n + 1);
  }, []);

  return {
    page,
    enabled,
    status: enabled && status === 'idle' ? 'connecting' : status,
    readSegment: segmentFor(page, sharingMode),
    sharingMode: page === 'entry' ? null : sharingMode,
    target,
    workItems,
    pendingCorrections,
    awaitingReply,
    announcement,
    sendUserMessage,
    selectCandidate,
    correctWorkItem,
    setSharingMode,
    setWorkTarget,
    announce,
    reconnect,
    subscribe,
  };
}

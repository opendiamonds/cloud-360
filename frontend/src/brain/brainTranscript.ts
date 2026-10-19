/**
 * brainTranscript.ts — 對話紀錄 store 的 context、型別、hook 與純 reducer（`BR93.x`；`[EP4]`=A）
 *
 * Provider 元件在 `BrainTranscriptContext.tsx`（`react-refresh/only-export-components`：元件與
 * 非元件匯出分檔）。
 *
 * **只在記憶體**：不寫 localStorage／sessionStorage／IndexedDB（`EPN-13`、ADR-0006 加密面）。
 * 重新整理、開新分頁、登入或登出即清空（清空由登入／登出事件觸發，security-design §六之一）。
 *
 * **對照只記段**（performance-design §二之二）：`turnSegment: Record<turnId, SegmentId>`；位置在該段
 * `items` 內以 turnId 線性搜尋（≤ 500 筆）。若記「段＋索引」，截斷最舊一則後所有索引減一，下一個
 * token 會寫進錯的訊息（`EPN-05`）。
 *
 * 四個主要動作沿用設計的名稱：`append`（新增一則；滿 500 則先擠掉最舊者）、`updateTurn`（依 turnId
 * 找到原訊息更新；找不到即視為首見，依 BR93.5 在接收頁目前讀取的段新建）、`interruptOpenTurns`
 * （卸載或斷線時把本連線未終止的輪次轉 interrupted，BR93.7／BR92.7）、`reset`。其餘動作
 * （反問狀態、工作項錨點、使用者輪次的等待旗標）都是這四者之上的小變形。reducer 一律回傳新物件。
 */

import { createContext, useContext, type Dispatch } from 'react';
import type { ClarifyPayload, CostCardPayload, ErrorCode, SegmentId } from './brainProtocol';

export const TRANSCRIPT_MAX_PER_SEGMENT = 500;

export const SEGMENT_IDS: readonly SegmentId[] = ['shared', 'workspace', 'assessment'];

export const PENDING_ANCHOR = '__next-brain__';

export type BrainTurnStatus = 'streaming' | 'done' | 'empty' | 'error' | 'interrupted';
export type ClarifyState = 'default' | 'picking' | 'dismissed' | 'stale' | 'resolved';
export type InterruptReason = 'disconnect' | 'unmount';

export interface UserItem {
  kind: 'user';
  id: string;
  text: string;
  /** 送出它的連線；任一輪終止或連線關閉即清為 null（BR93.3）。 */
  pendingConnId: string | null;
  interrupted: InterruptReason | null;
  retried: boolean;
}

export interface BrainItem {
  kind: 'brain';
  id: string;
  turnId: string;
  text: string;
  status: BrainTurnStatus;
  errorMessage: string | null;
  errorCode: ErrorCode | null;
  costCard: CostCardPayload | null;
  connId: string | null;
  interruptReason: InterruptReason | null;
  /** 重試時重送的原句（建立當下該段最後一則使用者原句）。 */
  retryText: string | null;
  retried: boolean;
}

export interface ClarifyItem {
  kind: 'clarify';
  id: string;
  turnId: string | null;
  payload: ClarifyPayload;
  state: ClarifyState;
  pickedId: string | null;
}

export type TranscriptItem = UserItem | BrainItem | ClarifyItem;

export interface SegmentTranscript {
  items: TranscriptItem[];
  truncated: boolean;
  /**
   * workItemId → 錨點大腦訊息的 id（BR94.5）。首次出現時該段最後一則是大腦訊息 → 錨定它；最後一則是
   * 使用者原句（該輪的回覆尚未到——伺服器在交辦時先送 work_items 再送 token）→ 暫記 `PENDING_ANCHOR`，
   * 由該段下一則新建的大腦訊息承接；該段沒有任何項目時為 ''（列在最後）。
   */
  anchors: Record<string, string>;
}

export interface TranscriptState {
  segments: Record<SegmentId, SegmentTranscript>;
  turnSegment: Record<string, SegmentId>;
}

export type TranscriptAction =
  | { type: 'appendUser'; segment: SegmentId; id: string; text: string; connId: string }
  | { type: 'token'; turnId: string; text: string; segment: SegmentId; connId: string; id: string }
  | { type: 'costCard'; turnId: string; card: CostCardPayload; segment: SegmentId; connId: string; id: string }
  | { type: 'done'; turnId: string; segment: SegmentId; connId: string; id: string }
  | {
      type: 'error';
      turnId: string;
      code: ErrorCode;
      message: string;
      segment: SegmentId;
      connId: string;
      id: string;
    }
  | { type: 'clarify'; turnId: string | null; payload: ClarifyPayload; segment: SegmentId; connId: string; id: string }
  | { type: 'clarifyState'; id: string; state: ClarifyState; pickedId?: string | null }
  | { type: 'resolvePicking' }
  | { type: 'anchorWorkItems'; segment: SegmentId; workItemIds: string[] }
  | { type: 'retried'; id: string }
  | { type: 'interruptOpenTurns'; connId: string; reason: InterruptReason }
  | { type: 'reset' };

function emptySegment(): SegmentTranscript {
  return { items: [], truncated: false, anchors: {} };
}

export function initialTranscriptState(): TranscriptState {
  return {
    segments: { shared: emptySegment(), workspace: emptySegment(), assessment: emptySegment() },
    turnSegment: {},
  };
}

function turnIdOf(item: TranscriptItem): string | null {
  return item.kind === 'brain' ? item.turnId : null;
}

/** `append`：滿 500 則先擠掉最舊一則（並同步刪除它的 turnId 對照），再附加。 */
function append(state: TranscriptState, segment: SegmentId, item: TranscriptItem): TranscriptState {
  const seg = state.segments[segment];
  let items = seg.items;
  let truncated = seg.truncated;
  let turnSegment = state.turnSegment;
  if (items.length >= TRANSCRIPT_MAX_PER_SEGMENT) {
    const removed = items[0];
    items = items.slice(1);
    truncated = true;
    const removedTurn = turnIdOf(removed);
    if (removedTurn !== null && turnSegment[removedTurn] === segment) {
      turnSegment = { ...turnSegment };
      delete turnSegment[removedTurn];
    }
  }
  items = [...items, item];
  const newTurn = turnIdOf(item);
  if (newTurn !== null) turnSegment = { ...turnSegment, [newTurn]: segment };
  return {
    segments: { ...state.segments, [segment]: { ...seg, items, truncated } },
    turnSegment,
  };
}

function mapItems(
  state: TranscriptState,
  fn: (item: TranscriptItem, segment: SegmentId) => TranscriptItem,
): TranscriptState {
  const segments = { ...state.segments };
  for (const segment of SEGMENT_IDS) {
    const seg = state.segments[segment];
    let changed = false;
    const items = seg.items.map((item) => {
      const next = fn(item, segment);
      if (next !== item) changed = true;
      return next;
    });
    if (changed) segments[segment] = { ...seg, items };
  }
  return { ...state, segments };
}

function lastUserText(seg: SegmentTranscript): string | null {
  for (let i = seg.items.length - 1; i >= 0; i -= 1) {
    const item = seg.items[i];
    if (item.kind === 'user') return item.text;
  }
  return null;
}

function newBrainItem(state: TranscriptState, segment: SegmentId, id: string, turnId: string, connId: string): BrainItem {
  return {
    kind: 'brain',
    id,
    turnId,
    text: '',
    status: 'streaming',
    errorMessage: null,
    errorCode: null,
    costCard: null,
    connId,
    interruptReason: null,
    retryText: lastUserText(state.segments[segment]),
    retried: false,
  };
}

/**
 * `updateTurn`：依 turnId 找到原訊息（跨段，BR93.7）套用 patch；找不到（首見，或已被截斷移除，
 * EPN-05）→ 在 `fallbackSegment`（接收頁目前讀取的段，BR93.5）新建一則再套用。
 */
function updateTurn(
  state: TranscriptState,
  turnId: string,
  fallbackSegment: SegmentId,
  connId: string,
  newId: string,
  patch: (item: BrainItem) => BrainItem,
): TranscriptState {
  const segment = state.turnSegment[turnId];
  if (segment !== undefined) {
    const seg = state.segments[segment];
    const index = seg.items.findIndex((item) => item.kind === 'brain' && item.turnId === turnId);
    if (index >= 0) {
      const items = seg.items.slice();
      items[index] = patch(items[index] as BrainItem);
      return { ...state, segments: { ...state.segments, [segment]: { ...seg, items } } };
    }
  }
  const created = newBrainItem(state, fallbackSegment, newId, turnId, connId);
  const appended = append(state, fallbackSegment, patch(created));
  // 等待中的工作項錨點由這則新建的大腦訊息承接（BR94.5）。
  const seg = appended.segments[fallbackSegment];
  if (!Object.values(seg.anchors).includes(PENDING_ANCHOR)) return appended;
  const anchors = Object.fromEntries(
    Object.entries(seg.anchors).map(([id, anchor]) => [id, anchor === PENDING_ANCHOR ? created.id : anchor]),
  );
  return { ...appended, segments: { ...appended.segments, [fallbackSegment]: { ...seg, anchors } } };
}

/** 任一輪終止（或反問）即解除該連線上使用者輪次的等待旗標（BR93.3，以「任一輪終止」近似，OPEN-EP14-4）。 */
function clearPending(state: TranscriptState, connId: string): TranscriptState {
  return mapItems(state, (item) =>
    item.kind === 'user' && item.pendingConnId === connId ? { ...item, pendingConnId: null } : item,
  );
}

function resolvePicking(state: TranscriptState): TranscriptState {
  return mapItems(state, (item) =>
    item.kind === 'clarify' && item.state === 'picking' ? { ...item, state: 'resolved' } : item,
  );
}

export function transcriptReducer(state: TranscriptState, action: TranscriptAction): TranscriptState {
  switch (action.type) {
    case 'appendUser': {
      // 候選未決時送出新句 → 舊組轉 stale（BR95.5）。
      const staled = mapItems(state, (item, segment) =>
        segment === action.segment && item.kind === 'clarify' && item.state === 'default'
          ? { ...item, state: 'stale' }
          : item,
      );
      return append(staled, action.segment, {
        kind: 'user',
        id: action.id,
        text: action.text,
        pendingConnId: action.connId,
        interrupted: null,
        retried: false,
      });
    }
    case 'token': {
      const next = updateTurn(resolvePicking(state), action.turnId, action.segment, action.connId, action.id, (item) => ({
        ...item,
        text: item.text + action.text,
        // interrupted 的 turnId 又收到後續 → 回到 streaming（BR93.7）。
        status: item.status === 'interrupted' || item.status === 'streaming' ? 'streaming' : item.status,
        interruptReason: item.status === 'interrupted' ? null : item.interruptReason,
        connId: action.connId,
      }));
      return next;
    }
    case 'costCard':
      return updateTurn(resolvePicking(state), action.turnId, action.segment, action.connId, action.id, (item) => ({
        ...item,
        costCard: action.card,
        status: item.status === 'interrupted' ? 'streaming' : item.status,
        interruptReason: item.status === 'interrupted' ? null : item.interruptReason,
        connId: action.connId,
      }));
    case 'done': {
      const known = state.turnSegment[action.turnId] !== undefined;
      const hasClarify = SEGMENT_IDS.some((s) =>
        state.segments[s].items.some((item) => item.kind === 'clarify' && item.turnId === action.turnId),
      );
      let next = clearPending(resolvePicking(state), action.connId);
      if (!known && hasClarify) return next; // 該輪只有反問：不另建空白訊息
      next = updateTurn(next, action.turnId, action.segment, action.connId, action.id, (item) => ({
        ...item,
        // 零內容的 done 是契約違規（BR93.2）：轉 empty，不留空白訊息。
        status: item.text.trim() || item.costCard ? 'done' : 'empty',
        interruptReason: null,
      }));
      return next;
    }
    case 'error':
      return updateTurn(
        clearPending(resolvePicking(state), action.connId),
        action.turnId,
        action.segment,
        action.connId,
        action.id,
        (item) => ({
          ...item,
          status: 'error',
          errorMessage: action.message,
          errorCode: action.code,
          interruptReason: null,
        }),
      );
    case 'clarify': {
      const next = clearPending(resolvePicking(state), action.connId);
      return append(next, action.segment, {
        kind: 'clarify',
        id: action.id,
        turnId: action.turnId,
        payload: action.payload,
        state: 'default',
        pickedId: null,
      });
    }
    case 'clarifyState':
      return mapItems(state, (item) =>
        item.kind === 'clarify' && item.id === action.id
          ? { ...item, state: action.state, pickedId: action.pickedId ?? item.pickedId }
          : item,
      );
    case 'resolvePicking':
      return resolvePicking(state);
    case 'anchorWorkItems': {
      const seg = state.segments[action.segment];
      const last = seg.items[seg.items.length - 1];
      const anchor = !last ? '' : last.kind === 'brain' ? last.id : last.kind === 'user' ? PENDING_ANCHOR : last.id;
      let anchors = seg.anchors;
      for (const id of action.workItemIds) {
        if (anchors[id] === undefined) {
          if (anchors === seg.anchors) anchors = { ...seg.anchors };
          anchors[id] = anchor;
        }
      }
      if (anchors === seg.anchors) return state;
      return { ...state, segments: { ...state.segments, [action.segment]: { ...seg, anchors } } };
    }
    case 'retried':
      return mapItems(state, (item) =>
        (item.kind === 'brain' || item.kind === 'user') && item.id === action.id ? { ...item, retried: true } : item,
      );
    case 'interruptOpenTurns': {
      const segments = { ...state.segments };
      for (const segment of SEGMENT_IDS) {
        const seg = state.segments[segment];
        let changed = false;
        const items = seg.items.map((item, index) => {
          if (item.kind === 'brain' && item.connId === action.connId && item.status === 'streaming') {
            changed = true;
            return { ...item, status: 'interrupted' as const, interruptReason: action.reason };
          }
          if (item.kind === 'user' && item.pendingConnId === action.connId) {
            changed = true;
            // 其後已有大腦訊息（它會自己轉 interrupted 並帶重試）→ 只清等待旗標，避免同一輪兩個重試鈕。
            const answered = seg.items.slice(index + 1).some((later) => later.kind === 'brain');
            return { ...item, pendingConnId: null, interrupted: answered ? null : action.reason };
          }
          return item;
        });
        if (changed) segments[segment] = { ...seg, items };
      }
      return { ...state, segments };
    }
    case 'reset':
      return initialTranscriptState();
    default: {
      const exhaustive: never = action;
      return exhaustive;
    }
  }
}

export interface BrainTranscriptValue {
  state: TranscriptState;
  dispatch: Dispatch<TranscriptAction>;
}

export const BrainTranscriptContextObject = createContext<BrainTranscriptValue | undefined>(undefined);

export function useBrainTranscript(): BrainTranscriptValue {
  const value = useContext(BrainTranscriptContextObject);
  if (!value) throw new Error('useBrainTranscript must be used within a BrainTranscriptProvider');
  return value;
}

let localSeq = 0;
/** 畫面用的本地 id（不是 turnId、不送伺服器）。 */
export function nextLocalId(prefix: string): string {
  localSeq += 1;
  return `${prefix}-${localSeq}`;
}

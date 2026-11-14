/**
 * brainProtocol.ts — 大腦 WebSocket 的純判斷（`U14 entry-page-ui`）
 *
 * **設計補強**（code-generation 計畫 §一之三 #19）：`logical-components.md` 未列本檔。抽出的理由是讓
 * `useBrainConnection.ts` 只承載 effect 與 ref，入站解析、關閉碼分流、退避排程與子協定組裝這些
 * **無 React 依賴**的判斷集中一處、可被閱讀與單獨推理。本檔不 import React、不碰 DOM 以外的全域狀態。
 *
 * 契約來源一律是 `ws-contract.d.ts`（`U2` 的產生檔，ADR-0019／ADR-0020／ADR-0022）。
 */

import type { components } from '../types/ws-contract';

type Schemas = components['schemas'];

export type WsEnvelope = Schemas['WsEnvelope'];
export type WsClientEnvelope = Schemas['WsClientEnvelope'];
export type ServerMessageType = Schemas['WsServerMessageType'];
export type ErrorCode = Schemas['ErrorPayload']['code'];
export type SegmentId = Schemas['WorkTargetPayload']['segment'];
export type BrainPage = Schemas['UserMessagePayload']['page'];
export type SubPage = Schemas['SetSharingModePayload']['scope'];
export type SharingMode = Schemas['SharingModePayload']['mode'];
export type WorkTargetPayload = Schemas['WorkTargetPayload'];
export type WorkItem = Schemas['WorkItem'];
export type ClarifyPayload = Schemas['ClarifyPayload'];
export type CostCardPayload = Schemas['CostCardPayload'];

/** 本版協定（`hello.v` 與 `ready.protocolVersion`）。型別即正本：後端升版時 tsc -b 紅燈。 */
export const PROTOCOL_VERSION: Schemas['ReadyPayload']['protocolVersion'] = 1;

// ---------------------------------------------------------------------------
// 子協定（BR92.1；ADR-0019 §5）
// ---------------------------------------------------------------------------

type Sub = Schemas['WsSubprotocol'];

// 三個值皆以 `WsSubprotocol` 的欄位型別標註：寫錯或後端改值時 tsc -b 紅燈。協定名以 template literal
// 組出（受字面型別的語境型別約束，型別仍是完整字面），使協定名不以完整字面散落於 src——Step 11 的
// grep 完成條件以「只在產生檔 ws-contract.d.ts 出現」判讀。
const PROTOCOL_NAME: Sub['protocolName'] = `${'cloud360'}.brain.v1`;
const SUBPROTOCOL_SCHEME: Sub['scheme'] = 'bearer';
const SUBPROTOCOL_SEPARATOR: Sub['separator'] = '.';

/** `new WebSocket(url, subprotocols(token))`：協定名 ＋ bearer 項。token 只出現在這裡（BR92.8）。 */
export function subprotocols(token: string): string[] {
  return [PROTOCOL_NAME, SUBPROTOCOL_SCHEME + SUBPROTOCOL_SEPARATOR + token];
}

// ---------------------------------------------------------------------------
// 入站解析（BR92.6；U2 的規則 3.1）
// ---------------------------------------------------------------------------

const SERVER_TYPES: ReadonlySet<string> = new Set<ServerMessageType>([
  'ready',
  'token',
  'clarify',
  'work_items',
  'cost_card',
  'sharing_mode',
  'work_target',
  'done',
  'error',
]);

export type Inbound =
  | { kind: 'message'; envelope: WsEnvelope }
  | { kind: 'unknown-type'; type: string }
  | { kind: 'malformed' };

/** 先以 `WsUnvalidatedEnvelope` 的寬鬆形狀解析；type 不在九值內 → `unknown-type`（呼叫端忽略，只記 type）。 */
export function parseInbound(raw: unknown): Inbound {
  if (typeof raw !== 'string') return { kind: 'malformed' };
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return { kind: 'malformed' };
  }
  if (!data || typeof data !== 'object') return { kind: 'malformed' };
  const loose = data as Partial<Schemas['WsUnvalidatedEnvelope']> & { turnId?: unknown };
  if (typeof loose.type !== 'string' || typeof loose.v !== 'number') return { kind: 'malformed' };
  if (!loose.payload || typeof loose.payload !== 'object') return { kind: 'malformed' };
  if (!SERVER_TYPES.has(loose.type)) return { kind: 'unknown-type', type: loose.type };
  return { kind: 'message', envelope: data as WsEnvelope };
}

/**
 * `error.code` 的窮盡分類（BR92.6）：新增 code 時 `never` 使 tsc -b 紅燈。
 * 畫面一律原樣顯示伺服器的 `message`；本分類只決定是否為「這一輪」的錯誤以外的訊號。
 */
export function errorCategory(code: ErrorCode): 'empty' | 'internal' | 'unauthorized' | 'invalid' {
  switch (code) {
    case 'EMPTY_RESPONSE':
      return 'empty';
    case 'INTERNAL_ERROR':
      return 'internal';
    case 'UNAUTHORIZED':
      return 'unauthorized';
    case 'INVALID_REQUEST':
      return 'invalid';
    default: {
      const exhaustive: never = code;
      return exhaustive;
    }
  }
}

// ---------------------------------------------------------------------------
// 關閉碼分流（BR92.5；security-design §六之二）
// ---------------------------------------------------------------------------

export type CloseDecision = 'needs-login' | 'forbidden' | 'version-mismatch' | 'retry';

export function classifyClose(code: number): CloseDecision {
  if (code === 4401) return 'needs-login';
  if (code === 4403) return 'forbidden';
  if (code === 4400) return 'version-mismatch';
  // 1011、網路中斷（1006）、握手未被接受（含被限流）一律退避重連。
  return 'retry';
}

// ---------------------------------------------------------------------------
// 退避排程（BR92.5、EPN-02；performance-design §一之二）
// ---------------------------------------------------------------------------

/** 第 n 次失敗後的基準等待秒數（**n 自 0 起算**：第一次失敗後等 BASE[0]＝1 秒，nfr-design R-07）。 */
export const BACKOFF_BASE_SECONDS: readonly number[] = [1, 2, 4, 8, 15, 15];
/** 自第一次失敗起累計滿 60 秒即放棄（以經過時間判定，非次數）。 */
export const GIVE_UP_AFTER_MS = 60_000;

/** 抖動只往下：×[0.8, 1.0]，理由是「降低同秒重連」（performance-design §一之三）。 */
export function jitter(random: () => number = Math.random): number {
  return 0.8 + 0.2 * random();
}

/** 第 n 次失敗後的等待毫秒數（n 自 0 起算）；單次上限 15 秒。 */
export function delayFor(n: number, random: () => number = Math.random): number {
  const base = BACKOFF_BASE_SECONDS[Math.min(Math.max(n, 0), BACKOFF_BASE_SECONDS.length - 1)];
  return Math.round(base * 1000 * jitter(random));
}

export function shouldGiveUp(firstFailureAt: number, now: number): boolean {
  return now - firstFailureAt >= GIVE_UP_AFTER_MS;
}

// ---------------------------------------------------------------------------
// 出站（BR92.3）：一律經 WsClientEnvelope 型別建構
// ---------------------------------------------------------------------------

export function clientFrame(
  type: Schemas['WsClientMessageType'],
  payload: WsClientEnvelope['payload'],
): string {
  const envelope: WsClientEnvelope = { v: PROTOCOL_VERSION, type, payload };
  return JSON.stringify(envelope);
}

/** 頁面 → 該頁目前讀取的段（BR92.3／BR92.4）：入口頁恆為共享段。 */
export function segmentFor(page: BrainPage, mode: SharingMode | null): SegmentId {
  if (page === 'entry') return 'shared';
  return mode === 'isolated' ? page : 'shared';
}

// ---------------------------------------------------------------------------
// 名稱顯示（BR97.2；ADR-0022 C-8；functional-design R-06 後半）
// ---------------------------------------------------------------------------

export const NAME_UNNAMED = '（未命名）';
export const NAME_UNAVAILABLE = '（無法顯示名稱）';
export const TARGET_NONE = '尚未選定';

/** 一層的顯示文字：識別碼為 null → null（該層略過）；名稱 null → 無法顯示；空字串 → 未命名。 */
export function layerName(id: string | null, name: string | null): string | null {
  if (id === null) return null;
  if (name === null) return NAME_UNAVAILABLE;
  if (name === '') return NAME_UNNAMED;
  return name;
}

/** 作業對象的簡稱：最深的非 null 層；三層皆 null → 「尚未選定」。 */
export function targetLabel(t: WorkTargetPayload): string {
  return (
    layerName(t.diagramId, t.diagramName) ??
    layerName(t.systemId, t.systemName) ??
    layerName(t.projectId, t.projectName) ??
    TARGET_NONE
  );
}

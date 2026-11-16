/**
 * wsFrames.ts — e2e 用的型別化伺服器訊框建構器（`BR98.4`；functional-design R-01、R-04）
 *
 * **為何放在 `src` 之下**：`frontend/tests` 不在任何 tsconfig 內（`tsconfig.app.json` 只 include `src`），
 * e2e spec 本身不受 `tsc -b` 檢查。訊框的欄位名與形狀全部在這裡以 `components['schemas']` 的型別逐欄組出，
 * 由既有的 `npm run build` 檢查——契約欄位改名或增減時，這裡紅燈（突變 C3）。
 *
 * **只收原始型別引數**（R-04）：每個建構函式內先宣告具名的 payload 型別再放進 envelope。直接把物件字面量
 * 放進 `WsEnvelope.payload`（無判別的聯集）可能被聯集中別的成員收下，欄位漂移就不會紅燈。
 *
 * spec 只能呼叫本檔的匯出函式取得要送出的字串；spec 內手寫含 `type` 與 `payload` 鍵的物件字面量會被
 * `eslint.config.js` 的 tests 區塊擋下（`EPN-19`）。
 *
 * 本模組**不被任何 app 程式 import**（不進生產 bundle），且不 import 任何 vite 專屬 API。
 */

import type { components } from '../../types/ws-contract';

type S = components['schemas'];
export type WsEnvelope = S['WsEnvelope'];
type WorkItem = S['WorkItem'];
type Segment = S['WorkTargetPayload']['segment'];
type Scope = S['SharingModePayload']['scope'];
type Mode = S['SharingModePayload']['mode'];
type Status = S['WorkItem']['status'];
type ErrorCode = S['ErrorPayload']['code'];
type ClarifyKind = S['ClarifyPayload']['kind'];

const V: S['WsEnvelope']['v'] = 1;

export function encodeFrame(env: WsEnvelope): string {
  return JSON.stringify(env);
}

export function readyFrame(): WsEnvelope {
  const payload: S['ReadyPayload'] = { protocolVersion: 1 };
  return { v: V, type: 'ready', turnId: null, payload };
}

export function tokenFrame(turnId: string, text: string): WsEnvelope {
  const payload: S['TokenPayload'] = { text };
  return { v: V, type: 'token', turnId, payload };
}

export function doneFrame(turnId: string): WsEnvelope {
  const payload: S['DonePayload'] = { turnId };
  return { v: V, type: 'done', turnId, payload };
}

/** `turnId` 為 null 即非輪次錯誤（BR1.5／BR1.6：envelope 與 payload 兩份同為 null）。 */
export function errorFrame(turnId: string | null, code: ErrorCode, message: string): WsEnvelope {
  const payload: S['ErrorPayload'] = { code, message, turnId };
  return { v: V, type: 'error', turnId, payload };
}

/** 候選以 `[id, label, capability]` 三元組傳入；信心值固定給 0.42（畫面不得顯示，BR95.3）。 */
export function clarifyFrame(
  turnId: string,
  kind: ClarifyKind,
  candidates: ReadonlyArray<readonly [string, string, string]>,
): WsEnvelope {
  const list: S['ClarifyCandidate'][] = candidates.map(([id, label, capability]) => {
    const candidate: S['ClarifyCandidate'] = { id, label, capability, confidence: 0.42 };
    return candidate;
  });
  const payload: S['ClarifyPayload'] = { kind, candidates: list };
  return { v: V, type: 'clarify', turnId, payload };
}

/** 單一工作項（只收原始型別）。供 `workItemsFrame` 組合。 */
export function workItem(
  workItemId: string,
  label: string,
  status: Status,
  capability: string = 'architecture-design',
  waitingOn: string | null = null,
  failureReason: string | null = null,
  sideEffect: string = 'none',
): WorkItem {
  const item: WorkItem = { workItemId, label, status, capability, waitingOn, failureReason, sideEffect };
  return item;
}

export function workItemsFrame(...items: WorkItem[]): WsEnvelope {
  const payload: S['WorkItemsPayload'] = { items };
  return { v: V, type: 'work_items', turnId: null, payload };
}

export function costCardFrame(
  turnId: string,
  estimateSetId: number,
  savingText: string | null,
  comparisonText: string | null,
  qualityText: string | null,
  unavailableKeys: readonly string[] | null,
  costPageUrl: string,
): WsEnvelope {
  const unavailableReasons: S['CostCardPayload']['unavailableReasons'] =
    unavailableKeys === null ? null : Object.fromEntries(unavailableKeys.map((k) => [k, '無法取價']));
  const payload: S['CostCardPayload'] = {
    estimateSetId,
    savingText,
    comparisonText,
    qualityText,
    unavailableReasons,
    costPageUrl,
  };
  return { v: V, type: 'cost_card', turnId, payload };
}

export function sharingModeFrame(scope: Scope, mode: Mode): WsEnvelope {
  const payload: S['SharingModePayload'] = { scope, mode };
  return { v: V, type: 'sharing_mode', turnId: null, payload };
}

export function workTargetFrame(
  segment: Segment,
  projectId: string | null,
  systemId: string | null,
  diagramId: string | null,
  projectName: string | null,
  systemName: string | null,
  diagramName: string | null,
): WsEnvelope {
  const payload: S['WorkTargetPayload'] = {
    segment,
    projectId,
    systemId,
    diagramId,
    projectName,
    systemName,
    diagramName,
  };
  return { v: V, type: 'work_target', turnId: null, payload };
}

export function emptyTargetFrame(segment: Segment): WsEnvelope {
  return workTargetFrame(segment, null, null, null, null, null, null);
}

// ---------------------------------------------------------------------------
// 情境序列（回傳已編碼的字串陣列，spec 逐一 send）
// ---------------------------------------------------------------------------

/**
 * 握手快照：ready → 兩則 sharing_mode → 共享段（與獨立段）的 work_target → work_items。
 * 與 `brain_gateway._snapshot_envelopes` 的順序相同。
 */
export function snapshotFrames(
  sharedTarget: WsEnvelope = emptyTargetFrame('shared'),
  items: readonly WorkItem[] = [],
  workspaceMode: Mode = 'shared',
  assessmentMode: Mode = 'shared',
  isolatedTargets: readonly WsEnvelope[] = [],
): string[] {
  return [
    readyFrame(),
    sharingModeFrame('workspace', workspaceMode),
    sharingModeFrame('assessment', assessmentMode),
    sharedTarget,
    ...isolatedTargets,
    workItemsFrame(...items),
  ].map(encodeFrame);
}

/** 一輪完整回覆：逐個 token，最後 done。 */
export function turnFrames(turnId: string, ...texts: string[]): string[] {
  return [...texts.map((t) => tokenFrame(turnId, t)), doneFrame(turnId)].map(encodeFrame);
}

/** 協定版本不符的 ready（以寬鬆封包型別組出；`ReadyPayload.protocolVersion` 的字面型別容不下它）。 */
export function readyWithVersionFrame(protocolVersion: number): string {
  const loose: S['WsUnvalidatedEnvelope'] = { v: 1, type: 'ready', payload: { protocolVersion } };
  return JSON.stringify(loose);
}

/**
 * envelope 與 payload 都缺 `turnId` 鍵的 error（契約違規；客戶端應視同 turnId=null 的非輪次錯誤，
 * code-generation review-02 R-11）。以寬鬆封包型別組出：`WsEnvelope` 的 turnId 為必填鍵。
 */
export function errorFrameWithoutTurnId(code: ErrorCode, message: string): string {
  const loose: S['WsUnvalidatedEnvelope'] = { v: 1, type: 'error', payload: { code, message } };
  return JSON.stringify(loose);
}

/** 缺 `turnId` 鍵的 token（契約違規；客戶端應丟棄，不建空字串輪次，R-11）。 */
export function tokenFrameWithoutTurnId(text: string): string {
  const loose: S['WsUnvalidatedEnvelope'] = { v: 1, type: 'token', payload: { text } };
  return JSON.stringify(loose);
}

/** 未知 type 的訊框（BR92.6：客戶端應安全忽略）。 */
export function unknownTypeFrame(type: string, marker: string): string {
  const loose: S['WsUnvalidatedEnvelope'] = { v: 1, type, payload: { marker } };
  return JSON.stringify(loose);
}

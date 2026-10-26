/**
 * useWorkspaceTargetSync — `/workspace` 與作業對象的雙向同步掛點（`BR97.5`、`BR97.6`；`[EP3]`=A）
 *
 * 本檔另匯出兩頁共用的核心 `useTargetSyncCore` 與純函式 `decideInitialAlignment`（評核頁的
 * `useAssessmentTargetSync` 呼叫它們，判斷只有一份，`NFR2.141`）。
 *
 * **首次對齊只在兩處執行**（performance-design §四）：連線的 `work_target` 事件回呼，與頁面在既有的
 * 非同步續延中呼叫的 `onPageReady(snapshot)`——兩者都不在 effect 內（開圖函式內有 setState，
 * `react-hooks/set-state-in-effect` 會追進去）。快照先到 → 暫存 `pendingInitialTarget`、旗標不消耗；
 * 就緒時對齊。快照後到 → 收到時對齊。
 *
 * 之後「目前選定的圖」每次改變，由 effect 送 `set_work_target`（送 WebSocket 訊息不是 setState）。
 * 回聲抑制以 `pendingEchoes`（本頁已送出、尚未收到回聲的 diagramId，上限 8、每次 ready 清空，
 * functional-design R-05）判定。
 *
 * **無連線（含無 `K1`）時所有入口為 no-op**（nfr-design R-05）：`setWorkTarget` 在未 ready 時不送、
 * 回傳 false；`work_target` 事件不會到達。
 *
 * ref 只在事件回呼、`onPageReady` 與 effect 內讀寫；render 期間只讀 state 與 props。
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { targetLabel, type WorkTargetPayload } from './brainProtocol';
import type { BrainConnection } from './brainSession';
import type { DiagramSaveStatus } from '../components/DrawioCanvas';
import { isCanvasDirty } from '../utils/unsavedWork';

export type DiagramOrigin = 'bootstrap' | 'user' | 'url' | 'brain';

export interface OwnedDiagram {
  id: number;
  is_owner?: boolean;
}

export interface AlignmentInput {
  target: WorkTargetPayload;
  urlDiagramId: number | null;
  currentDiagramId: number | null;
  openedBy: DiagramOrigin | null;
  diagrams: readonly OwnedDiagram[];
  listOk: boolean;
  unsaved: boolean;
}

export type AlignmentDecision = 'open' | 'hold' | 'writeback' | 'none';

export function isOwnedDiagram(diagrams: readonly OwnedDiagram[], id: number): boolean {
  return diagrams.some((d) => d.id === id && d.is_owner === true);
}

/**
 * 首次對齊的唯一判斷（`BR97.5` 的 (1)–(3)，含 R-02 的未儲存前置條件與 R-08 的 bootstrap 不回寫）。
 *
 * - 清單請求失敗 → `none`：擁有者未知，兩個方向都不同步。
 * - (1) 網址帶 diagramId → `writeback`：頁面優先，交 `BR97.6` 判斷是否回寫。
 * - (2) 目標圖自有且不等於目前開啟的圖 → 無未儲存內容 `open`；有 → `hold`（不開、不回寫）。
 * - (3) 否則 `writeback`；但作業對象有任何非 null 層級而 diagramId 為 null、目前的圖是 bootstrap
 *   開的 → `none`（不以使用者沒選的圖覆蓋他在入口頁選的對象，R-08）。
 */
export function decideInitialAlignment(input: AlignmentInput): AlignmentDecision {
  if (!input.listOk) return 'none';
  if (input.urlDiagramId !== null) return 'writeback';
  const { target } = input;
  const targetDiagram = target.diagramId === null ? null : Number(target.diagramId);
  if (
    targetDiagram !== null &&
    targetDiagram !== input.currentDiagramId &&
    isOwnedDiagram(input.diagrams, targetDiagram)
  ) {
    return input.unsaved ? 'hold' : 'open';
  }
  const hasLevel = target.projectId !== null || target.systemId !== null || target.diagramId !== null;
  if (hasLevel && target.diagramId === null && input.openedBy === 'bootstrap') return 'none';
  return 'writeback';
}

/** 頁面在就緒時明確傳入的值（不讀 ref：bootstrap 的 setState 尚未 commit，performance-design §四）。 */
export interface PageReadySnapshot {
  openedDiagramId?: number | null;
  openedBy?: DiagramOrigin | null;
  diagrams: readonly OwnedDiagram[];
  listOk: boolean;
  unsaved?: boolean;
}

/** 頁面目前狀態的鏡像（每次 render 由 effect 同步進 ref）。 */
export interface SyncMirror {
  currentDiagramId: number | null;
  urlDiagramId: number | null;
  diagrams: readonly OwnedDiagram[];
  unsaved: boolean;
  /** 本頁「選定的圖為 null 而內容未存檔」的情形（BR97.6 ④）：工作區＝新建空白畫布；評核頁＝未存檔上傳。 */
  unsavedCanvas: boolean;
  openDiagram: (id: number) => void;
}

export type SyncNoticeState =
  | { kind: 'changed'; label: string; diagramId: number | null; canOpen: boolean }
  | { kind: 'hold'; label: string; diagramId: number }
  | { kind: 'list-failed' };

export interface TargetSync {
  onPageReady: (snapshot: PageReadySnapshot) => void;
  markOrigin: (origin: DiagramOrigin) => void;
  onDiagramDeleted: (id: number) => void;
  /** SyncNotice 的「開啟這張圖」：有未儲存內容時先以既有形狀 window.confirm 確認。 */
  openNoticeDiagram: () => void;
  notice: SyncNoticeState | null;
  /** 由 render 推導（不另存 state）：目前的圖是別人分享的（BR97.6 ②）。 */
  sharedDiagram: boolean;
  /** 由 render 推導：目前畫布未存檔而作業對象維持（BR97.6 ④）。 */
  unsavedCanvas: boolean;
}

const MAX_PENDING_ECHOES = 8;

/** 回聲比對鍵：diagramId 為 null（刪除作業對象的圖時送出的設定）以空字串表示。 */
function echoKey(diagramId: string | null): string {
  return diagramId ?? '';
}

export function useTargetSyncCore(conn: BrainConnection, mirror: SyncMirror): TargetSync {
  const [notice, setNotice] = useState<SyncNoticeState | null>(null);
  const [listFailed, setListFailed] = useState(false);
  const [aligned, setAligned] = useState(false);

  const mirrorRef = useRef(mirror);
  const connRef = useRef(conn);
  const targetRef = useRef<WorkTargetPayload | null>(null);
  const pendingInitialRef = useRef<WorkTargetPayload | null>(null);
  const alignedRef = useRef(false);
  const pageReadyRef = useRef(false);
  const listOkRef = useRef(true);
  /** 頁面在就緒時傳入的圖清單：清單請求剛回來、setDiagrams 尚未 commit 的空窗內，以它判斷擁有者。 */
  const readyDiagramsRef = useRef<readonly OwnedDiagram[]>([]);
  const pendingEchoesRef = useRef<string[]>([]);
  const openedByRef = useRef<DiagramOrigin | null>(null);
  const lastDiagramRef = useRef<number | null>(mirror.currentDiagramId);

  useEffect(() => {
    mirrorRef.current = mirror;
    connRef.current = conn;
  });

  /** 記下本頁送出、尚未收到回聲的值（上限 8，超出丟最舊；functional-design R-05）。 */
  const rememberEcho = (diagramId: string | null) => {
    const echoes = pendingEchoesRef.current;
    echoes.push(echoKey(diagramId));
    if (echoes.length > MAX_PENDING_ECHOES) echoes.shift();
  };

  /** `BR97.6` ①：新值自有、不等於作業對象 → 送 set_work_target{null, null, diagramId}。 */
  // `diagrams` 預設取頁面鏡像；首次對齊走 onPageReady 時傳入頁面明確給的清單（setDiagrams 尚未 commit）。
  const writeBack = useCallback((diagramId: number | null, diagrams?: readonly OwnedDiagram[]) => {
    if (!alignedRef.current || !listOkRef.current || diagramId === null) return;
    const mirrorList = mirrorRef.current.diagrams;
    const list =
      diagrams ?? (mirrorList.some((d) => d.id === diagramId) ? mirrorList : readyDiagramsRef.current);
    if (!isOwnedDiagram(list, diagramId)) return; // ② 別人分享的圖：不送
    const did = String(diagramId);
    if (targetRef.current?.diagramId === did) return; // ⑤ 等於作業對象：不往返
    const sent = connRef.current.setWorkTarget({ projectId: null, systemId: null, diagramId: did });
    if (sent) rememberEcho(did); // 無連線時 no-op
  }, []);

  const align = useCallback(
    (target: WorkTargetPayload, snapshot: PageReadySnapshot | null) => {
      alignedRef.current = true;
      setAligned(true);
      pendingInitialRef.current = null;
      const m = mirrorRef.current;
      const currentDiagramId =
        snapshot && snapshot.openedDiagramId !== undefined ? snapshot.openedDiagramId : m.currentDiagramId;
      // 這張圖已由本次對齊判斷過（含 bootstrap 剛開、尚未 commit 的那張）：選定圖的 effect 不得再把它
      // 當成一次「改變」而回寫（否則快照先到時 bootstrap 的圖會在開啟作業對象的圖之前被回寫）。
      lastDiagramRef.current = currentDiagramId;
      const decision = decideInitialAlignment({
        target,
        urlDiagramId: m.urlDiagramId,
        currentDiagramId,
        openedBy: openedByRef.current,
        diagrams: snapshot ? snapshot.diagrams : m.diagrams,
        listOk: listOkRef.current,
        unsaved: snapshot && snapshot.unsaved !== undefined ? snapshot.unsaved : m.unsaved,
      });
      if (decision === 'open') {
        openedByRef.current = 'brain';
        m.openDiagram(Number(target.diagramId));
        return;
      }
      if (decision === 'hold') {
        const label = targetLabel(target);
        setNotice({ kind: 'hold', label, diagramId: Number(target.diagramId) });
        connRef.current.announce(`作業對象是「${label}」；目前畫布有未儲存的變更，沒有自動開啟`);
        return;
      }
      if (decision === 'none') {
        if (!listOkRef.current) {
          setListFailed(true);
          setNotice({ kind: 'list-failed' });
        }
        return;
      }
      writeBack(currentDiagramId, snapshot ? snapshot.diagrams : undefined);
    },
    [writeBack],
  );

  // 連線事件：只在事件回呼內被呼叫（BR92.4 已過濾為本頁目前讀取的段）。
  const { subscribe } = conn;
  useEffect(
    () =>
      subscribe({
        onReady: () => {
          pendingEchoesRef.current = []; // 斷線前送出的回聲可能永遠不到
        },
        onWorkTarget: (payload: WorkTargetPayload) => {
          targetRef.current = payload;
          if (!alignedRef.current) {
            pendingInitialRef.current = payload; // 後到者覆蓋先到者；旗標不消耗
            if (pageReadyRef.current) align(payload, null);
            return;
          }
          const did = payload.diagramId;
          const echoes = pendingEchoesRef.current;
          const echoIndex = echoes.indexOf(echoKey(did));
          if (echoIndex >= 0) {
            echoes.splice(echoIndex, 1); // 自己的回聲：不提示
            return;
          }
          const m = mirrorRef.current;
          if (did !== null && Number(did) === m.currentDiagramId) {
            setNotice(null);
            return;
          }
          if (payload.projectId === null && payload.systemId === null && did === null) {
            setNotice(null);
            return;
          }
          const label = targetLabel(payload);
          const diagramId = did === null ? null : Number(did);
          setNotice({
            kind: 'changed',
            label,
            diagramId,
            canOpen: diagramId !== null && listOkRef.current && isOwnedDiagram(m.diagrams, diagramId),
          });
          connRef.current.announce(`作業對象已改為 ${label}`);
        },
      }),
    [subscribe, align],
  );

  // 狀態驅動回寫（BR97.6）：對齊之後，選定的圖每次改變都判斷一次。送出的是 WebSocket 訊息，不是 setState。
  // 剛存成的新圖（WorkspacePage 儲存新圖、評核頁上傳後存檔）在圖清單重抓回來之前擁有者未知：等它出現在
  // 清單中再判斷，否則新圖永遠不會回寫。
  useEffect(() => {
    const current = mirror.currentDiagramId;
    if (lastDiagramRef.current === current) return;
    if (current !== null && !mirror.diagrams.some((d) => d.id === current)) return;
    lastDiagramRef.current = current;
    writeBack(current);
  }, [mirror.currentDiagramId, mirror.diagrams, writeBack]);

  const onPageReady = useCallback(
    (snapshot: PageReadySnapshot) => {
      pageReadyRef.current = true;
      listOkRef.current = snapshot.listOk;
      readyDiagramsRef.current = snapshot.diagrams;
      if (snapshot.openedBy) openedByRef.current = snapshot.openedBy;
      if (alignedRef.current) return;
      const pending = pendingInitialRef.current;
      if (pending) {
        align(pending, snapshot);
      } else if (!snapshot.listOk) {
        setListFailed(true);
        setNotice({ kind: 'list-failed' });
      }
    },
    [align],
  );

  const markOrigin = useCallback((origin: DiagramOrigin) => {
    openedByRef.current = origin;
  }, []);

  /** `BR97.6` ③：被刪的圖等於作業對象的圖 → 送保留上兩層、diagramId 為 null 的 set_work_target。 */
  const onDiagramDeleted = useCallback((id: number) => {
    const t = targetRef.current;
    if (!t || t.diagramId !== String(id)) return;
    if (connRef.current.setWorkTarget({ projectId: t.projectId, systemId: t.systemId, diagramId: null })) {
      rememberEcho(null);
    }
  }, []);

  const openNoticeDiagram = useCallback(() => {
    const current = notice;
    if (!current || current.kind === 'list-failed' || current.diagramId === null) return;
    const m = mirrorRef.current;
    if (m.unsaved && !window.confirm('有未儲存的變更，確定要開啟另一張圖？')) return;
    openedByRef.current = 'brain';
    m.openDiagram(current.diagramId);
    setNotice(null);
  }, [notice]);

  const currentIsShared =
    !listFailed &&
    mirror.currentDiagramId !== null &&
    mirror.diagrams.some((d) => d.id === mirror.currentDiagramId && d.is_owner === false);
  const target = conn.target;
  const targetHasLevel =
    target !== null && (target.projectId !== null || target.systemId !== null || target.diagramId !== null);

  return {
    onPageReady,
    markOrigin,
    onDiagramDeleted,
    openNoticeDiagram,
    notice,
    sharedDiagram: conn.status === 'ready' && currentIsShared,
    unsavedCanvas: conn.status === 'ready' && aligned && mirror.unsavedCanvas && targetHasLevel,
  };
}

interface WorkspaceSyncInput {
  currentDiagramId: number | null;
  diagrams: readonly OwnedDiagram[];
  saveStatus: DiagramSaveStatus;
  xml: string;
  openDiagram: (id: number) => void;
}

export function useWorkspaceTargetSync(conn: BrainConnection, input: WorkspaceSyncInput): TargetSync {
  return useTargetSyncCore(conn, {
    currentDiagramId: input.currentDiagramId,
    urlDiagramId: null,
    diagrams: input.diagrams,
    // 判定只有一份（security-design §六之三）：與 handleCanvasExit 同一個 isCanvasDirty。
    unsaved: isCanvasDirty(input.saveStatus, input.xml),
    unsavedCanvas: input.currentDiagramId === null,
    openDiagram: input.openDiagram,
  });
}

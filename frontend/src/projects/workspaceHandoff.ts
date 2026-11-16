/**
 * workspaceHandoff.ts — 專案總覽「在工作區建立架構圖」的交接（部署後追加，2026-11-15）
 *
 * **本階段新增、已核可 scope／requirements 尚未涵蓋**：使用者在 staging 看過專案總覽後選定
 * 「先做 1＋2，3 開新 intent」。本檔是第 1 項的一半；回補項（requirements 新 FR、user-stories 新 AC）見
 * `operation/followups/project-page-brain-entry.md`。第 3 項（讓大腦新建一張架構圖）**不在範圍**。
 *
 * **設定作業對象沿用既有機制**：只經 `BrainConnection.setWorkTarget`（`ObjectPicker` 用的同一條
 * `set_work_target`），三層 id 由 `objectPickerModel.targetIdsForSystem` 產生（`OPN-21` 的 `String()` 轉換
 * 只有一處）。不另造通道、不改 ws 契約。
 *
 * **先等伺服器確認，再導頁**：送出後等本頁讀取段的 `work_target` 回推帶回同一個系統 id 才導到
 * `/workspace`。理由：伺服器以擁有者範圍解析對象（`resolve_work_target`），不合格時不會回推該系統；
 * 若送出即導頁，會在「其實沒設成」時把使用者帶到工作區，存檔後圖不會掛到系統，而畫面看起來一切正常。
 * 逾時（`HANDOFF_TIMEOUT_MS`）不導頁並顯示原因。
 *
 * 一頁只有一個事件掛點（`brainSession.subscribe` 的契約），故本 hook 只在 `SystemDiagrams` 呼叫一次，
 * 各系統列共用同一份待決狀態。
 *
 * 本檔不碰瀏覽器儲存、沒有主控台輸出。
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { BrainConnection } from '../brain/brainSession';
import { targetIdsForSystem } from '../brain/objectPickerModel';
import type { SystemOut } from './projectsApi';

/** 交給 `/workspace` 的導覽 state：工作區見到它就開空白畫布，不還原上次開的圖。 */
const NEW_DIAGRAM_STATE = { cloud360StartNewDiagram: true } as const;

export const HANDOFF_TIMEOUT_MS = 8000;

/** 非擁有者的說明（`[OP3]`=A）：唯一來源在 `objectPickerModel.ts`，選單與專案頁共用。 */
export { NOT_OWNED_TARGET_NOTE } from '../brain/objectPickerModel';

/** `/workspace` 讀取導覽 state 的唯一判定。 */
export function isNewDiagramHandoff(state: unknown): boolean {
  return (
    typeof state === 'object' &&
    state !== null &&
    (state as { cloud360StartNewDiagram?: unknown }).cloud360StartNewDiagram === true
  );
}

export interface WorkspaceHandoff {
  /** 正在等伺服器確認的系統 id；null＝沒有待決的交接。 */
  pendingSystemId: number | null;
  error: string | null;
  start: (system: SystemOut) => void;
}

export function useWorkspaceHandoff(brain: BrainConnection | null): WorkspaceHandoff {
  const navigate = useNavigate();
  const pendingRef = useRef<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [pendingSystemId, setPendingSystemId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const goToWorkspace = useCallback(() => {
    navigate('/workspace', { state: NEW_DIAGRAM_STATE });
  }, [navigate]);

  const subscribe = brain?.subscribe;
  useEffect(() => {
    if (!subscribe) return undefined;
    return subscribe({
      onWorkTarget: (payload) => {
        const wanted = pendingRef.current;
        if (wanted === null || payload.systemId !== wanted) return;
        pendingRef.current = null;
        if (timerRef.current !== null) clearTimeout(timerRef.current);
        timerRef.current = null;
        goToWorkspace();
      },
    });
  }, [subscribe, goToWorkspace]);

  useEffect(
    () => () => {
      if (timerRef.current !== null) clearTimeout(timerRef.current);
      timerRef.current = null;
      pendingRef.current = null;
    },
    [],
  );

  const start = (system: SystemOut) => {
    if (!brain || pendingRef.current !== null) return;
    setError(null);
    const ids = targetIdsForSystem(system);
    if (brain.target?.systemId === ids.systemId) {
      // 已經是這個系統：不必往返，直接前往。
      goToWorkspace();
      return;
    }
    if (!brain.setWorkTarget(ids)) {
      setError('目前無法設定作業對象：與大腦的連線中斷');
      return;
    }
    pendingRef.current = ids.systemId;
    setPendingSystemId(system.id);
    timerRef.current = setTimeout(() => {
      timerRef.current = null;
      if (pendingRef.current !== ids.systemId) return;
      pendingRef.current = null;
      setPendingSystemId(null);
      setError('大腦沒有確認作業對象，沒有前往工作區。請確認脈絡列後再試一次。');
    }, HANDOFF_TIMEOUT_MS);
  };

  return { pendingSystemId, error, start };
}

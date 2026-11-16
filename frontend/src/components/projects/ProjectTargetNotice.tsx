import React, { useId, useState } from 'react';
import { useAuth } from '../../context/auth-context';
import { useBrainSession } from '../../brain/brainSession';
import { isOwnedByMe, targetIdsForProject } from '../../brain/objectPickerModel';
import { targetLabel } from '../../brain/brainProtocol';
import type { ProjectOut } from '../../projects/projectsApi';
import { NOT_OWNED_TARGET_NOTE } from '../../projects/workspaceHandoff';

/**
 * ProjectTargetNotice — 專案頁的作業對象提示（部署後追加，2026-11-15）
 *
 * **本階段新增、已核可 scope／requirements 尚未涵蓋**：使用者選定「專案頁也能跟大腦對話」（第 2 項）。
 * 回補項見 `operation/followups/project-page-brain-entry.md`。
 *
 * **進頁不改作業對象**：作業對象是跨頁共用的（入口、工作區、評估頁的共享段讀同一個），進專案頁就悄悄
 * 改掉，別頁的對話對象會跟著被換掉而使用者不知道。所以只在「目前作業對象不在這個專案內」時提示，
 * 並提供一鍵改設；改不改由使用者決定。
 *
 * 形狀沿用 `SyncNotice`（同一條琥珀色提示列）；改設只經既有的 `setWorkTarget`（`set_work_target`），
 * 三層 id 由 `objectPickerModel.targetIdsForProject` 產生；送出失敗的說法與 `ObjectPicker` 相同。
 * 不是專案擁有者時照列、停用並以 `ObjectPicker` 的同一句說明（`[OP3]`=A）。
 *
 * 作業對象尚未收到（`target === null`）或連線未就緒時不渲染：此時無從判斷「在不在這個專案內」。
 */
export const ProjectTargetNotice: React.FC<{ project: ProjectOut }> = ({ project }) => {
  const { user } = useAuth();
  const { status, target, setWorkTarget } = useBrainSession();
  const noteId = useId();
  const [error, setError] = useState<string | null>(null);

  if (status !== 'ready' || target === null) return null;
  if (target.projectId === String(project.id)) return null;

  const owned = user?.id !== undefined && isOwnedByMe(project, user.id);
  const handleClick = () => {
    if (!owned) return;
    setError(null);
    if (!setWorkTarget(targetIdsForProject(project))) setError('目前無法切換：與大腦的連線中斷');
  };

  return (
    <div
      data-testid="project-target-notice"
      className="flex flex-wrap items-center gap-3 bg-amber-50 border-b border-amber-100 px-4 py-2 text-sm text-amber-800"
    >
      <span className="break-all">目前作業對象「{targetLabel(target)}」不在這個專案內，大腦會以它為準回答</span>
      <button
        type="button"
        data-testid="project-target-set"
        aria-disabled={owned ? undefined : true}
        aria-describedby={owned ? undefined : noteId}
        onClick={handleClick}
        className={owned ? 'font-semibold text-brand-700 hover:underline' : 'cursor-not-allowed font-semibold text-gray-400'}
      >
        把作業對象設為這個專案
      </button>
      {!owned && (
        <span id={noteId} data-testid="project-target-not-owned" className="text-xs text-gray-600">
          {NOT_OWNED_TARGET_NOTE}
        </span>
      )}
      {error && (
        <span role="status" className="font-bold text-red-800">
          {error}
        </span>
      )}
    </div>
  );
};

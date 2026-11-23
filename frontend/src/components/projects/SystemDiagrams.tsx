import React, { useId, useState } from 'react';
import { useAuth } from '../../context/auth-context';
import type { BrainConnection } from '../../brain/brainSession';
import { isOwnedByMe } from '../../brain/objectPickerModel';
import { DraftBadge } from '../DraftBadge';
import {
  ApiError,
  isDraft,
  setDiagramSystem,
  type MyDiagram,
  type ProjectOut,
  type SystemOut,
} from '../../projects/projectsApi';
import {
  NOT_OWNED_TARGET_NOTE,
  useWorkspaceHandoff,
  type WorkspaceHandoff,
} from '../../projects/workspaceHandoff';

/**
 * SystemDiagrams — 總覽籤的「系統的架構圖」區（build-and-test 本機驗證 F1，2026-11-12）
 *
 * **本階段新增、已核可 scope／requirements 尚未涵蓋**：FR9.1 只說系統對應架構圖檔、FR9.5 只要求
 * 專案／系統的建立路徑。回補：requirements 新增「架構圖掛到系統」FR、user-stories 補 AC。
 *
 * 每個系統列出**我自己的**、已掛在該系統的圖，並可把我的其他圖掛上來（含從別的系統改掛）或
 * 取消掛載。伺服器是唯一的判定點（`K2 edit` ＋ 圖的擁有者 ＋ 目標系統所屬專案的擁有者）；
 * 本元件只在缺 `K2 edit` 時不渲染控制項，其餘拒絕（404）照實顯示伺服器的訊息。
 *
 * 資料抓取沿用 `react-hooks/set-state-in-effect` 的兩層形狀：純抓取在 `projectsApi`，state 只在
 * `.then`／`.catch` 內更新，`useEffect` 以 `cancelled` 防卸載後 setState（抓取自 2026-11-15 起在
 * `OverviewTab`）。
 *
 * **部署後追加（2026-11-15；本階段新增、已核可 scope／requirements 尚未涵蓋）**：
 * - 「我的圖」清單改由 `OverviewTab` 持有並傳入（同一份資料同時算頂端的架構圖計數，單一真實來源）；
 * - 每個系統列加「在工作區建立架構圖」：先經既有 `set_work_target` 把作業對象設為該系統、等伺服器確認後
 *   導到 `/workspace`（見 `projects/workspaceHandoff.ts`）。只在有大腦連線（`K1 view`）且具 `A1 edit` 時渲染；
 *   不是專案擁有者時照列但停用並說明（`[OP3]`=A，說法與 `ObjectPicker` 相同）。系統列在圖清單載入中或
 *   失敗時也照列，讓這個動作不依賴圖清單。
 */
export type MyDiagramsLoad = { status: 'loading' } | { status: 'failed' } | { status: 'ready'; diagrams: MyDiagram[] };

const CreateInWorkspace: React.FC<{
  system: SystemOut;
  owned: boolean;
  brain: BrainConnection;
  handoff: WorkspaceHandoff;
}> = ({ system, owned, brain, handoff }) => {
  const noteId = useId();
  const ready = brain.status === 'ready';
  const pendingHere = handoff.pendingSystemId === system.id;
  const busy = handoff.pendingSystemId !== null;
  const enabled = owned && ready && !busy;
  let note: string | null = null;
  if (!owned) note = NOT_OWNED_TARGET_NOTE;
  else if (!ready) note = '大腦連線就緒後才能設定作業對象';
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2">
      <button
        type="button"
        data-testid={`system-create-in-workspace-${system.id}`}
        aria-disabled={enabled ? undefined : true}
        aria-describedby={note ? noteId : undefined}
        onClick={() => {
          if (enabled) handoff.start(system);
        }}
        className={`min-h-11 rounded border px-3 text-sm font-bold ${
          enabled ? 'border-brand-200 text-brand-700 hover:bg-brand-50' : 'cursor-not-allowed border-gray-200 text-gray-400'
        }`}
      >
        {pendingHere ? '正在設定作業對象…' : '在工作區建立架構圖'}
      </button>
      {note && (
        <span id={noteId} data-testid={`system-create-in-workspace-note-${system.id}`} className="text-xs text-gray-600">
          {note}
        </span>
      )}
    </div>
  );
};

const SystemRow: React.FC<{
  system: SystemOut;
  systems: SystemOut[];
  /** null＝圖清單尚未載入或失敗：只渲染系統名與建立動作。 */
  diagrams: MyDiagram[] | null;
  canEdit: boolean;
  busy: boolean;
  onChange: (diagramId: number, systemId: number | null) => void;
  createAction: React.ReactNode;
}> = ({ system, systems, diagrams, canEdit, busy, onChange, createAction }) => {
  const selectId = useId();
  const attached = (diagrams ?? []).filter((d) => d.system_id === system.id);
  const candidates = (diagrams ?? []).filter((d) => d.system_id !== system.id);
  const [choice, setChoice] = useState('');
  const systemName = (id: number | null) => systems.find((s) => s.id === id)?.name;

  return (
    <li className="rounded border border-gray-200 p-3" data-testid={`system-diagrams-${system.id}`}>
      <h3 className="text-sm font-bold text-gray-900">{system.name}</h3>
      {diagrams === null ? null : attached.length === 0 ? (
        <p className="mt-1 text-sm text-gray-600">這個系統還沒有掛上你的架構圖</p>
      ) : (
        <ul className="mt-1 space-y-1 text-sm text-gray-800">
          {attached.map((d) => (
            <li key={d.id} className="flex items-center gap-2" data-testid="system-diagram-item">
              <span>{d.title}</span>
              {isDraft(d) && <DraftBadge testId={`system-diagram-draft-${d.id}`} />}
              {canEdit && (
                <button
                  type="button"
                  className="min-h-11 rounded px-2 text-xs text-gray-700 underline disabled:opacity-50"
                  disabled={busy}
                  onClick={() => onChange(d.id, null)}
                >
                  取消掛載「{d.title}」
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {canEdit && candidates.length > 0 && (
        <form
          className="mt-2 flex flex-wrap items-center gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (!choice) return;
            onChange(Number(choice), system.id);
            setChoice('');
          }}
        >
          <label htmlFor={selectId} className="text-sm text-gray-700">
            把架構圖掛到「{system.name}」
          </label>
          <select
            id={selectId}
            className="min-h-11 rounded border border-gray-300 px-2 text-sm"
            value={choice}
            onChange={(event) => setChoice(event.target.value)}
          >
            <option value="">選擇我的架構圖</option>
            {candidates.map((d) => (
              <option
                key={d.id}
                value={String(d.id)}
                data-testid={`attach-candidate-${d.id}`}
                data-draft={isDraft(d) ? 'true' : 'false'}
              >
                {/* 修訂 1（FR6.4）：這份清單也要能辨識草稿，避免不知情地把草稿搬到別的系統。 */}
                {`${d.title}${isDraft(d) ? '（草稿）' : ''}${
                  d.system_id === null
                    ? ''
                    : `（目前在「${systemName(d.system_id) ?? '其他專案的系統'}」）`
                }`}
              </option>
            ))}
          </select>
          <button
            type="submit"
            className="min-h-11 rounded bg-blue-700 px-3 text-sm font-bold text-white disabled:opacity-50"
            disabled={busy || !choice}
          >
            掛上
          </button>
        </form>
      )}
      {createAction}
    </li>
  );
};

export const SystemDiagrams: React.FC<{
  project: ProjectOut;
  systems: SystemOut[];
  state: MyDiagramsLoad;
  onReload: () => void;
  /** 本頁的大腦連線；無 `K1 view`（未開連線）時為 null。 */
  brain: BrainConnection | null;
}> = ({ project, systems, state, onReload, brain }) => {
  const { token, user, can, canArch } = useAuth();
  const canSee = canArch('view');
  const canEdit = can('K2', 'edit');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null);
  const handoff = useWorkspaceHandoff(brain);
  // 擁有者判定只有一處（`objectPickerModel.isOwnedByMe`，`OPN-12`）；這不是授權，伺服器仍以擁有者範圍解析。
  const owned = user?.id !== undefined && isOwnedByMe(project, user.id);
  // 沒有大腦連線時不顯示：存檔掛到系統靠的是作業對象，沒有連線就沒有作業對象，顯示了也掛不上。
  const showCreate = brain !== null && canArch('edit');

  if (!canSee || systems.length === 0) return null;

  const handleChange = (diagramId: number, systemId: number | null) => {
    if (!token || busy) return;
    setBusy(true);
    setMessage(null);
    setDiagramSystem(token, diagramId, systemId)
      .then(() => {
        setMessage({ kind: 'ok', text: systemId === null ? '已取消掛載' : '已掛到系統' });
        onReload();
      })
      .catch((err: unknown) => {
        setMessage({
          kind: 'error',
          text: err instanceof ApiError ? err.message : '變更架構圖歸屬失敗，請稍後再試',
        });
      })
      .finally(() => setBusy(false));
  };

  return (
    <section data-testid="project-system-diagrams" aria-labelledby="project-system-diagrams-title">
      <h2 id="project-system-diagrams-title" className="text-sm font-bold text-gray-900">
        系統的架構圖
      </h2>
      <p className="mt-1 text-xs text-gray-500">只列出你自己的架構圖；大腦依這裡的歸屬找系統下的圖。</p>
      <p role="status" className="mt-1 text-sm" data-testid="system-diagrams-status">
        {message && (
          <span className={message.kind === 'ok' ? 'text-green-800' : 'font-bold text-red-800'}>
            {message.text}
          </span>
        )}
        {handoff.error && (
          <span className="font-bold text-red-800" data-testid="system-create-in-workspace-error">
            {handoff.error}
          </span>
        )}
      </p>
      {state.status === 'loading' && <p className="mt-2 text-sm text-gray-500">正在載入架構圖…</p>}
      {state.status === 'failed' && <p className="mt-2 text-sm font-bold text-amber-800">無法取得架構圖</p>}
      <ul className="mt-2 space-y-2">
        {[...systems]
          .sort((a, b) => a.id - b.id)
          .map((system) => (
            <SystemRow
              key={system.id}
              system={system}
              systems={systems}
              diagrams={state.status === 'ready' ? state.diagrams : null}
              canEdit={canEdit}
              busy={busy}
              onChange={handleChange}
              createAction={
                showCreate && brain ? (
                  <CreateInWorkspace system={system} owned={owned} brain={brain} handoff={handoff} />
                ) : null
              }
            />
          ))}
      </ul>
    </section>
  );
};

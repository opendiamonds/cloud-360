import React, { useEffect, useId, useState } from 'react';
import { useAuth } from '../../context/auth-context';
import {
  ApiError,
  listMyDiagrams,
  setDiagramSystem,
  type MyDiagram,
  type SystemOut,
} from '../../projects/projectsApi';

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
 * `.then`／`.catch` 內更新，`useEffect` 以 `cancelled` 防卸載後 setState。
 */
type LoadState = { status: 'loading' } | { status: 'failed' } | { status: 'ready'; diagrams: MyDiagram[] };

const SystemRow: React.FC<{
  system: SystemOut;
  systems: SystemOut[];
  diagrams: MyDiagram[];
  canEdit: boolean;
  busy: boolean;
  onChange: (diagramId: number, systemId: number | null) => void;
}> = ({ system, systems, diagrams, canEdit, busy, onChange }) => {
  const selectId = useId();
  const attached = diagrams.filter((d) => d.system_id === system.id);
  const candidates = diagrams.filter((d) => d.system_id !== system.id);
  const [choice, setChoice] = useState('');
  const systemName = (id: number | null) => systems.find((s) => s.id === id)?.name;

  return (
    <li className="rounded border border-gray-200 p-3" data-testid={`system-diagrams-${system.id}`}>
      <h3 className="text-sm font-bold text-gray-900">{system.name}</h3>
      {attached.length === 0 ? (
        <p className="mt-1 text-sm text-gray-600">這個系統還沒有掛上你的架構圖</p>
      ) : (
        <ul className="mt-1 space-y-1 text-sm text-gray-800">
          {attached.map((d) => (
            <li key={d.id} className="flex items-center gap-2" data-testid="system-diagram-item">
              <span>{d.title}</span>
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
              <option key={d.id} value={String(d.id)}>
                {d.system_id === null
                  ? d.title
                  : `${d.title}（目前在「${systemName(d.system_id) ?? '其他專案的系統'}」）`}
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
    </li>
  );
};

export const SystemDiagrams: React.FC<{ systems: SystemOut[] }> = ({ systems }) => {
  const { token, can, canArch } = useAuth();
  const canSee = canArch('view');
  const canEdit = can('K2', 'edit');
  const [state, setState] = useState<LoadState>({ status: 'loading' });
  const [reloadKey, setReloadKey] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (!token || !canSee) return;
    let cancelled = false;
    listMyDiagrams(token)
      .then((diagrams) => {
        if (!cancelled) setState({ status: 'ready', diagrams });
      })
      .catch(() => {
        if (!cancelled) setState({ status: 'failed' });
      });
    return () => {
      cancelled = true;
    };
  }, [token, canSee, reloadKey]);

  if (!canSee || systems.length === 0) return null;

  const handleChange = (diagramId: number, systemId: number | null) => {
    if (!token || busy) return;
    setBusy(true);
    setMessage(null);
    setDiagramSystem(token, diagramId, systemId)
      .then(() => {
        setMessage({ kind: 'ok', text: systemId === null ? '已取消掛載' : '已掛到系統' });
        setReloadKey((k) => k + 1);
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
      </p>
      {state.status === 'loading' && <p className="mt-2 text-sm text-gray-500">正在載入架構圖…</p>}
      {state.status === 'failed' && <p className="mt-2 text-sm font-bold text-amber-800">無法取得架構圖</p>}
      {state.status === 'ready' && (
        <ul className="mt-2 space-y-2">
          {[...systems]
            .sort((a, b) => a.id - b.id)
            .map((system) => (
              <SystemRow
                key={system.id}
                system={system}
                systems={systems}
                diagrams={state.diagrams}
                canEdit={canEdit}
                busy={busy}
                onChange={handleChange}
              />
            ))}
        </ul>
      )}
    </section>
  );
};

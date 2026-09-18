import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useAuth } from '../context/auth-context';
import { apiUrl } from '../config/api';

interface RolePermRow {
  role: string;
  story_id: string;
  can_view: boolean;
  can_edit: boolean;
  can_review: boolean;
}

const PILLARS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J'] as const;

/** Pillar → 功能中文名 */
const PILLAR_LABELS: Record<(typeof PILLARS)[number], string> = {
  A: '架構設計',
  B: '跨雲選型',
  C: '成本與 FinOps',
  D: '基礎建設即程式碼',
  E: '維運優化',
  F: 'AI 多雲維運',
  G: '安全與合規',
  H: 'MCP 與 Skill',
  J: '身分與權限',
};

/** Story → 功能短名（欄位標題） */
const STORY_LABELS: Record<string, string> = {
  __ARCH__: '架構圖生成',
  A1: '自然語言轉架構',
  A2: 'AI 協同編輯',
  A3: 'Well-Architected 評核',
  A4: '聊天／圖持久化',
  B1: '單一雲端評選',
  B2: '生態相容掃描',
  B3: '地緣合規與延遲',
  C1: 'TCO 與流量預算',
  C2: '資源優化定價',
  C3: 'Egress 隱性成本',
  D1: 'Terraform 產出',
  D2: 'IaC 安全掃描',
  D3: 'Secret／敏感值',
  E1: 'Right-sizing',
  E2: '架構現代化',
  E3: 'Runbooks 生成',
  F1: '跨雲健康查詢',
  F2: '變更與回滾',
  F3: '高風險審批閘門',
  G1: 'CSPM 持續合規',
  G2: 'IAM 最小權限',
  G3: 'Policy-as-Code',
  H1: '內部 API 註冊',
  H2: 'Agent 存取邊界',
  H3: 'MCP／Skill 生命週期',
  /** Pillar J 細項 UI 僅這兩項（不含 J1 登入） */
  J3a: '使用者設定',
  J3b: '細項設定',
};

/** Pillar J 在矩陣 UI 只顯示的 story */
const J_MATRIX_STORIES = new Set(['J3a', 'J3b']);


/** A1／A2／A4 合併為同一欄（架構圖生成） */
const ARCH_BUNDLE = ['A1', 'A2', 'A4'] as const;
const ARCH_COLUMN = '__ARCH__';

const ACTION_LABELS = [
  ['can_view', '檢視'],
  ['can_edit', '編輯'],
  ['can_review', '審核'],
] as const;

type CellKey = string; // `${role}::${story}`

function cellKey(role: string, story: string) {
  return `${role}::${story}`;
}

export const RolePermissionsPage: React.FC = () => {
  const { token, can, refreshMe } = useAuth();
  const canEdit = can('J3b', 'edit');
  const canReset = can('J3b', 'review');

  const [rows, setRows] = useState<RolePermRow[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [stories, setStories] = useState<string[]>([]);
  const [pillar, setPillar] = useState<string>('A');
  const [dirty, setDirty] = useState<Record<CellKey, RolePermRow>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(
    null
  );

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // 純抓取，完全不碰 state。react-hooks/set-state-in-effect 會做過程間分析：
  // 只要 effect 同步呼叫的函式內部有 setState 就會被擋，因此把 state 更新一律
  // 留在呼叫端的 .then／.catch／.finally callback 內（規則允許的形式）。
  const fetchMatrix = useCallback(async () => {
    const [metaRes, matrixRes] = await Promise.all([
      fetch(apiUrl('/api/auth/roles'), {
        headers: { Authorization: `Bearer ${token}` },
      }),
      fetch(apiUrl('/api/auth/role-permissions'), {
        headers: { Authorization: `Bearer ${token}` },
      }),
    ]);
    if (!metaRes.ok) throw new Error('無法取得角色清單');
    if (!matrixRes.ok) {
      const d = await matrixRes.json();
      throw new Error(d.detail || '無法取得權限矩陣');
    }
    const meta = await metaRes.json();
    const matrix: RolePermRow[] = await matrixRes.json();
    return { meta, matrix };
  }, [token]);

  // 套用抓回來的資料。兩處呼叫端共用，避免邏輯重複。
  const applyMatrix = useCallback(
    ({ meta, matrix }: { meta: { roles?: string[]; stories?: string[] }; matrix: RolePermRow[] }) => {
      setRoles(meta.roles || []);
      // Pillar J：矩陣只編 J3a／J3b（使用者設定／細項設定），不含 J1 登入
      setStories(
        (meta.stories || []).filter(
          (s: string) => !s.startsWith('J') || J_MATRIX_STORIES.has(s)
        )
      );
      setRows(matrix);
      setDirty({});
    },
    []
  );

  // 使用者主動觸發（存檔／還原後重載）：先切回 loading 再抓。
  const load = useCallback(() => {
    if (!token) return Promise.resolve();
    setIsLoading(true);
    setError(null);
    return fetchMatrix()
      .then(applyMatrix)
      .catch((err) => setError(err instanceof Error ? err.message : '載入失敗'))
      .finally(() => setIsLoading(false));
  }, [token, fetchMatrix, applyMatrix]);

  useEffect(() => {
    if (!token) return;
    // 初次載入時 isLoading 已是 true，不需要再設一次。
    let cancelled = false;
    fetchMatrix()
      .then((data) => { if (!cancelled) applyMatrix(data); })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : '載入失敗'); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [token, fetchMatrix, applyMatrix]);

  const visibleStories = useMemo(() => {
    const raw = stories.filter((s) => s.startsWith(pillar));
    if (pillar !== 'A') return raw;
    const out: string[] = [];
    let archAdded = false;
    for (const s of raw) {
      if ((ARCH_BUNDLE as readonly string[]).includes(s)) {
        if (!archAdded) {
          out.push(ARCH_COLUMN);
          archAdded = true;
        }
      } else {
        out.push(s);
      }
    }
    return out;
  }, [stories, pillar]);

  const lookup = (role: string, story: string): RolePermRow => {
    const realStory = story === ARCH_COLUMN ? 'A1' : story;
    const key = cellKey(role, realStory);
    if (dirty[key]) return { ...dirty[key], story_id: story };
    const found = rows.find((r) => r.role === role && r.story_id === realStory);
    return (
      found
        ? { ...found, story_id: story }
        : {
            role,
            story_id: story,
            can_view: false,
            can_edit: false,
            can_review: false,
          }
    );
  };

  const toggle = (
    role: string,
    story: string,
    field: 'can_view' | 'can_edit' | 'can_review'
  ) => {
    if (!canEdit) return;
    const cur = lookup(role, story);
    let next = { ...cur, [field]: !cur[field] };
    // 編輯／審核開啟時自動帶檢視；關閉檢視則三者皆關
    if (field === 'can_edit' && next.can_edit) next.can_view = true;
    if (field === 'can_review' && next.can_review) next.can_view = true;
    if (field === 'can_view' && !next.can_view) {
      next = { ...next, can_edit: false, can_review: false };
    }
    // 審核語意：可與編輯並存；僅審核時不強制關編輯（由管理員勾選）

    if (story === ARCH_COLUMN) {
      setDirty((prev) => {
        const copy = { ...prev };
        for (const sid of ARCH_BUNDLE) {
          copy[cellKey(role, sid)] = {
            role,
            story_id: sid,
            can_view: next.can_view,
            can_edit: next.can_edit,
            can_review: next.can_review,
          };
        }
        return copy;
      });
      return;
    }

    setDirty((prev) => ({
      ...prev,
      [cellKey(role, story)]: { ...next, story_id: story },
    }));
  };

  const handleSave = async () => {
    const payload = Object.values(dirty);
    if (!payload.length) {
      showToast('沒有變更需要儲存', 'error');
      return;
    }
    setIsSaving(true);
    try {
      const res = await fetch(apiUrl('/api/auth/role-permissions'), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ rows: payload }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '儲存失敗');
      showToast(`✔ 已更新 ${payload.length} 格權限`, 'success');
      await load();
      await refreshMe();
    } catch (err) {
      showToast(err instanceof Error ? err.message : '儲存失敗', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async () => {
    if (!canReset) return;
    if (!window.confirm('確定還原為設計預設矩陣？此操作會覆寫目前所有自訂權限。')) {
      return;
    }
    try {
      const res = await fetch(apiUrl('/api/auth/role-permissions/reset-defaults'), {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '還原失敗');
      showToast(`✔ ${data.message}`, 'success');
      await load();
      await refreshMe();
    } catch (err) {
      showToast(err instanceof Error ? err.message : '還原失敗', 'error');
    }
  };

  const dirtyCount = Object.keys(dirty).length;

  return (
    <div className="relative min-h-full bg-slate-950 p-6 md:p-10 pb-16 text-white font-sans w-full">
      {toast && (
        <div
          className={`fixed top-6 left-1/2 -translate-x-1/2 z-50 px-6 py-4 rounded-2xl shadow-xl backdrop-blur-xl border flex items-center gap-3 ${
            toast.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
              : 'bg-red-500/10 border-red-500/20 text-red-300'
          }`}
        >
          <span className="font-semibold text-sm tracking-wide">{toast.message}</span>
        </div>
      )}

      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-black tracking-tight text-white">角色細項權限</h1>
          <p className="text-slate-400 text-sm font-medium">
            設定各角色對 User Story 的檢視／編輯／審核（J3b）。變更儲存後即時生效。矩陣可用滾輪上下／左右捲動。
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {canReset && (
            <button
              type="button"
              onClick={handleReset}
              className="px-4 py-2 text-xs font-bold rounded-xl border border-amber-500/40 text-amber-300 hover:bg-amber-500/10"
            >
              還原設計預設
            </button>
          )}
          {canEdit && (
            <button
              type="button"
              disabled={isSaving || dirtyCount === 0}
              onClick={handleSave}
              className="px-5 py-2 text-xs font-bold rounded-xl bg-blue-600 text-white disabled:opacity-40 hover:bg-blue-500"
            >
              {isSaving ? '儲存中…' : `儲存變更${dirtyCount ? ` (${dirtyCount})` : ''}`}
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        {PILLARS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setPillar(p)}
            className={`px-4 py-2 text-xs font-extrabold rounded-xl border transition-colors ${
              pillar === p
                ? 'bg-blue-500/20 border-blue-400 text-blue-200'
                : 'bg-white/5 border-white/10 text-slate-400 hover:bg-white/10'
            }`}
            title={`${p} — ${PILLAR_LABELS[p]}`}
          >
            {PILLAR_LABELS[p]}
          </button>
        ))}
      </div>

      <div className="bg-white/5 backdrop-blur-2xl border border-white/10 rounded-[2rem] shadow-2xl overflow-hidden">
        {isLoading ? (
          <div className="p-20 text-center text-slate-400">載入權限矩陣…</div>
        ) : error ? (
          <div className="p-20 text-center text-red-300 font-bold">{error}</div>
        ) : (
          <div className="overflow-auto max-h-[min(70vh,720px)] overscroll-contain">
            <table className="w-full text-left border-collapse min-w-[900px]">
              <thead className="sticky top-0 z-20">
                <tr className="bg-slate-950 border-b border-white/10 text-[10px] font-bold text-slate-400 tracking-wider">
                  <th className="px-4 py-4 sticky left-0 top-0 bg-slate-950 z-30">角色</th>
                  {visibleStories.map((s) => (
                    <th key={s} className="px-3 py-4 text-center min-w-[7rem] bg-slate-950">
                      <div className="text-slate-300 font-extrabold">
                        {s === ARCH_COLUMN ? 'A1／A2／A4' : s}
                      </div>
                      <div className="mt-1 font-medium text-slate-500 normal-case leading-snug">
                        {STORY_LABELS[s] || s}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {roles.map((role) => (
                  <tr key={role} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 text-xs font-bold text-slate-200 sticky left-0 bg-slate-950/90 z-10 whitespace-nowrap">
                      {role}
                    </td>
                    {visibleStories.map((story) => {
                      const cell = lookup(role, story);
                      const isDirty =
                        story === ARCH_COLUMN
                          ? ARCH_BUNDLE.some((sid) => !!dirty[cellKey(role, sid)])
                          : !!dirty[cellKey(role, story)];
                      return (
                        <td
                          key={story}
                          className={`px-2 py-2 text-center ${isDirty ? 'bg-blue-500/10' : ''}`}
                        >
                          <div className="inline-flex flex-col gap-1 items-start text-[10px] font-bold text-slate-400">
                            {ACTION_LABELS.map(([field, label]) => {
                              const checked = cell[field];
                              return (
                              <label
                                key={field}
                                className={`inline-flex items-center gap-1.5 cursor-pointer ${
                                  !canEdit ? 'opacity-60 cursor-default' : ''
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  disabled={!canEdit}
                                  onChange={() => toggle(role, story, field)}
                                  className="rounded border-slate-600"
                                />
                                {label}
                              </label>
                              );
                            })}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {!canEdit && (
        <p className="mt-4 text-xs text-slate-500">目前為唯讀（需要 J3b.edit 才能修改）。</p>
      )}
    </div>
  );
};

import { useCallback, useEffect, useState } from 'react';
import { apiUrl } from '../config/api';

type ImprovementPlan = { displayText?: string };
type Choice = {
  id: string;
  title: string;
  improvementPlan?: ImprovementPlan;
};
type Question = {
  id: string;
  title: string;
  description?: string;
  choices: Choice[];
  riskRules?: unknown[];
};
type Pillar = {
  id: string;
  name: string;
  questions: Question[];
};
type Lens = {
  schemaVersion: string;
  name?: string;
  description?: string;
  pillars: Pillar[];
};

const PILLAR_ORDER = [
  'security',
  'reliability',
  'cost_optimization',
  'performance_efficiency',
  'operational_excellence',
];

type Props = {
  token: string;
};

export function LensCriteriaEditor({ token }: Props) {
  const [provider, setProvider] = useState('aws');
  const [lens, setLens] = useState<Lens | null>(null);
  const [source, setSource] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [okMsg, setOkMsg] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string>('security');

  const headers = useCallback(
    () => ({
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    }),
    [token]
  );

  // 純抓取，完全不碰 state。react-hooks/set-state-in-effect 會做過程間分析：
  // 只要 effect 同步呼叫的函式內部有 setState 就會被擋，因此 state 更新一律留在
  // 呼叫端的 callback 內（規則允許的形式）。
  const fetchLens = useCallback(async (prov: string) => {
    const res = await fetch(
      apiUrl(`/api/architecture/lens/active?provider=${encodeURIComponent(prov)}`),
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }, [token]);

  // 使用者主動觸發的重載（存檔後）：先切回 loading 再抓。
  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    setOkMsg(null);
    return fetchLens(provider)
      .then((data) => {
        setLens(data.lens as Lens);
        setSource(data.source || '');
      })
      .catch((e) => setError(e instanceof Error ? e.message : '載入 Lens 失敗'))
      .finally(() => setLoading(false));
  }, [fetchLens, provider]);

  useEffect(() => {
    let cancelled = false;
    fetchLens(provider)
      .then((data) => {
        if (cancelled) return;
        setLens(data.lens as Lens);
        setSource(data.source || '');
      })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : '載入 Lens 失敗'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fetchLens, provider]);

  const changeProvider = (next: string) => {
    if (next === provider) return;
    setProvider(next);
    setLoading(true);
    setError(null);
    setOkMsg(null);
    setLens(null);
  };

  const updateQuestion = (
    pillarId: string,
    qIndex: number,
    patch: Partial<Question>
  ) => {
    setLens((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        pillars: prev.pillars.map((p) => {
          if (p.id !== pillarId) return p;
          const questions = p.questions.map((q, i) =>
            i === qIndex ? { ...q, ...patch } : q
          );
          return { ...p, questions };
        }),
      };
    });
    setOkMsg(null);
  };

  const updateChoice = (
    pillarId: string,
    qIndex: number,
    cIndex: number,
    patch: Partial<Choice>
  ) => {
    setLens((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        pillars: prev.pillars.map((p) => {
          if (p.id !== pillarId) return p;
          const questions = p.questions.map((q, qi) => {
            if (qi !== qIndex) return q;
            const choices = q.choices.map((c, ci) =>
              ci === cIndex ? { ...c, ...patch } : c
            );
            return { ...q, choices };
          });
          return { ...p, questions };
        }),
      };
    });
    setOkMsg(null);
  };

  const addQuestion = async (pillarId: string) => {
    setError(null);
    try {
      const res = await fetch(
        apiUrl(
          `/api/architecture/lens/new-question-template?pillar_id=${encodeURIComponent(
            pillarId
          )}&title=${encodeURIComponent('New review question')}`
        ),
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const question = data.question as Question;
      setLens((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          pillars: prev.pillars.map((p) =>
            p.id === pillarId
              ? { ...p, questions: [...p.questions, question] }
              : p
          ),
        };
      });
      setExpanded(pillarId);
      setOkMsg(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : '新增題目失敗');
    }
  };

  const removeQuestion = (pillarId: string, qIndex: number) => {
    setLens((prev) => {
      if (!prev) return prev;
      const pillar = prev.pillars.find((p) => p.id === pillarId);
      if (!pillar || pillar.questions.length <= 1) {
        setError('每個支柱至少須保留 1 題');
        return prev;
      }
      if (!window.confirm('確定刪除此題？刪後只影響之後新評核。')) {
        return prev;
      }
      setError(null);
      setOkMsg(null);
      return {
        ...prev,
        pillars: prev.pillars.map((p) => {
          if (p.id !== pillarId) return p;
          return {
            ...p,
            questions: p.questions.filter((_, i) => i !== qIndex),
          };
        }),
      };
    });
  };

  const suggestPlan = async (
    pillarId: string,
    qIndex: number,
    cIndex: number,
    title: string
  ) => {
    try {
      const res = await fetch(
        apiUrl('/api/architecture/lens/suggest-improvement-plan'),
        {
          method: 'POST',
          headers: headers(),
          body: JSON.stringify({ title }),
        }
      );
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      updateChoice(pillarId, qIndex, cIndex, {
        improvementPlan: { displayText: data.displayText },
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : '產生建議失敗');
    }
  };

  const save = async () => {
    if (!lens) return;
    setSaving(true);
    setError(null);
    setOkMsg(null);
    try {
      for (const p of lens.pillars) {
        if (!p.questions.length) {
          throw new Error(`支柱 ${p.name || p.id} 至少須有 1 題`);
        }
      }
      const res = await fetch(apiUrl('/api/architecture/lens/active'), {
        method: 'PUT',
        headers: headers(),
        body: JSON.stringify({ lens, provider }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setLens(data.lens as Lens);
      setSource('database');
      setOkMsg('已儲存。之後新評核將使用此標準；歷史評核不變。');
    } catch (e) {
      setError(e instanceof Error ? e.message : '儲存失敗');
    } finally {
      setSaving(false);
    }
  };

  const providerSelect = (
    <label className="flex flex-col gap-1 text-xs font-semibold text-gray-500">
      雲端提供者
      <select
        className="border border-gray-200 rounded-xl px-3 py-2 text-sm font-semibold text-gray-800"
        value={provider}
        onChange={(e) => changeProvider(e.target.value)}
        disabled={saving}
      >
        <option value="aws">AWS</option>
        <option value="gcp">GCP</option>
        <option value="azure">Azure</option>
      </select>
    </label>
  );

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm flex flex-wrap items-end gap-3">
          {providerSelect}
        </div>
        <div className="bg-white border border-gray-100 rounded-2xl p-6 text-sm text-gray-500">
          載入 Lens 標準中…
        </div>
      </div>
    );
  }

  if (!lens) {
    return (
      <div className="space-y-4">
        <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm flex flex-wrap items-end gap-3">
          {providerSelect}
        </div>
        <div className="bg-white border border-red-100 rounded-2xl p-6 text-sm text-red-600">
          {error || '無法載入 Lens'}
        </div>
      </div>
    );
  }

  const pillarsSorted = [...lens.pillars].sort(
    (a, b) => PILLAR_ORDER.indexOf(a.id) - PILLAR_ORDER.indexOf(b.id)
  );

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-end gap-4">
          {providerSelect}
          <div>
            <h2 className="text-lg font-bold text-gray-900">Lens 審核標準</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              來源：{source === 'database' ? '資料庫（已自訂）' : '檔案預設'} ·{' '}
              {provider.toUpperCase()} · 需 A3「審核」權限 · 不修改 riskRules 條件式
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void load()}
            className="px-3 py-2 text-sm font-semibold text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50"
          >
            重新載入
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={() => void save()}
            className="px-4 py-2 text-sm font-semibold text-white bg-brand-600 rounded-xl hover:bg-brand-700 disabled:opacity-50"
          >
            {saving ? '儲存中…' : '儲存標準'}
          </button>
        </div>
      </div>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-3 py-2">
          {error}
        </div>
      )}
      {okMsg && (
        <div className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-xl px-3 py-2">
          {okMsg}
        </div>
      )}

      {pillarsSorted.map((pillar) => {
        const open = expanded === pillar.id;
        return (
          <div
            key={pillar.id}
            className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden"
          >
            <button
              type="button"
              className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50"
              onClick={() => setExpanded(open ? '' : pillar.id)}
            >
              <span className="font-bold text-gray-900">
                {pillar.name}{' '}
                <span className="text-xs font-semibold text-gray-400">
                  ({pillar.questions.length} 題)
                </span>
              </span>
              <span className="text-gray-400 text-sm">{open ? '▾' : '▸'}</span>
            </button>
            {open && (
              <div className="border-t border-gray-100 px-4 py-3 space-y-4">
                {pillar.questions.map((q, qi) => (
                  <div
                    key={q.id}
                    className="border border-gray-100 rounded-xl p-3 space-y-2 bg-gray-50/50"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <label className="flex-1 text-xs font-semibold text-gray-500">
                        題目標題
                        <input
                          className="mt-1 w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm font-semibold text-gray-800"
                          value={q.title}
                          onChange={(e) =>
                            updateQuestion(pillar.id, qi, {
                              title: e.target.value,
                            })
                          }
                        />
                      </label>
                      <button
                        type="button"
                        className="text-xs font-semibold text-red-600 hover:underline mt-5 shrink-0"
                        onClick={() => removeQuestion(pillar.id, qi)}
                      >
                        刪除
                      </button>
                    </div>
                    <label className="block text-xs font-semibold text-gray-500">
                      說明
                      <textarea
                        className="mt-1 w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm text-gray-800 min-h-[3rem]"
                        value={q.description || ''}
                        onChange={(e) =>
                          updateQuestion(pillar.id, qi, {
                            description: e.target.value,
                          })
                        }
                      />
                    </label>
                    <p className="text-[10px] text-gray-400 font-mono">id: {q.id}</p>
                    {q.choices.map((c, ci) => (
                      <div
                        key={c.id}
                        className="bg-white border border-gray-100 rounded-lg p-2 space-y-2"
                      >
                        <label className="block text-xs font-semibold text-gray-500">
                          選項文案
                          <input
                            className="mt-1 w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm text-gray-800"
                            value={c.title}
                            onChange={(e) =>
                              updateChoice(pillar.id, qi, ci, {
                                title: e.target.value,
                              })
                            }
                          />
                        </label>
                        <label className="block text-xs font-semibold text-gray-500">
                          改善建議（improvementPlan）
                          <textarea
                            className="mt-1 w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm text-gray-800 min-h-[2.5rem]"
                            value={c.improvementPlan?.displayText || ''}
                            onChange={(e) =>
                              updateChoice(pillar.id, qi, ci, {
                                improvementPlan: {
                                  displayText: e.target.value,
                                },
                              })
                            }
                          />
                        </label>
                        <button
                          type="button"
                          className="text-xs font-semibold text-brand-700 hover:underline"
                          onClick={() =>
                            void suggestPlan(pillar.id, qi, ci, q.title)
                          }
                        >
                          依題目標題產生預設建議
                        </button>
                      </div>
                    ))}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => void addQuestion(pillar.id)}
                  className="text-sm font-semibold text-brand-700 hover:underline"
                >
                  ＋ 新增題目（系統模板）
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

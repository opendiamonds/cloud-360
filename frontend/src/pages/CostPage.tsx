import React, { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiUrl } from '../config/api';
import { useAuth } from '../context/auth-context';
import { EstimateUploadZone } from '../components/cost/EstimateUploadZone';
import { EstimateCloudCard } from '../components/cost/EstimateCloudCard';
import { EstimateChecksPanel } from '../components/cost/EstimateChecksPanel';
import { EstimateHistoryDrawer } from '../components/cost/EstimateHistoryDrawer';
import { EstimateShareModal } from '../components/cost/EstimateShareModal';
import { EstimateSaveModal } from '../components/cost/EstimateSaveModal';
import { EstimateAdvicePanel } from '../components/cost/EstimateAdvicePanel';
import { EstimateOfficialCalculators } from '../components/cost/EstimateOfficialCalculators';
import {
  authHeaders,
  cloudLabel,
  type EstimateSetDetail,
  type EstimateSetSummary,
} from '../components/cost/types';

export const CostPage: React.FC = () => {
  const { can } = useAuth();
  const canView = can('C1', 'view');
  const canEdit = can('C1', 'edit');
  const [searchParams, setSearchParams] = useSearchParams();

  const [detail, setDetail] = useState<EstimateSetDetail | null>(null);
  const [history, setHistory] = useState<EstimateSetSummary[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const loadDetail = useCallback(async (id: number) => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(apiUrl(`/api/cost/v1/sets/${id}`), {
        headers: authHeaders(),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(typeof data.detail === 'string' ? data.detail : '載入失敗');
        setDetail(null);
        return;
      }
      const data = (await res.json()) as EstimateSetDetail;
      setDetail(data);
      setSearchParams({ estimate: String(id) }, { replace: true });
    } catch {
      setError('載入失敗');
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, [setSearchParams]);

  const refreshHistory = useCallback(async () => {
    try {
      const res = await fetch(apiUrl('/api/cost/v1/sets?include_history=true'), {
        headers: authHeaders(),
      });
      if (!res.ok) return [];
      const data = await res.json();
      const items = (data.items || data.sets || data) as EstimateSetSummary[];
      const list = Array.isArray(items) ? items : [];
      setHistory(list);
      return list;
    } catch {
      return [];
    }
  }, []);

  const deleteHistoryItem = useCallback(
    async (id: number) => {
      setError('');
      try {
        const res = await fetch(apiUrl(`/api/cost/v1/sets/${id}`), {
          method: 'DELETE',
          headers: authHeaders(),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          const detail =
            typeof data.detail === 'string' ? data.detail : `刪除失敗（HTTP ${res.status}）`;
          setError(detail);
          throw new Error(detail);
        }
        const remaining = await refreshHistory();
        if (detail?.id === id) {
          if (remaining.length > 0) {
            await loadDetail(remaining[0].id);
          } else {
            setDetail(null);
            setSearchParams({}, { replace: true });
            setLoading(false);
          }
        }
      } catch (e) {
        if (e instanceof Error && e.message) {
          /* error already set when from API */
        } else {
          setError('刪除失敗');
        }
        throw e;
      }
    },
    [detail?.id, loadDetail, refreshHistory, setSearchParams],
  );

  useEffect(() => {
    if (!canView) {
      setLoading(false);
      return;
    }
    const boot = async () => {
      const items = (await refreshHistory()) || [];
      const fromQuery = Number(searchParams.get('estimate') || '');
      if (fromQuery > 0) {
        await loadDetail(fromQuery);
        return;
      }
      if (items.length > 0) {
        await loadDetail(items[0].id);
        return;
      }
      setDetail(null);
      setLoading(false);
    };
    void boot();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- landing once on mount
  }, [canView]);

  if (!canView) {
    return (
      <div className="h-full overflow-y-auto bg-gray-50 p-6" data-testid="cost-page">
        <div className="max-w-5xl mx-auto">
          <p className="text-sm text-gray-600">您沒有檢視成本／估價工作區的權限。</p>
        </div>
      </div>
    );
  }

  const badgeText =
    detail == null
      ? ''
      : !detail.is_saved
        ? '尚未儲存'
        : detail.privacy === 'private'
          ? '僅自己可見'
          : '已分享';

  return (
    <div className="h-full overflow-y-auto bg-gray-50 p-6" data-testid="cost-page">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
              估價工作區
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              上傳官方估價表、檢視明細與機械檢查，並取得 AI 成本建議
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {detail && (
              <span
                data-testid="estimate-privacy-badge"
                className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-700"
              >
                {badgeText}
              </span>
            )}
            <button
              type="button"
              className="px-3 py-2 rounded-xl text-sm font-bold text-gray-700 bg-white border border-gray-200"
              onClick={async () => {
                await refreshHistory();
                setHistoryOpen(true);
              }}
            >
              歷史
            </button>
            {detail?.is_owner && canEdit && (
              <button
                type="button"
                data-testid="estimate-save-controls"
                className="px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm font-bold"
                onClick={() => setSaveOpen(true)}
              >
                {detail.is_saved ? '重新命名' : '儲存'}
              </button>
            )}
            {detail?.is_owner && detail.is_saved && (
              <button
                type="button"
                data-testid="estimate-share-controls"
                className="px-4 py-2 rounded-xl bg-brand-600 text-white text-sm font-bold"
                onClick={() => setShareOpen(true)}
              >
                分享
              </button>
            )}
          </div>
        </div>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <EstimateOfficialCalculators />

        <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm space-y-3">
          <div>
            <h2 className="text-sm font-bold text-gray-800">上傳估價表</h2>
            <p className="mt-1 text-xs text-gray-500">
              支援 AWS／GCP 的 CSV 與 Azure 的 XLSX；單一檔 ≤ 5MB，單次最多 3 檔。分析完成後請按「儲存」並命名，才會出現在歷史。
            </p>
          </div>
          <EstimateUploadZone
            canEdit={canEdit}
            compact={!!detail}
            onError={setError}
            onUploaded={(d) => {
              const next = d as EstimateSetDetail;
              setDetail(next);
              setSearchParams({ estimate: String(next.id) }, { replace: true });
            }}
          />
        </div>

        {loading && (
          <p className="text-sm text-gray-400">載入中…</p>
        )}

        {!loading && !detail && (
          <div className="bg-white border border-gray-100 rounded-2xl p-10 shadow-sm text-center">
            <p className="text-sm font-semibold text-gray-800">還沒有估價表</p>
            <p className="mt-2 text-sm text-gray-400">
              先用上方官方 Calculator 匯出估價，再上傳到本頁；上傳後會顯示逐項明細、檢查結果與 AI 建議。確認無誤後按「儲存」命名並寫入歷史。
            </p>
          </div>
        )}

        {detail && (
          <div className="space-y-4">
            <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-sm font-bold text-gray-800">
                  {detail.note?.trim() || '明細與機械檢查'}
                </h2>
                {!detail.is_saved && detail.is_owner && canEdit && (
                  <button
                    type="button"
                    className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-800"
                    onClick={() => setSaveOpen(true)}
                  >
                    儲存到歷史
                  </button>
                )}
              </div>
              {detail.estimates.map((est) => (
                <div key={est.cloud} className="space-y-2">
                  <EstimateCloudCard estimate={est} />
                  <EstimateChecksPanel
                    checks={est.checks}
                    cloudLabel={cloudLabel(est.cloud)}
                  />
                </div>
              ))}
            </div>

            <EstimateAdvicePanel
              estimateSetId={detail.id}
              adviceStatus={detail.advice_status}
            />
          </div>
        )}

        <EstimateHistoryDrawer
          open={historyOpen}
          onClose={() => setHistoryOpen(false)}
          items={history}
          canEdit={canEdit}
          onSelect={(id) => void loadDetail(id)}
          onDelete={deleteHistoryItem}
        />
        <EstimateSaveModal
          isOpen={saveOpen}
          onClose={() => setSaveOpen(false)}
          estimateSetId={detail?.id ?? null}
          initialName={detail?.note}
          onSaved={(d) => {
            const next = d as EstimateSetDetail;
            setDetail(next);
            void refreshHistory();
          }}
        />
        <EstimateShareModal
          isOpen={shareOpen}
          onClose={() => setShareOpen(false)}
          estimateSetId={detail?.id ?? null}
          onSaved={() => {
            if (detail) void loadDetail(detail.id);
            void refreshHistory();
          }}
        />
      </div>
    </div>
  );
};

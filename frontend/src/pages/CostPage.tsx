import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiUrl } from '../config/api';
import { useAuth } from '../context/auth-context';
import { cloudDisplayName, regionsForCloud } from '../cost/supportedRegions';

type Snapshot = {
  id: number;
  region: string | null;
  region_required: boolean;
  diagram_cloud?: string | null;
  allowed_regions?: string[];
  lines: Array<{
    mxcell_id: string;
    label: string;
    hours: number;
    subtotal: number | null;
    status: string;
    hourly_list: number | null;
    sku?: string | null;
    mapping_note?: string | null;
  }>;
  total: number | null;
  unpriced_count: number;
  pie: Record<string, number>;
  coverage: Array<{ cloud: string; mode: string }>;
  pricing_source?: string | null;
  pricing_error?: string | null;
  pricing_as_of?: string | null;
  agent_assumptions?: string[] | null;
  calculator_lines?: Array<{
    map_key?: string | null;
    mxcell_id?: string | null;
    label?: string | null;
    product_name: string;
    specification: string;
    monthly_usd: number;
  }> | null;
};

const PIE_LABELS: Record<string, string> = {
  compute: '運算',
  database: '資料庫',
  network: '網路',
  other: '其他',
};

const SELECT_CLASS =
  'border border-gray-200 rounded-xl px-3 py-2 text-sm font-semibold text-gray-800 min-w-[12rem] bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/30 disabled:bg-gray-50 disabled:text-gray-400';

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function formatCoverage(coverage: Snapshot['coverage']): string {
  return coverage
    .map((c) => {
      const name = c.cloud === 'aws' ? 'AWS' : c.cloud === 'gcp' ? 'GCP' : 'Azure';
      return c.mode === 'official_list' ? `${name} 走官方價` : `${name} 全 Manual Override`;
    })
    .join(' · ');
}

function lineStatusLabel(status: string, _sku: string | null | undefined): string {
  switch (status) {
    case 'price_fetch_failed':
      return '官方價查詢失敗（網路逾時或未預熱快取）';
    case 'manual_override':
      return '手動覆寫單價';
    case 'priced':
      return '';
    default:
      return '無法對應可估價 SKU，或此服務尚無官方定價規格';
  }
}

/** 依偵測雲端產生「首次查價」提示（來源與耗時不同） */
function firstFetchHint(cloud: string | null | undefined): string {
  switch (cloud) {
    case 'aws':
      return '首次查 AWS 官方價（Price List）可能需 1–2 分鐘';
    case 'gcp':
      return 'GCP 架構圖將由 Agent 開啟 Pricing Calculator 估算，可能需要 1–2 分鐘';
    case 'azure':
      return 'Azure 架構圖將由 Agent 開啟 Pricing Calculator 估算，可能需要 1–2 分鐘';
    default:
      return '首次查官方價可能需數秒至數分鐘（依雲端而定）';
  }
}

function pricingSourceShort(cloud: string | null | undefined): string {
  switch (cloud) {
    case 'aws':
      return 'AWS Price List';
    case 'gcp':
      return 'GCP Billing Catalog';
    case 'azure':
      return 'Azure Retail Prices';
    default:
      return '雲端官方價目';
  }
}

function formatPricingSourceLabel(
  pricingSource: string | null | undefined,
  diagramCloud: string | null | undefined,
): string {
  switch (pricingSource) {
    case 'azure_calculator':
      return 'Azure Pricing Calculator（官方估價工具）';
    case 'azure_calculator_failed':
      return 'Azure Pricing Calculator 估價失敗';
    case 'gcp_calculator':
      return 'GCP Pricing Calculator（官方估價工具）';
    case 'gcp_calculator_failed':
      return 'GCP Pricing Calculator 估價失敗';
    case 'aws_calculator':
      return 'AWS Pricing Calculator（官方估價工具）';
    default:
      return pricingSourceShort(diagramCloud);
  }
}

function isCalculatorPricing(pricingSource: string | null | undefined): boolean {
  return (
    pricingSource === 'azure_calculator' ||
    pricingSource === 'gcp_calculator' ||
    pricingSource === 'aws_calculator'
  );
}

function isCalculatorFailed(pricingSource: string | null | undefined): boolean {
  return (
    pricingSource === 'azure_calculator_failed' ||
    pricingSource === 'gcp_calculator_failed'
  );
}

function usesCalculatorAgent(diagramCloud: string | null | undefined): boolean {
  return diagramCloud === 'azure' || diagramCloud === 'gcp';
}

function calculatorCloudLabel(diagramCloud: string | null | undefined): string {
  if (diagramCloud === 'gcp') return 'Google Cloud';
  if (diagramCloud === 'azure') return 'Azure';
  return '雲端';
}

function calculatorExportPath(snapshot: Snapshot): string {
  if (snapshot.diagram_cloud === 'gcp') {
    return `/api/cost/diagrams/${snapshot.id}/calculator-export/csv`;
  }
  return `/api/cost/diagrams/${snapshot.id}/calculator-export/xlsx`;
}

function calculatorExportDefaultFilename(snapshot: Snapshot): string {
  const region = snapshot.region || 'estimate';
  if (snapshot.diagram_cloud === 'gcp') {
    return `gcp-calculator-estimate-${region}.csv`;
  }
  return `ExportedEstimate-${region}.xlsx`;
}

function calculatorExportButtonLabel(
  isExporting: boolean,
  diagramCloud: string | null | undefined,
): string {
  if (isExporting) {
    return diagramCloud === 'gcp'
      ? '正在填寫 Calculator 並匯出 CSV…'
      : '正在填寫 Calculator 並匯出 Excel…';
  }
  return diagramCloud === 'gcp' ? '匯出官方 Calculator CSV' : '匯出官方 Calculator Excel';
}

function calculatorExportHint(diagramCloud: string | null | undefined): string {
  if (diagramCloud === 'gcp') {
    return '按鈕會以與估價相同的資源／數量重新填寫 Google Cloud Pricing Calculator，再點官方 Download estimate as .csv（可能需要 1–2 分鐘）。';
  }
  return '按鈕會以與估價相同的資源／數量重新填寫 Azure Pricing Calculator，再點官方 Export 下載 .xlsx（可能需要 1–2 分鐘）。';
}

function calculatorBreakdownHint(diagramCloud: string | null | undefined): string {
  const vendor = calculatorCloudLabel(diagramCloud);
  return `以下為 ${vendor} Pricing Calculator 各產品列的規格與 Monthly 價格（與上方總價同源）。`;
}

function formatPricingAsOf(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleString('zh-TW', { hour12: false });
}

function refreshHint(
  diagramCloud: string | null | undefined,
  pricingSource: string | null | undefined,
): string {
  if (
    diagramCloud === 'azure' ||
    pricingSource === 'azure_calculator' ||
    pricingSource === 'azure_calculator_failed'
  ) {
    return '正在透過 Azure Pricing Calculator 即時估算…（可能需要 1–2 分鐘）';
  }
  if (
    diagramCloud === 'gcp' ||
    pricingSource === 'gcp_calculator' ||
    pricingSource === 'gcp_calculator_failed'
  ) {
    return '正在透過 Google Cloud Pricing Calculator 即時估算…（可能需要 1–2 分鐘）';
  }
  return firstFetchHint(diagramCloud);
}

export const CostPage: React.FC = () => {
  const navigate = useNavigate();
  const { can } = useAuth();
  const [params, setParams] = useSearchParams();
  const [diagrams, setDiagrams] = useState<Array<{ id: number; title: string }>>([]);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [status, setStatus] = useState<'loading' | 'idle' | 'ready' | 'error' | 'empty'>('loading');
  const [error, setError] = useState<string | null>(null);
  const [selectedDiagramId, setSelectedDiagramId] = useState<number | null>(null);
  const [hasEstimated, setHasEstimated] = useState(false);
  const [regionValue, setRegionValue] = useState('');
  const [regionSaving, setRegionSaving] = useState(false);
  const [regionError, setRegionError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isEstimating, setIsEstimating] = useState(false);
  const [isExportingExcel, setIsExportingExcel] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const diagramIdFromUrl = params.get('diagram') ? Number(params.get('diagram')) : null;
  const canEditRegion = can('C1r', 'edit');
  const regionOptions = regionsForCloud(snapshot?.diagram_cloud);
  const detectedCloudLabel = cloudDisplayName(snapshot?.diagram_cloud);
  const canRunEstimate =
    selectedDiagramId != null &&
    Boolean(regionValue) &&
    !regionSaving &&
    !isRefreshing &&
    !isEstimating;

  const canExportExcel =
    hasEstimated &&
    isCalculatorPricing(snapshot?.pricing_source) &&
    Boolean(snapshot?.region);

  const loadSnapshot = useCallback(
    async (id: number, options?: { runAgent?: boolean; estimating?: boolean }) => {
      const runAgent = options?.runAgent ?? true;
      const estimating = options?.estimating ?? runAgent;

      if (estimating) {
        setIsEstimating(true);
      } else {
        setIsRefreshing(true);
      }

      const query = runAgent ? '' : '?run_agent=false';
      const res = await fetch(apiUrl(`/api/cost/diagrams/${id}${query}`), {
        headers: authHeaders(),
      });
      if (!res.ok) {
        if (selectedDiagramId === id) {
          setStatus('error');
          setError(`載入失敗 (${res.status})`);
        }
        setIsRefreshing(false);
        setIsEstimating(false);
        return false;
      }
      const data = (await res.json()) as Snapshot;
      setSnapshot(data);
      setRegionValue(data.region ?? '');
      setSelectedDiagramId(id);
      setStatus('ready');
      if (runAgent) {
        setHasEstimated(true);
      }
      setIsRefreshing(false);
      setIsEstimating(false);
      return true;
    },
    [selectedDiagramId],
  );

  useEffect(() => {
    (async () => {
      const listRes = await fetch(apiUrl('/api/cost/diagrams'), { headers: authHeaders() });
      if (!listRes.ok) {
        setStatus('error');
        setError('無法載入圖列表');
        return;
      }
      const list = (await listRes.json()) as { items: Array<{ id: number; title: string }> };
      setDiagrams(list.items);
      if (list.items.length === 0) {
        setStatus('empty');
        return;
      }

      const urlId =
        diagramIdFromUrl && list.items.some((d) => d.id === diagramIdFromUrl)
          ? diagramIdFromUrl
          : null;
      setSelectedDiagramId(urlId);
      setStatus('idle');
    })();
  }, [diagramIdFromUrl]);

  const onDiagramSelect = async (rawId: string) => {
    const id = Number(rawId);
    if (!rawId || Number.isNaN(id)) {
      setSelectedDiagramId(null);
      setSnapshot(null);
      setHasEstimated(false);
      setExportReady(false);
      setExportError(null);
      setRegionValue('');
      setRegionError(null);
      setParams({}, { replace: true });
      setStatus('idle');
      return;
    }

    setSelectedDiagramId(id);
    setHasEstimated(false);
    setExportError(null);
    setRegionError(null);
    setParams({ diagram: String(id) }, { replace: true });
    setStatus('loading');
    await loadSnapshot(id, { runAgent: false, estimating: false });
  };

  const onRunEstimate = async () => {
    if (!selectedDiagramId || !canRunEstimate) return;
    await loadSnapshot(selectedDiagramId, { runAgent: true, estimating: true });
  };

  const onExportCalculatorExport = async () => {
    if (!snapshot || !canExportExcel) return;
    setExportError(null);
    setIsExportingExcel(true);
    try {
      const res = await fetch(apiUrl(calculatorExportPath(snapshot)), {
        headers: authHeaders(),
      });
      if (!res.ok) {
        let detail = `匯出失敗 (${res.status})`;
        try {
          const body = (await res.json()) as { detail?: string };
          if (typeof body.detail === 'string' && body.detail.trim()) {
            detail = body.detail;
          }
        } catch {
          /* ignore */
        }
        setExportError(detail);
        return;
      }
      const blob = await res.blob();
      const disposition = res.headers.get('Content-Disposition') || '';
      const match = disposition.match(/filename=\"?([^\";]+)\"?/i);
      const filename = match?.[1] || calculatorExportDefaultFilename(snapshot);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } finally {
      setIsExportingExcel(false);
    }
  };

  useEffect(() => {
    if (status !== 'idle' || selectedDiagramId == null || snapshot?.id === selectedDiagramId) {
      return;
    }
    void loadSnapshot(selectedDiagramId, { runAgent: false, estimating: false });
  }, [status, selectedDiagramId, snapshot?.id, loadSnapshot]);

  const onRegionChange = async (region: string) => {
    if (!snapshot || !canEditRegion || !region) return;
    setRegionValue(region);
    setRegionError(null);
    setRegionSaving(true);
    try {
      const res = await fetch(apiUrl(`/api/cost/diagrams/${snapshot.id}/region`), {
        method: 'PUT',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ region }),
      });
      if (!res.ok) {
        setRegionValue(snapshot.region ?? '');
        let detail = `儲存區域失敗 (${res.status})`;
        try {
          const body = (await res.json()) as { detail?: string };
          if (typeof body.detail === 'string' && body.detail.trim()) {
            detail = body.detail;
          }
        } catch {
          /* ignore */
        }
        setRegionError(
          res.status === 403 ? '權限不足：您的角色無法設定估價區域' : detail,
        );
        return;
      }
      await loadSnapshot(snapshot.id, { runAgent: true, estimating: true });
    } finally {
      setRegionSaving(false);
    }
  };

  const onHoursCommit = async (mxcellId: string, hours: number) => {
    if (!snapshot) return;
    if (hours < 0 || hours > 24 || !Number.isInteger(hours)) return;
    await fetch(apiUrl(`/api/cost/diagrams/${snapshot.id}/lines/${mxcellId}/hours`), {
      method: 'PUT',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ hours }),
    });
    await loadSnapshot(snapshot.id, { runAgent: true, estimating: true });
  };

  const coverageText = snapshot?.coverage ? formatCoverage(snapshot.coverage) : '';
  const fetchFailedCount = snapshot?.lines.filter((l) => l.status === 'price_fetch_failed').length ?? 0;
  const pieTotal = snapshot
    ? Object.values(snapshot.pie).reduce((sum, v) => sum + Number(v), 0)
    : 0;
  const calculatorLines = snapshot?.calculator_lines ?? [];
  const calculatorLinesTotal = calculatorLines.reduce(
    (sum, row) => sum + Number(row.monthly_usd),
    0,
  );

  return (
    <div className="h-full overflow-y-auto bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">預估成本</h1>
            <p className="text-sm text-gray-500 mt-1">
              從架構圖萃取資源、查詢雲端單價並估算每月 TCO（支援 AWS／GCP／Azure 官方價）
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/workspace')}
            className="text-sm font-semibold text-brand-700 hover:underline shrink-0"
          >
            返回工作區
          </button>
        </div>

        {status === 'loading' && (
          <div className="bg-white border border-gray-100 rounded-2xl p-10 shadow-sm text-center">
            <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600 mb-3">
              <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            </div>
            <p className="text-sm font-semibold text-gray-700">載入架構圖設定中…</p>
          </div>
        )}

        {status === 'idle' && diagrams.length > 0 && (
          <div className="bg-white border border-gray-100 rounded-2xl p-10 shadow-sm text-center space-y-3">
            <p className="text-base font-bold text-gray-800">請先選擇要估價的架構圖</p>
            <p className="text-sm text-gray-500 max-w-md mx-auto">
              選定架構圖與估價區域後，再按「開始估價」才會查詢官方定價或開啟雲端 Pricing Calculator。
            </p>
          </div>
        )}

        {status === 'empty' && (
          <div className="bg-white border border-gray-100 rounded-2xl p-10 shadow-sm text-center space-y-4">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gray-100 text-gray-400">
              <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <div>
              <p className="text-base font-bold text-gray-800">尚無可估價的架構圖</p>
              <p className="text-sm text-gray-500 mt-1 max-w-md mx-auto">
                請先在「架構圖生成」建立或上傳架構圖，完成後即可在此查看每月預估成本。
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate('/workspace')}
              className="inline-flex px-4 py-2 rounded-xl bg-brand-600 text-white text-sm font-bold hover:bg-brand-700 transition-colors"
            >
              前往架構工作區
            </button>
          </div>
        )}

        {status === 'error' && (
          <div className="bg-white border border-red-100 rounded-2xl p-5 shadow-sm space-y-3">
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-red-50 text-red-600">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <div>
                <p className="text-sm font-bold text-red-800">無法載入成本資料</p>
                <p className="text-sm text-red-600 mt-0.5">{error}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="text-xs font-bold text-brand-700 px-3 py-1.5 rounded-lg bg-brand-50"
            >
              重新載入
            </button>
          </div>
        )}

        {diagrams.length > 0 && status !== 'empty' && status !== 'error' && (
          <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm space-y-3">
            <h2 className="text-sm font-bold text-gray-800">估價設定</h2>
            <div className="flex flex-wrap gap-4 items-end">
              <label className="flex flex-col gap-1 text-xs font-semibold text-gray-500">
                架構圖
                <select
                  className={SELECT_CLASS}
                  value={selectedDiagramId ?? ''}
                  disabled={status === 'loading' || isEstimating}
                  onChange={(e) => onDiagramSelect(e.target.value)}
                >
                  <option value="">— 請選擇架構圖 —</option>
                  {diagrams.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.title}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-xs font-semibold text-gray-500">
                估價區域
                <select
                  data-testid="cost-region"
                  className={SELECT_CLASS}
                  value={regionValue}
                  disabled={
                    !canEditRegion ||
                    status === 'loading' ||
                    !snapshot ||
                    regionSaving ||
                    isRefreshing ||
                    isEstimating
                  }
                  onChange={(e) => onRegionChange(e.target.value)}
                >
                  <option value="">— 選擇區域 —</option>
                  {regionOptions.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                data-testid="cost-run-estimate"
                disabled={!canRunEstimate}
                onClick={() => void onRunEstimate()}
                className="inline-flex items-center justify-center px-4 py-2 rounded-xl bg-brand-600 text-white text-sm font-bold hover:bg-brand-700 transition-colors disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed"
              >
                {isEstimating ? '估價中…' : '開始估價'}
              </button>
            </div>
            {snapshot?.diagram_cloud && (
              <p className="text-xs text-gray-500">
                依架構圖元件偵測為 <span className="font-bold text-gray-700">{detectedCloudLabel}</span>
                ，僅列出該雲端區域
                {regionOptions.length === 0 ? '（目前無可用區域）' : ''}
              </p>
            )}
            {!snapshot?.diagram_cloud && snapshot && (
              <p className="text-xs text-amber-700">
                無法判斷架構圖雲端，暫顯示全部區域。請確認圖上元件可對應到 AWS／GCP／Azure。
              </p>
            )}
            {(regionSaving || isRefreshing || isEstimating) && canEditRegion && (
              <p className="text-xs text-gray-500">
                {isEstimating ? (
                  <>
                    正在估價…（
                    {refreshHint(snapshot?.diagram_cloud, snapshot?.pricing_source)}）
                  </>
                ) : (
                  '正在更新架構圖設定…'
                )}
              </p>
            )}
            {!hasEstimated && snapshot && regionValue && !isEstimating && (
              <div className="rounded-xl bg-brand-50 border border-brand-100 px-4 py-2.5 text-sm text-brand-900">
                <span className="font-bold">已選定區域，尚未估價</span>
                <span className="text-brand-800">
                  {' '}
                  — 請按「開始估價」查詢官方定價
                  {usesCalculatorAgent(snapshot.diagram_cloud)
                    ? `（${calculatorCloudLabel(snapshot.diagram_cloud)} 將開啟 Pricing Calculator，約 1–2 分鐘）`
                    : ''}
                  。
                </span>
              </div>
            )}
            {regionError && (
              <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-2.5 text-sm text-red-800">
                {regionError}
              </div>
            )}
            {snapshot?.region_required && canEditRegion && (
              <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-2.5 text-sm text-amber-900">
                <span className="font-bold">請先選擇估價區域</span>
                <span className="text-amber-800">
                  {' '}
                  — 選定後才會
                  {usesCalculatorAgent(snapshot.diagram_cloud)
                    ? `透過 ${calculatorCloudLabel(snapshot.diagram_cloud)} Pricing Calculator 或官方 API 估算月估總額`
                    : `查詢 ${pricingSourceShort(snapshot.diagram_cloud)} 並計算月估總額`}
                  。
                </span>
              </div>
            )}
            {snapshot?.region_required && !canEditRegion && (
              <div className="rounded-xl bg-slate-50 border border-slate-200 px-4 py-2.5 text-sm text-slate-800">
                <span className="font-bold">此架構圖尚未設定估價區域</span>
                <span className="text-slate-600">
                  {' '}
                  — 您目前的角色只能檢視成本，無法變更區域。請由具{' '}
                  <span className="font-semibold">Project_Architect</span> 權限的架構師在上方選定區域後，才會顯示月估總額。
                </span>
              </div>
            )}
          </div>
        )}

        {snapshot && status === 'ready' && hasEstimated && (
          <>
            <div data-slot="cost-overspend" />

            <div
              className="bg-white border border-brand-100 rounded-2xl p-5 shadow-sm space-y-4"
              aria-live="polite"
            >
              <h2 className="text-sm font-bold text-gray-800">月估總額</h2>
              <div className="flex flex-wrap items-baseline gap-3">
                {snapshot.total != null ? (
                  <>
                    <p className="text-3xl font-bold text-gray-900" data-testid="cost-total">
                      ${snapshot.total.toFixed(2)}
                      <span className="text-lg font-semibold text-gray-500 ml-1">/ 月</span>
                    </p>
                    {isCalculatorPricing(snapshot.pricing_source) && (
                      <span
                        className="inline-flex items-center px-2.5 py-1 rounded-lg bg-brand-50 text-brand-800 text-xs font-bold border border-brand-100"
                        data-testid="cost-calculator-badge"
                      >
                        Calculator 總價
                      </span>
                    )}
                  </>
                ) : isCalculatorFailed(snapshot.pricing_source) ? (
                  <div className="space-y-2" data-testid="cost-total">
                    <p className="text-lg font-semibold text-red-700">
                      {formatPricingSourceLabel(snapshot.pricing_source, snapshot.diagram_cloud)}
                    </p>
                    {snapshot.pricing_error && (
                      <p className="text-sm text-red-600">{snapshot.pricing_error}</p>
                    )}
                    <p className="text-xs text-gray-500">
                      若瀏覽器主控台出現「message channel closed」，通常來自瀏覽器擴充功能，可忽略；請確認後端已安裝
                      Playwright Chromium（<code className="text-xs">playwright install chromium</code>）。
                    </p>
                  </div>
                ) : snapshot.unpriced_count > 0 ? (
                  <p className="text-lg font-semibold text-gray-600" data-testid="cost-total">
                    {fetchFailedCount > 0
                      ? `${detectedCloudLabel === '未知' ? '官方' : detectedCloudLabel} 官方價尚未就緒（請稍候或執行預熱腳本）`
                      : '尚無完整估價（部分資源無法對應或未支援）'}
                  </p>
                ) : (
                  <p className="text-lg font-semibold text-gray-400" data-testid="cost-total">
                    —
                  </p>
                )}
                {snapshot.unpriced_count > 0 && (
                  <span
                    className="inline-flex items-center px-2.5 py-1 rounded-lg bg-amber-50 text-amber-800 text-xs font-bold border border-amber-100"
                    data-testid="cost-unpriced-count"
                  >
                    {snapshot.unpriced_count} 項尚未定價
                  </span>
                )}
              </div>
              {(snapshot.pricing_source || snapshot.pricing_as_of) && (
                <p
                  className="text-sm text-gray-600"
                  data-testid="cost-pricing-source"
                >
                  <span className="font-semibold text-gray-700">總價來源：</span>
                  {formatPricingSourceLabel(snapshot.pricing_source, snapshot.diagram_cloud)}
                  {formatPricingAsOf(snapshot.pricing_as_of) && (
                    <span className="text-gray-400 ml-2">
                      （{formatPricingAsOf(snapshot.pricing_as_of)}）
                    </span>
                  )}
                </p>
              )}
              {isCalculatorPricing(snapshot.pricing_source) && (
                <div className="flex flex-wrap items-center gap-3 pt-1">
                  <button
                    type="button"
                    data-testid="cost-calculator-export-official"
                    disabled={isExportingExcel || isEstimating || !canExportExcel}
                    onClick={() => void onExportCalculatorExport()}
                    className="inline-flex items-center justify-center px-4 py-2 rounded-xl border border-brand-200 bg-white text-brand-800 text-sm font-bold hover:bg-brand-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {calculatorExportButtonLabel(isExportingExcel, snapshot.diagram_cloud)}
                  </button>
                  <p className="text-xs text-gray-500">{calculatorExportHint(snapshot.diagram_cloud)}</p>
                </div>
              )}
              {exportError && (
                <p className="text-sm text-red-600" data-testid="cost-calculator-export-error">
                  {exportError}
                </p>
              )}
              {isCalculatorPricing(snapshot.pricing_source) && (
                <p className="text-xs text-gray-500">
                  月估總額取自雲端供應商 Pricing Calculator 的 Estimated monthly cost；下方資源列的小計僅供參考，加總可能與總價不一致。
                </p>
              )}
              {snapshot.agent_assumptions && snapshot.agent_assumptions.length > 0 && (
                <details
                  className="text-xs text-gray-500 border border-gray-100 rounded-xl px-3 py-2"
                  data-testid="cost-calculator-assumptions"
                >
                  <summary className="cursor-pointer font-semibold text-gray-600 select-none">
                    Calculator 假設摘要（{snapshot.agent_assumptions.length} 項）
                  </summary>
                  <ul className="mt-2 space-y-1 list-disc list-inside text-gray-600">
                    {snapshot.agent_assumptions.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </details>
              )}
              {coverageText && (
                <p className="text-sm text-gray-500 border-t border-gray-100 pt-3">
                  <span className="font-semibold text-gray-600">定價假設：</span>
                  {coverageText}
                </p>
              )}
            </div>

            {isCalculatorPricing(snapshot.pricing_source) && calculatorLines.length > 0 && (
              <div
                className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm overflow-hidden"
                data-testid="cost-calculator-breakdown"
              >
                <h2 className="text-sm font-bold text-gray-800 mb-1">Calculator 估價明細</h2>
                <p className="text-xs text-gray-500 mb-4">
                  {calculatorBreakdownHint(snapshot.diagram_cloud)}
                </p>
                <div className="overflow-x-auto -mx-1">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 text-left">
                        <th className="py-3 px-2 text-xs font-bold text-gray-500 uppercase tracking-wide">
                          架構元件
                        </th>
                        <th className="py-3 px-2 text-xs font-bold text-gray-500 uppercase tracking-wide">
                          Calculator 產品
                        </th>
                        <th className="py-3 px-2 text-xs font-bold text-gray-500 uppercase tracking-wide">
                          選擇規格
                        </th>
                        <th className="py-3 px-2 text-xs font-bold text-gray-500 uppercase tracking-wide text-right">
                          月費 (USD)
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {calculatorLines.map((row, index) => (
                        <tr
                          key={`${row.product_name}-${row.map_key ?? index}`}
                          className="hover:bg-gray-50/80 transition-colors"
                          data-testid="cost-calculator-line"
                        >
                          <td className="py-3 px-2 font-semibold text-gray-900">
                            {row.label || '—'}
                          </td>
                          <td className="py-3 px-2 text-gray-800">{row.product_name}</td>
                          <td className="py-3 px-2 text-gray-600 text-xs leading-relaxed max-w-md">
                            {row.specification}
                          </td>
                          <td className="py-3 px-2 text-right font-bold text-gray-900 tabular-nums">
                            ${Number(row.monthly_usd).toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="border-t border-gray-200 bg-gray-50/80">
                        <td
                          colSpan={3}
                          className="py-3 px-2 text-sm font-bold text-gray-700 text-right"
                        >
                          Calculator 項目加總
                        </td>
                        <td
                          className="py-3 px-2 text-right text-base font-bold text-brand-700 tabular-nums"
                          data-testid="cost-calculator-lines-total"
                        >
                          ${calculatorLinesTotal.toFixed(2)}
                        </td>
                      </tr>
                      <tr className="border-t border-gray-100">
                        <td
                          colSpan={3}
                          className="py-2 px-2 text-xs font-semibold text-gray-500 text-right"
                        >
                          Estimated monthly cost（頁面總價）
                        </td>
                        <td className="py-2 px-2 text-right text-sm font-bold text-gray-900 tabular-nums">
                          {snapshot.total != null ? `$${snapshot.total.toFixed(2)}` : '—'}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            )}

            <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm space-y-4">
              <h2 className="text-sm font-bold text-gray-800">成本組成</h2>
              <div data-testid="cost-pie-legend" className="space-y-3">
                {Object.entries(snapshot.pie).map(([key, value]) => {
                  const amount = Number(value);
                  const pct = pieTotal > 0 ? Math.round((amount / pieTotal) * 100) : 0;
                  return (
                    <div key={key} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-semibold text-gray-700">
                          {PIE_LABELS[key] ?? key}
                          <span className="ml-2 text-xs font-normal text-gray-400">{key}</span>
                        </span>
                        <span className="font-bold text-gray-900 tabular-nums">
                          {key}: ${amount.toFixed(2)}
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-brand-500 transition-all duration-300"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm overflow-hidden">
              <h2 className="text-sm font-bold text-gray-800 mb-4">資源明細</h2>
              {snapshot.lines.length === 0 ? (
                <p className="text-sm text-gray-400 py-6 text-center">
                  此架構圖尚無可估價的雲端資源節點
                </p>
              ) : (
                <div className="overflow-x-auto -mx-1">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 text-left">
                        <th className="py-3 px-2 text-xs font-bold text-gray-500 uppercase tracking-wide">
                          資源
                        </th>
                        <th className="py-3 px-2 text-xs font-bold text-gray-500 uppercase tracking-wide">
                          每日時數
                        </th>
                        <th className="py-3 px-2 text-xs font-bold text-gray-500 uppercase tracking-wide text-right">
                          月小計
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {snapshot.lines.map((line) => (
                        <tr key={line.mxcell_id} className="hover:bg-gray-50/80 transition-colors">
                          <td className="py-3 px-2">
                            <div className="font-semibold text-gray-900">{line.label}</div>
                            {line.status !== 'priced' && line.status !== 'manual_override' && (
                              <div className="text-xs text-amber-600 mt-0.5">
                                {lineStatusLabel(line.status, line.sku)}
                              </div>
                            )}
                            {line.mapping_note && (
                              <div className="text-xs text-brand-700 mt-0.5">{line.mapping_note}</div>
                            )}
                          </td>
                          <td className="py-3 px-2">
                            <input
                              type="number"
                              min={0}
                              max={24}
                              data-testid="cost-hours-input"
                              data-mxcell-id={line.mxcell_id}
                              className="w-20 border border-gray-200 rounded-xl px-3 py-2 text-sm font-semibold text-gray-800 text-center focus:outline-none focus:ring-2 focus:ring-brand-500/30 disabled:bg-gray-50 disabled:text-gray-400"
                              defaultValue={line.hours}
                              readOnly={!can('C1h', 'edit')}
                              onBlur={(e) => {
                                const h = parseInt(e.target.value, 10);
                                if (!Number.isNaN(h)) onHoursCommit(line.mxcell_id, h);
                              }}
                            />
                          </td>
                          <td className="py-3 px-2 text-right font-bold text-gray-900 tabular-nums">
                            {line.subtotal != null ? `$${line.subtotal.toFixed(2)}` : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

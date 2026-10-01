/** Workload / budget context collected before estimate upload (for AI advice). */

import type { ReactNode } from 'react';
import type { WorkloadContext } from './workloadContext';

type Props = {
  value: WorkloadContext;
  onChange: (next: WorkloadContext) => void;
  disabled?: boolean;
};

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block space-y-1">
      <span className="text-xs font-semibold text-gray-700">{label}</span>
      {hint && <span className="block text-[11px] text-gray-400 leading-snug">{hint}</span>}
      {children}
    </label>
  );
}

const inputCls =
  'w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 placeholder:text-gray-400';
const areaCls = `${inputCls} min-h-[72px] resize-y`;

export function EstimateWorkloadForm({ value, onChange, disabled }: Props) {
  const set = (key: keyof WorkloadContext, v: string) =>
    onChange({ ...value, [key]: v });

  return (
    <section
      data-testid="estimate-workload-form"
      className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm space-y-4"
    >
      <div>
        <h2 className="text-sm font-bold text-gray-800">工作負載與預算（給 AI 建議用）</h2>
        <p className="mt-1 text-xs text-gray-500 leading-relaxed">
          選填。填得越完整，建議越能對齊你的系統說明、合規、費用上限與流量假設；會與估價表明細一併送交 AI。
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="md:col-span-2">
          <Field
            label="系統說明"
            hint="用途、主要元件、環境（正式／測試）、是否已上線"
          >
            <textarea
              className={areaCls}
              disabled={disabled}
              value={value.system_description}
              onChange={(e) => set('system_description', e.target.value)}
              placeholder="例：B2B SaaS 後台，API＋DB＋物件儲存，正式環境在亞太"
            />
          </Field>
        </div>

        <div className="md:col-span-2">
          <Field
            label="資訊需求／合規"
            hint="資料駐留、加密、稽核、備份 RPO／RTO、個資等級"
          >
            <textarea
              className={areaCls}
              disabled={disabled}
              value={value.information_requirements}
              onChange={(e) => set('information_requirements', e.target.value)}
              placeholder="例：資料須留在台灣／新加坡；日誌保留 90 天；需加密靜態資料"
            />
          </Field>
        </div>

        <Field label="月預算上限" hint="不含或含稅請在下方備註說明">
          <div className="flex gap-2">
            <input
              type="number"
              min={0}
              step="any"
              className={inputCls}
              disabled={disabled}
              value={value.monthly_budget}
              onChange={(e) => set('monthly_budget', e.target.value)}
              placeholder="例：5000"
            />
            <select
              className={`${inputCls} max-w-[100px]`}
              disabled={disabled}
              value={value.budget_currency || 'USD'}
              onChange={(e) => set('budget_currency', e.target.value)}
            >
              <option value="USD">USD</option>
              <option value="TWD">TWD</option>
              <option value="EUR">EUR</option>
            </select>
          </div>
        </Field>

        <Field label="其他費用限制" hint="承諾折扣偏好、是否接受預付、稅務">
          <input
            className={inputCls}
            disabled={disabled}
            value={value.cost_constraints}
            onChange={(e) => set('cost_constraints', e.target.value)}
            placeholder="例：優先用 Savings Plan／CUD；可接受 1 年預付"
          />
        </Field>

        <Field label="月出站流量 (GB)" hint="Internet egress，不含同區內網">
          <input
            type="number"
            min={0}
            step="any"
            className={inputCls}
            disabled={disabled}
            value={value.monthly_egress_gb}
            onChange={(e) => set('monthly_egress_gb', e.target.value)}
            placeholder="例：2000"
          />
        </Field>

        <Field label="峰值頻寬 (Mbps)" hint="尖峰對外吞吐">
          <input
            type="number"
            min={0}
            step="any"
            className={inputCls}
            disabled={disabled}
            value={value.peak_bandwidth_mbps}
            onChange={(e) => set('peak_bandwidth_mbps', e.target.value)}
            placeholder="例：500"
          />
        </Field>

        <Field label="跨區／跨雲流量" hint="是否常有跨 Region 複製或 DR 流量">
          <select
            className={inputCls}
            disabled={disabled}
            value={value.cross_region_traffic || ''}
            onChange={(e) => set('cross_region_traffic', e.target.value)}
          >
            <option value="">未指定</option>
            <option value="low">低（少跨區）</option>
            <option value="medium">中</option>
            <option value="high">高（頻繁跨區／DR）</option>
          </select>
        </Field>

        <Field label="工作負載型態">
          <select
            className={inputCls}
            disabled={disabled}
            value={value.workload_pattern || ''}
            onChange={(e) => set('workload_pattern', e.target.value)}
          >
            <option value="">未指定</option>
            <option value="always_on">長開（穩定算力）</option>
            <option value="business_hours">營業時段為主</option>
            <option value="bursty">突發尖峰</option>
            <option value="batch">批次／離峰運算</option>
          </select>
        </Field>

        <Field label="月活使用者 (MAU)">
          <input
            type="number"
            min={0}
            className={inputCls}
            disabled={disabled}
            value={value.monthly_active_users}
            onChange={(e) => set('monthly_active_users', e.target.value)}
            placeholder="例：50000"
          />
        </Field>

        <Field label="同時線上／併發">
          <input
            type="number"
            min={0}
            className={inputCls}
            disabled={disabled}
            value={value.concurrent_users}
            onChange={(e) => set('concurrent_users', e.target.value)}
            placeholder="例：800"
          />
        </Field>

        <Field label="月 API／請求數" hint="含前端打後端與內部服務呼叫">
          <input
            type="number"
            min={0}
            className={inputCls}
            disabled={disabled}
            value={value.api_requests_per_month}
            onChange={(e) => set('api_requests_per_month', e.target.value)}
            placeholder="例：30000000"
          />
        </Field>

        <Field label="熱資料儲存 (GB)">
          <input
            type="number"
            min={0}
            step="any"
            className={inputCls}
            disabled={disabled}
            value={value.storage_hot_gb}
            onChange={(e) => set('storage_hot_gb', e.target.value)}
            placeholder="例：500"
          />
        </Field>

        <Field label="備份／歸檔 (GB)">
          <input
            type="number"
            min={0}
            step="any"
            className={inputCls}
            disabled={disabled}
            value={value.storage_backup_gb}
            onChange={(e) => set('storage_backup_gb', e.target.value)}
            placeholder="例：2000"
          />
        </Field>

        <Field label="可用性目標 (SLA)">
          <select
            className={inputCls}
            disabled={disabled}
            value={value.availability_sla || ''}
            onChange={(e) => set('availability_sla', e.target.value)}
          >
            <option value="">未指定</option>
            <option value="99.5">99.5%</option>
            <option value="99.9">99.9%</option>
            <option value="99.95">99.95%</option>
            <option value="99.99">99.99%</option>
          </select>
        </Field>

        <Field label="環境">
          <select
            className={inputCls}
            disabled={disabled}
            value={value.environment || ''}
            onChange={(e) => set('environment', e.target.value)}
          >
            <option value="">未指定</option>
            <option value="production">正式 (production)</option>
            <option value="staging">預釋 (staging)</option>
            <option value="development">開發 (development)</option>
          </select>
        </Field>

        <Field label="主要區域" hint="例：ap-northeast-1, asia-east1, eastus">
          <input
            className={inputCls}
            disabled={disabled}
            value={value.primary_regions}
            onChange={(e) => set('primary_regions', e.target.value)}
            placeholder="例：ap-northeast-1；備援 ap-southeast-1"
          />
        </Field>

        <Field label="年成長率 (%)" hint="用量／流量預估年增">
          <input
            type="number"
            min={0}
            step="any"
            className={inputCls}
            disabled={disabled}
            value={value.growth_pct_year}
            onChange={(e) => set('growth_pct_year', e.target.value)}
            placeholder="例：30"
          />
        </Field>
      </div>
    </section>
  );
}

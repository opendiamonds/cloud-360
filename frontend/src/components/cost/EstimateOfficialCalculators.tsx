/** Official cloud pricing calculator guides — open a short tutorial, then the site. */

import { useState } from 'react';
import { EstimateCalculatorGuideModal } from './EstimateCalculatorGuideModal';
import type { CloudId } from './types';

const OFFICIAL_COST_CALCULATORS: Array<{ id: CloudId; label: string }> = [
  { id: 'aws', label: 'AWS Pricing Calculator' },
  { id: 'gcp', label: 'Google Cloud Pricing Calculator' },
  { id: 'azure', label: 'Azure Pricing Calculator' },
];

type Props = {
  compact?: boolean;
};

export function EstimateOfficialCalculators({ compact }: Props) {
  const [guideCloud, setGuideCloud] = useState<CloudId | null>(null);

  return (
    <div
      data-testid="estimate-official-calculators"
      className={
        compact
          ? 'space-y-2'
          : 'bg-white border border-gray-100 rounded-2xl p-4 shadow-sm space-y-3'
      }
    >
      <div>
        <h2 className="text-sm font-bold text-gray-800">先到官方估價，再回來上傳</h2>
        <p className="mt-1 text-sm text-gray-500 leading-relaxed">
          按各雲按鈕會開啟 2–3 頁教學（含官網畫面與匯出位置）。填完後匯出 CSV／XLSX，再上傳到本頁。
        </p>
      </div>
      <ul className="flex flex-wrap gap-2">
        {OFFICIAL_COST_CALCULATORS.map((c) => (
          <li key={c.id}>
            <button
              type="button"
              data-testid={`official-calc-${c.id}`}
              className="inline-flex items-center gap-1.5 rounded-xl border border-brand-100 bg-brand-50 px-3 py-2 text-sm font-bold text-brand-800 hover:bg-brand-100"
              onClick={() => setGuideCloud(c.id)}
            >
              <span className="uppercase tracking-wide text-xs text-brand-600">
                {c.id}
              </span>
              {c.label}
            </button>
          </li>
        ))}
      </ul>
      {guideCloud && (
        <EstimateCalculatorGuideModal
          cloud={guideCloud}
          onClose={() => setGuideCloud(null)}
        />
      )}
    </div>
  );
}

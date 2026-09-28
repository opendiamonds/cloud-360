/** Official cloud pricing calculator links — guide users to export estimates first. */

type OfficialCalculator = {
  id: 'aws' | 'gcp' | 'azure';
  label: string;
  href: string;
};

const OFFICIAL_COST_CALCULATORS: OfficialCalculator[] = [
  {
    id: 'aws',
    label: 'AWS Pricing Calculator',
    href: 'https://calculator.aws/',
  },
  {
    id: 'gcp',
    label: 'Google Cloud Pricing Calculator',
    href: 'https://cloud.google.com/products/calculator',
  },
  {
    id: 'azure',
    label: 'Azure Pricing Calculator',
    href: 'https://azure.microsoft.com/pricing/calculator/',
  },
];

type Props = {
  compact?: boolean;
};

export function EstimateOfficialCalculators({ compact }: Props) {
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
          請先到各雲官方 Cost／Pricing Calculator 產出含折扣的估價表（CSV／XLSX），匯出後再上傳到本頁。
          Cloud-360 負責解析明細、機械檢查與建議，不會取代官方估價工具。
        </p>
      </div>
      <ul className="flex flex-wrap gap-2">
        {OFFICIAL_COST_CALCULATORS.map((c) => (
          <li key={c.id}>
            <a
              href={c.href}
              target="_blank"
              rel="noopener noreferrer"
              data-testid={`official-calc-${c.id}`}
              className="inline-flex items-center gap-1.5 rounded-xl border border-brand-100 bg-brand-50 px-3 py-2 text-sm font-bold text-brand-800 hover:bg-brand-100"
            >
              <span className="uppercase tracking-wide text-xs text-brand-600">
                {c.id}
              </span>
              {c.label}
              <span className="text-xs font-semibold text-brand-500" aria-hidden>
                ↗
              </span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

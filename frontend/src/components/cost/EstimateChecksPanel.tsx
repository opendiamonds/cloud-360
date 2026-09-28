import type { EstimateChecks } from './types';

type Props = { checks: EstimateChecks; cloudLabel: string };

function flag(ok: boolean, label: string) {
  return (
    <li className={ok ? 'text-emerald-700' : 'text-amber-700'}>
      {ok ? '✓' : '!'} {label}
    </li>
  );
}

export function EstimateChecksPanel({ checks, cloudLabel }: Props) {
  const tr = checks.total_reconciled;
  return (
    <div
      data-testid="estimate-checks-panel"
      className="rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 text-sm"
    >
      <p className="mb-1 text-xs font-semibold text-gray-600">
        機械檢查 · {cloudLabel}
      </p>
      <ul className="space-y-0.5 text-xs">
        {flag(checks.currency_consistent, '幣別一致')}
        {flag(checks.quantity_positive, '數量為正')}
        {flag(
          tr.within_tolerance === true || tr.attempted === false,
          tr.skipped_reason
            ? `總額對帳略過（${tr.skipped_reason}）`
            : tr.within_tolerance
              ? '總額對帳通過'
              : '總額對帳未通過'
        )}
      </ul>
    </div>
  );
}

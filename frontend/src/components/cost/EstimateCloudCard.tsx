import { useState } from 'react';
import type { CloudEstimate } from './types';
import { cloudLabel } from './types';

type Props = { estimate: CloudEstimate };

export function EstimateCloudCard({ estimate }: Props) {
  const [open, setOpen] = useState(true);
  const visibleLines = estimate.lines.filter(
    (ln) => Boolean(ln.item_name?.trim()) && ln.amount != null,
  );
  const linesSum = visibleLines.reduce(
    (acc, ln) => acc + (ln.amount ?? 0),
    0,
  );
  const totalAmount =
    estimate.stated_total != null ? estimate.stated_total : linesSum;
  const totalCurrency =
    estimate.currency ||
    visibleLines.find((ln) => ln.currency)?.currency ||
    '';
  const hasTotal = visibleLines.length > 0 || estimate.stated_total != null;

  return (
    <section
      data-testid="estimate-cloud-card"
      className="rounded-2xl border border-gray-100 bg-white shadow-sm"
    >
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <div>
          <h3 className="text-base font-bold text-gray-900">
            {cloudLabel(estimate.cloud)}
          </h3>
          <p className="text-xs text-gray-500">
            {visibleLines.length} 列
            {hasTotal
              ? ` · 總額 ${totalAmount} ${totalCurrency}`.trimEnd()
              : ''}
          </p>
        </div>
        <span className="text-sm text-gray-400">{open ? '收合' : '展開'}</span>
      </button>
      {open && (
        <div className="border-t border-gray-100 px-4 py-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500">
                <th className="py-1 pr-3">#</th>
                <th className="py-1 pr-3">品項</th>
                <th className="py-1 pr-3">規格</th>
                <th className="py-1 pr-3">數量</th>
                <th className="py-1 pr-3">金額</th>
                <th className="py-1">狀態</th>
              </tr>
            </thead>
            <tbody>
              {visibleLines.map((ln) => (
                <tr key={ln.ordinal} className="border-t border-gray-50">
                  <td className="py-1.5 pr-3 text-gray-500">{ln.ordinal}</td>
                  <td className="py-1.5 pr-3">{ln.item_name || '—'}</td>
                  <td className="py-1.5 pr-3">
                    <div>{ln.spec_description || ln.spec || '—'}</div>
                    {ln.spec_description && ln.spec && ln.spec_description !== ln.spec && (
                      <div className="text-[11px] text-gray-400">SKU {ln.spec}</div>
                    )}
                  </td>
                  <td className="py-1.5 pr-3">{ln.quantity ?? '—'}</td>
                  <td className="py-1.5 pr-3">
                    {ln.amount != null ? `${ln.amount} ${ln.currency || ''}` : '—'}
                  </td>
                  <td className="py-1.5">
                    {ln.parse_status === 'unidentifiable' ? (
                      <span className="text-amber-700">無法辨識</span>
                    ) : (
                      <span className="text-gray-500">已解析</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            {hasTotal && (
              <tfoot>
                <tr className="border-t border-gray-200 font-semibold text-gray-900">
                  <td className="py-2 pr-3" colSpan={4}>
                    總金額
                  </td>
                  <td className="py-2 pr-3">
                    {totalAmount} {totalCurrency}
                  </td>
                  <td className="py-2" />
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}
    </section>
  );
}

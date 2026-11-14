import React from 'react';
import type { CostCardPayload } from '../../brain/brainProtocol';

/**
 * CostAnswerCard — 成本卡片（`BR96.1`；偏離 D-5／D-7 見 functional-spec §八之一）
 *
 * 依已交付的 CostCardPayload 呈現：非 null 的三段文字、無法取價的原因鍵、伺服器給的成本頁連結
 * （href 原樣取 costPageUrl，不自組網址）。不顯示總額與分項（契約沒有）。連結只在使用者點擊時導航（BR96.3）。
 */
export const CostAnswerCard: React.FC<{ card: CostCardPayload }> = ({ card }) => {
  const texts = [card.savingText, card.comparisonText, card.qualityText].filter((t): t is string => t !== null);
  const reasons = card.unavailableReasons ? Object.keys(card.unavailableReasons) : [];
  return (
    <article data-testid="brain-cost-card" className="mt-2 rounded-xl border border-gray-200 bg-white p-3 text-sm">
      <h3 className="font-bold text-gray-900">估價表 #{card.estimateSetId} 的成本分析</h3>
      <div data-testid="brain-cost-card-text" className="mt-1 space-y-1 text-gray-700">
        {texts.length === 0 ? <p>這份估價表目前沒有可說明的建議</p> : texts.map((t, i) => <p key={i}>{t}</p>)}
        {reasons.length > 0 && <p className="text-amber-700">部分項目無法取價：{reasons.join('、')}</p>}
      </div>
      <a data-testid="brain-cost-card-link" href={card.costPageUrl} className="mt-2 inline-block font-semibold text-brand-700 hover:underline">
        到成本頁看估價表 #{card.estimateSetId} 的完整分析
      </a>
    </article>
  );
};

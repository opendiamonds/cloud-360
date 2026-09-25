import { useEffect, useState } from 'react';
import type { CloudId } from './types';
import { cloudLabel } from './types';

type Step = {
  title: string;
  body: string;
  image: string;
  callout: string;
};

const HREF: Record<CloudId, string> = {
  aws: 'https://calculator.aws/',
  gcp: 'https://cloud.google.com/products/calculator',
  azure: 'https://azure.microsoft.com/pricing/calculator/',
};

const STEPS: Record<CloudId, Step[]> = {
  aws: [
    {
      title: '開啟 AWS Pricing Calculator',
      body: '進入官網後按 Create estimate（建立預估）。不必登入也能填公開價。',
      image: '/cost-guides/aws-1-landing.png',
      callout: '右上／主畫面的 Create estimate',
    },
    {
      title: '加入要估價的服務',
      body: '在 Add service 搜尋 EC2、S3、RDS 等，逐項加入並填寫規格與區域。',
      image: '/cost-guides/aws-2-add-service.png',
      callout: '服務清單與 Configure 按鈕',
    },
    {
      title: '匯出 CSV',
      body: '填完後到 My Estimate。右上角 Export（匯出）選 CSV，確認後下載。再回到本頁上傳該檔。',
      image: '/cost-guides/aws-3-estimate.png',
      callout: 'My Estimate 右上角 Export → CSV',
    },
  ],
  gcp: [
    {
      title: '開啟 Google Cloud Pricing Calculator',
      body: '右側是 Cost details。按 Add to estimate 開始加入產品。',
      image: '/cost-guides/gcp-1-landing.png',
      callout: 'Add to estimate',
    },
    {
      title: '加入產品並調整規格',
      body: '搜尋 Compute Engine、Cloud Storage 等，在右側面板調整機器類型、用量與區域。',
      image: '/cost-guides/gcp-1-landing.png',
      callout: '右側 Cost details 會列出已加入項目',
    },
    {
      title: '匯出 CSV／試算表',
      body: '右側預估金額列上方有下載／匯出圖示（文件圖示）。按下去可匯出估價表。若介面改版，請找 Export 或 Download。再回到本頁上傳。',
      image: '/cost-guides/gcp-1-landing.png',
      callout: '右側預估列附近的下載／匯出圖示',
    },
  ],
  azure: [
    {
      title: '開啟 Azure Pricing Calculator',
      body: '上方是 Your estimate，下方是產品目錄。用搜尋或「加入估算」把服務加進估價。',
      image: '/cost-guides/azure-1-landing.png',
      callout: '產品卡上的 Add ／ 加入估算',
    },
    {
      title: '設定各服務規格',
      body: '加入後在估價區展開該服務，選區域、SKU、數量。頂端會顯示預估前期與每月費用。',
      image: '/cost-guides/azure-1-landing.png',
      callout: '頂端 Your estimate 與產品選擇器',
    },
    {
      title: '匯出 Excel（XLSX）',
      body: '估價工具列有 Export（匯出）。選 Excel 下載 .xlsx，再回到本頁上傳。官方匯出通常不含數量欄，本系統會視為 1。',
      image: '/cost-guides/azure-1-landing.png',
      callout: 'Your estimate 工具列的 Export',
    },
  ],
};

type Props = {
  cloud: CloudId;
  onClose: () => void;
};

export function EstimateCalculatorGuideModal({ cloud, onClose }: Props) {
  const [page, setPage] = useState(0);
  const steps = STEPS[cloud];
  const step = steps[page];
  const href = HREF[cloud];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowRight') setPage((p) => Math.min(steps.length - 1, p + 1));
      if (e.key === 'ArrowLeft') setPage((p) => Math.max(0, p - 1));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose, steps.length]);

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/45 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="calc-guide-title"
        data-testid={`estimate-calc-guide-${cloud}`}
        className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl"
      >
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3">
          <h2 id="calc-guide-title" className="text-lg font-bold text-gray-900">
            {cloudLabel(cloud)} 估價教學
          </h2>
          <button type="button" className="rounded-lg px-2 py-1 text-gray-500 hover:bg-gray-100" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
            第 {page + 1}／{steps.length} 頁
          </p>
          <h3 className="text-base font-bold text-gray-900">{step.title}</h3>
          <p className="text-sm leading-relaxed text-gray-600">{step.body}</p>
          <div className="relative overflow-hidden rounded-xl border border-gray-200 bg-gray-50">
            <img
              src={step.image}
              alt={`${cloudLabel(cloud)} ${step.title}`}
              className="block w-full object-cover object-top"
            />
            <div className="pointer-events-none absolute left-3 top-3 rounded-full bg-amber-400 px-3 py-1 text-xs font-bold text-amber-950 shadow">
              {step.callout}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-gray-100 px-5 py-3">
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            data-testid={`official-calc-link-${cloud}`}
            className="text-sm font-bold text-brand-700 hover:underline"
          >
            開啟 {cloudLabel(cloud)} 官方估價頁 ↗
          </a>
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded-xl border border-gray-200 px-3 py-1.5 text-sm font-semibold text-gray-700 disabled:opacity-40"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
            >
              上一頁
            </button>
            {page < steps.length - 1 ? (
              <button
                type="button"
                className="rounded-xl bg-brand-600 px-3 py-1.5 text-sm font-bold text-white"
                onClick={() => setPage((p) => p + 1)}
              >
                下一頁
              </button>
            ) : (
              <button
                type="button"
                className="rounded-xl bg-gray-800 px-3 py-1.5 text-sm font-bold text-white"
                onClick={onClose}
              >
                完成
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

import React from 'react';
import { useAuth } from '../../context/auth-context';

const EXAMPLE_ARCHITECTURE = '幫我畫一張電商網站的雲端架構圖';
const EXAMPLE_COST = '這份架構每個月大概要花多少錢？';

/**
 * EntryEmptyState — 入口頁空狀態（`BR98.1`；偏離 D-3）
 *
 * 只顯示大腦能交辦的兩張卡：A 架構設計（`canArch('view')` 或 `A3 view`）、C 成本（`C1 view`）。點卡片把範例句
 * 填入輸入列並聚焦，**不送出**。其餘六張與「最近的對話」不渲染（`BR98.2`，移到另一個 intent）。
 */
export const EntryEmptyState: React.FC<{ onPick: (text: string) => void }> = ({ onPick }) => {
  const { can, canArch } = useAuth();
  const showArchitecture = canArch('view') || can('A3', 'view');
  const showCost = can('C1', 'view');
  return (
    <div data-testid="brain-empty-state" className="rounded-2xl border border-gray-200 bg-white p-4">
      <p className="text-base font-semibold text-gray-900">你好，想請大腦幫你做什麼？</p>
      {(showArchitecture || showCost) && (
        <ul className="mt-3 grid gap-2 md:grid-cols-2">
          {showArchitecture && (
            <li>
              <button
                type="button"
                data-testid="brain-empty-card-architecture"
                onClick={() => onPick(EXAMPLE_ARCHITECTURE)}
                className="w-full rounded-xl border border-gray-200 p-3 text-left hover:border-brand-300 hover:bg-brand-50"
              >
                <span className="block font-semibold text-gray-900">架構設計與檢視</span>
                <span className="block text-xs text-gray-500">{EXAMPLE_ARCHITECTURE}</span>
              </button>
            </li>
          )}
          {showCost && (
            <li>
              <button
                type="button"
                data-testid="brain-empty-card-cost"
                onClick={() => onPick(EXAMPLE_COST)}
                className="w-full rounded-xl border border-gray-200 p-3 text-left hover:border-brand-300 hover:bg-brand-50"
              >
                <span className="block font-semibold text-gray-900">成本分析</span>
                <span className="block text-xs text-gray-500">{EXAMPLE_COST}</span>
              </button>
            </li>
          )}
        </ul>
      )}
      <p className="mt-3 text-sm text-gray-600">或直接說出你要做什麼</p>
    </div>
  );
};

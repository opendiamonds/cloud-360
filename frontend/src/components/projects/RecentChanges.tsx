import React from 'react';
import type { DiagramChangeOut, SystemOut } from '../../projects/projectsApi';

/**
 * RecentChanges — 總覽籤的「最近變更」（`BR86.2`；functional-design `R-02`）
 *
 * **照實呈現部分來源**：伺服器只回經大腦、已歸屬系統、且請求者自己擁有之圖的變更
 * （變更紀錄以**圖的擁有者**判定可見性；未歸屬系統的圖——`OPEN-H11`——查不到）。
 * 故區塊內標示逐字為「只含經大腦、已歸屬系統、且為你自己擁有之圖的變更」，
 * 空態逐字為「沒有符合條件的變更紀錄」——**不宣稱「這個專案沒有變更」**：成員會把
 * 一個因為「不是他的圖」而空的區塊讀成專案沒有任何變更。
 *
 * 逐系統結果合併、排序取前 5：`created_at` 由新到舊；`null` 排在所有有時間的列之後；
 * 同值依 id 由大到小（決定性 tie-break）。任一系統失敗時顯示「部分變更無法取得」並保留
 * 已取得的列。全部系統的結果到齊（`Map` 每個系統都有鍵）之前顯示載入中。
 */

const RECENT_CHANGES_SCOPE = '只含經大腦、已歸屬系統、且為你自己擁有之圖的變更';
const EMPTY_TEXT = '沒有符合條件的變更紀錄';
const MAX_ROWS = 5;

interface Row {
  change: DiagramChangeOut;
  systemName: string;
}

function compareRows(a: Row, b: Row): number {
  const ta = a.change.created_at ? Date.parse(a.change.created_at) : null;
  const tb = b.change.created_at ? Date.parse(b.change.created_at) : null;
  if (ta !== null && tb !== null && ta !== tb) return tb - ta;
  if (ta === null && tb !== null) return 1;
  if (ta !== null && tb === null) return -1;
  return b.change.id - a.change.id;
}

function formatShortDate(value: string | null | undefined): string {
  if (!value) return '時間不明';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '時間不明';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export const RecentChanges: React.FC<{
  systems: SystemOut[];
  changesBySystem: Map<number, DiagramChangeOut[] | 'failed'>;
}> = ({ systems, changesBySystem }) => {
  const complete = systems.every((s) => changesBySystem.has(s.id));
  const anyFailed = systems.some((s) => changesBySystem.get(s.id) === 'failed');
  const rows: Row[] = [];
  for (const system of systems) {
    const result = changesBySystem.get(system.id);
    if (!result || result === 'failed') continue;
    for (const change of result) rows.push({ change, systemName: system.name });
  }
  rows.sort(compareRows);
  const top = rows.slice(0, MAX_ROWS);

  return (
    <section data-testid="project-recent-changes" aria-labelledby="project-recent-changes-title">
      <h2 id="project-recent-changes-title" className="text-sm font-bold text-gray-900">
        最近變更
      </h2>
      <p data-testid="project-recent-changes-scope" className="mt-1 text-xs text-gray-600">
        {RECENT_CHANGES_SCOPE}
      </p>
      {!complete && <p className="mt-2 text-sm text-gray-500">正在載入變更紀錄…</p>}
      {complete && anyFailed && (
        <p data-testid="project-recent-changes-partial" className="mt-2 text-sm font-bold text-amber-800">
          部分變更無法取得
        </p>
      )}
      {complete && top.length === 0 && !anyFailed && (
        <p data-testid="project-recent-changes-empty" className="mt-2 text-sm text-gray-600">
          {EMPTY_TEXT}
        </p>
      )}
      {top.length > 0 && (
        <ul className="mt-2 space-y-1">
          {top.map(({ change, systemName }) => (
            <li
              key={change.id}
              data-testid={`project-recent-change-${change.id}`}
              className="flex flex-wrap gap-x-3 text-sm text-gray-700"
            >
              <span className="text-gray-500">{formatShortDate(change.created_at)}</span>
              <span>
                {systemName} / 架構圖 #{change.diagram_id}
              </span>
              <span>{change.requirement_summary}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};

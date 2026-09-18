export type OptimizeFinding = {
  code: string;
  pillar: string;
  severity: string;
  title: string;
  message: string;
  recommendation_hint?: string;
  hint?: string;
  lens_risk?: string;
};

const PILLAR_LABELS: Record<string, string> = {
  operational_excellence: 'Operational Excellence',
  security: 'Security',
  reliability: 'Reliability',
  performance_efficiency: 'Performance Efficiency',
  cost_optimization: 'Cost Optimization',
};

export function findingKey(f: OptimizeFinding): string {
  return (f.code || f.title || '').trim();
}

export function riskRank(f: OptimizeFinding): number {
  const lensRisk = (f.lens_risk || '').toUpperCase();
  const severity = (f.severity || '').toLowerCase();
  if (lensRisk === 'HIGH_RISK' || severity === 'high' || severity === 'critical') {
    return 3;
  }
  if (lensRisk === 'MEDIUM_RISK' || severity === 'warn' || severity === 'medium') {
    return 2;
  }
  if (lensRisk === 'LOW_RISK' || severity === 'low') {
    return 1;
  }
  return 0;
}

function riskLabel(rank: number): string {
  if (rank >= 3) return 'HIGH_RISK';
  if (rank >= 2) return 'MEDIUM_RISK';
  return 'LOW_RISK';
}

function countHighRisk(findings: OptimizeFinding[]): number {
  return findings.filter((f) => riskRank(f) >= 3).length;
}

export function normalizeOptimizeFinding(raw: Partial<OptimizeFinding>): OptimizeFinding {
  const hint = (raw.recommendation_hint || raw.hint || '').trim();
  return {
    code: raw.code || '',
    pillar: raw.pillar || '',
    severity: raw.severity || '',
    title: raw.title || raw.code || '',
    message: raw.message || '',
    recommendation_hint: hint,
    hint,
    lens_risk: raw.lens_risk,
  };
}

export function findingAdvice(
  f: OptimizeFinding,
  baselineByCode?: Map<string, OptimizeFinding>,
): string {
  const direct = (f.recommendation_hint || f.hint || '').trim();
  if (direct) return direct;
  const base = baselineByCode?.get(findingKey(f));
  const baseHint = (base?.recommendation_hint || base?.hint || '').trim();
  if (baseHint) return baseHint;
  const msg = (f.message || base?.message || '').trim();
  if (msg && !msg.startsWith('Custom Lens 風險等級：')) return msg;
  const title = f.title || f.code || '此項目';
  const code = f.code || '—';
  const risk = f.lens_risk || riskLabel(riskRank(f));
  if (risk === 'HIGH_RISK') {
    return (
      `請優先消除「${title}」（${code}）之高風險：調整架構圖元件、補上對應 ` +
      `Well-Architected 控制項，並重新評核確認。`
    );
  }
  if (risk === 'MEDIUM_RISK') {
    return (
      `建議針對「${title}」（${code}）補強中風險缺口，參考 Lens 改善計畫並更新圖面後再評核。`
    );
  }
  return `請檢視「${title}」（${code}）並依 Well-Architected 實務補強。`;
}

export function buildOptimizeSuggestionsSummary(
  baselineFindings: OptimizeFinding[],
  newFindings: OptimizeFinding[],
  opts?: {
    baselineScore?: number | null;
    newScore?: number | null;
    baselineHighRisk?: number;
    newHighRisk?: number;
  },
): string {
  const baselineMap = new Map<string, OptimizeFinding>();
  for (const f of baselineFindings) {
    const key = findingKey(f);
    if (key) baselineMap.set(key, f);
  }
  const newMap = new Map<string, OptimizeFinding>();
  for (const f of newFindings) {
    const key = findingKey(f);
    if (key) newMap.set(key, f);
  }

  const resolved: OptimizeFinding[] = [];
  for (const [, baseline] of baselineMap) {
    const baselineRank = riskRank(baseline);
    if (baselineRank < 2) continue;
    const next = newMap.get(findingKey(baseline));
    const nextRank = next ? riskRank(next) : 0;
    if (!next || nextRank < baselineRank) {
      resolved.push(baseline);
    }
  }
  resolved.sort((a, b) => riskRank(b) - riskRank(a));

  const remaining = newFindings
    .filter((f) => riskRank(f) >= 2)
    .sort((a, b) => riskRank(b) - riskRank(a));

  const lines: string[] = ['## 本次優化摘要', ''];

  const summaryParts: string[] = [];
  if (opts?.baselineScore != null && opts?.newScore != null) {
    summaryParts.push(
      `總分 ${Math.round(opts.baselineScore)} → ${Math.round(opts.newScore)}`,
    );
  }
  const beforeHr = opts?.baselineHighRisk ?? countHighRisk(baselineFindings);
  const afterHr = opts?.newHighRisk ?? countHighRisk(newFindings);
  summaryParts.push(`高風險 ${beforeHr} → ${afterHr} 項`);
  if (summaryParts.length) {
    lines.push(`${summaryParts.join('；')}。`, '');
  }

  lines.push('### 已改善項目', '');
  if (resolved.length === 0) {
    lines.push(
      '- 本次未偵測到可對照的 findings 改善（可能圖面已調整但規則代碼未變，或僅有低風險變動）。',
      '',
    );
  } else {
    for (const f of resolved) {
      const pillar = PILLAR_LABELS[f.pillar] || f.pillar;
      const was = f.lens_risk || riskLabel(riskRank(f));
      lines.push(`- **${pillar} · ${f.title}** (\`${f.code}\`，原 ${was})`);
      const advice = findingAdvice(f, baselineMap);
      if (advice) lines.push(`  - 原問題／建議：${advice}`);
      lines.push('  - 狀態：已消除或降級');
    }
    lines.push('');
  }

  lines.push('### 剩餘風險與建議', '');
  if (remaining.length === 0) {
    lines.push(
      '- 目前無中／高風險剩餘項目。儲存後可再執行評核確認細部建議。',
      '',
    );
  } else {
    for (const f of remaining) {
      const label = f.lens_risk || riskLabel(riskRank(f));
      const pillar = PILLAR_LABELS[f.pillar] || f.pillar;
      lines.push(`- **[${label}] ${pillar} · ${f.title}** (\`${f.code}\`)`);
      const msg = (f.message || '').trim();
      if (msg) lines.push(`  - **問題**：${msg}`);
      lines.push(`  - **建議**：${findingAdvice(f, baselineMap)}`);
    }
    lines.push('');
  }

  return lines.join('\n').trim();
}

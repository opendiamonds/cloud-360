import React, { useRef } from 'react';
import { useBrainSession } from '../../brain/brainSession';
import type { ClarifyItem } from '../../brain/brainTranscript';

type ClarifyKind = ClarifyItem['payload']['kind'];

/**
 * 每種反問的提示文字。261116-brain-create-diagram 契約 C6 新增後四種（contract-summary 的 Open Question
 * 「四種新反問的提示文字」於 code-generation 定案）；四者都只顯示 label、點選只送 candidateId。
 */
const PROMPTS: Record<ClarifyKind, string> = {
  intent: '我不確定你指的是哪一件事',
  target: '你指的是哪一個？',
  pick_system: '新的架構圖要建在哪個系統底下？',
  pick_diagram: '要修改哪一張架構圖？',
  resume_draft_or_new: '這個系統已有尚未完成的草稿。要接著畫哪一張草稿，或新建一張？',
  new_or_modify: '要新建一張架構圖，還是修改目前的圖？',
};

/**
 * 修訂 1（審查 draft-ui R-08）：群組的 `aria-label` 依 kind 給，讓螢幕閱讀器念出的群組名稱與選項
 * 對得上——`new_or_modify`／`resume_draft_or_new` 的選項是「動作」，不是「哪一個東西」。
 */
const GROUP_LABELS: Record<ClarifyKind, string> = {
  intent: '請選擇你指的是哪一件事',
  target: '請選擇你指的是哪一個',
  pick_system: '請選擇新架構圖要建在哪個系統',
  pick_diagram: '請選擇要修改的架構圖',
  resume_draft_or_new: '請選擇接著畫哪一張草稿，或新建一張',
  new_or_modify: '請選擇新建或修改',
};

/** 選項是動作（新建／修改）而不是對象的反問：回絕按鈕改為「都不要」。 */
const ACTION_KINDS: ReadonlySet<ClarifyKind> = new Set<ClarifyKind>(['new_or_modify', 'resume_draft_or_new']);

/**
 * ClarifyCandidates — 反問（`BR95.1`–`BR95.5`）
 *
 * 各種 kind 的提示不同；只顯示 label、不顯示信心值；恆有回絕（候選只有一個時亦然）。選定只在使用者按下時
 * 送出一次，之後整組停用；回絕送 candidateId:null、焦點回輸入列、不改脈絡列。stale／resolved／dismissed 淡化停用。
 */
export const ClarifyCandidates: React.FC<{ item: ClarifyItem }> = ({ item }) => {
  const conn = useBrainSession();
  const groupRef = useRef<HTMLDivElement>(null);
  const intent = item.payload.kind === 'intent';
  const active = item.state === 'default' && conn.status === 'ready';
  const prompt = PROMPTS[item.payload.kind] ?? PROMPTS.target;
  const groupLabel = GROUP_LABELS[item.payload.kind] ?? GROUP_LABELS.target;
  const dismissLabel = intent ? '都不是，我再講一次' : ACTION_KINDS.has(item.payload.kind) ? '都不要' : '都不是';

  const dismiss = () => {
    conn.selectCandidate(item.id, null);
    const input = groupRef.current
      ?.closest('[data-brain-session]')
      ?.querySelector<HTMLTextAreaElement>('[data-testid="brain-input"]');
    input?.focus();
  };

  return (
    <div
      ref={groupRef}
      role="group"
      aria-label={groupLabel}
      data-testid="brain-clarify"
      data-kind={item.payload.kind}
      data-state={item.state}
      className={`rounded-xl border border-gray-200 bg-white p-3 text-sm ${item.state === 'default' ? '' : 'opacity-60'}`}
    >
      <p className="font-semibold text-gray-800">{prompt}</p>
      <ul className="mt-2 space-y-1">
        {item.payload.candidates.map((c) => (
          <li key={c.id} className="flex items-center gap-2">
            {intent && <span className="flex-1 break-all">{c.label}</span>}
            <button
              type="button"
              data-testid={`brain-clarify-candidate-${c.id}`}
              disabled={!active}
              aria-busy={item.state === 'picking' && item.pickedId === c.id ? true : undefined}
              onClick={() => conn.selectCandidate(item.id, c.id)}
              className="rounded-lg border border-brand-200 px-2 py-1 font-semibold text-brand-700 hover:bg-brand-50 disabled:opacity-50"
            >
              {intent ? '就是這個' : c.label}
            </button>
          </li>
        ))}
      </ul>
      <button
        type="button"
        data-testid="brain-clarify-restate"
        disabled={!active}
        onClick={dismiss}
        className="mt-2 rounded-lg border border-dashed border-gray-400 px-2 py-1 text-gray-600 disabled:opacity-50"
      >
        {dismissLabel}
      </button>
    </div>
  );
};

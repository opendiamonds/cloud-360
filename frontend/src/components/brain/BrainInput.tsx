import React from 'react';
import { useBrainSession } from '../../brain/brainSession';

/**
 * BrainInput — 輸入列（`frontend-components.md` §五）
 *
 * 空白不送出；ready 之前與等待回覆期間停用（`BR92.2`、`BR93.3`）。超過伺服器輸入上限時以伺服器回傳的
 * error 呈現——前端不另抄上限數字（`EPN-27`）。草稿由呼叫端持有（空狀態卡片會填入範例句）。
 */
export const BrainInput: React.FC<{
  value: string;
  onChange: (value: string) => void;
  inputRef?: React.RefObject<HTMLTextAreaElement | null>;
  placeholder?: string;
}> = ({ value, onChange, inputRef, placeholder }) => {
  const conn = useBrainSession();
  const ready = conn.status === 'ready';
  const canSend = ready && !conn.awaitingReply && value.trim().length > 0;
  const submit = () => {
    if (!canSend) return;
    conn.sendUserMessage(value);
    onChange('');
  };
  return (
    <form
      className="flex items-end gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <textarea
        ref={inputRef}
        data-testid="brain-input"
        aria-label="對大腦說"
        rows={2}
        value={value}
        disabled={!ready}
        placeholder={placeholder ?? '說出你要做什麼…'}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            submit();
          }
        }}
        className="flex-1 resize-none rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none disabled:bg-gray-100"
      />
      <button
        type="submit"
        data-testid="brain-send"
        disabled={!canSend}
        className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
      >
        送出
      </button>
    </form>
  );
};

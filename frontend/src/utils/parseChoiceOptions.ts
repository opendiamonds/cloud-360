/** 解析助理訊息中的 A～E 選項列（A1 追問 UI）。 */

export type ChatChoiceOption = {
  key: string;
  label: string;
  /** 點選後送給後端的文字 */
  sendText: string;
  isOther: boolean;
};

const OPTION_LINE =
  /^([A-Ea-e])[.．、)）:\s]\s*(.+?)\s*$/;

function isOtherLabel(label: string): boolean {
  const t = label.trim();
  return (
    t === '其他' ||
    t.startsWith('其他') ||
    /other/i.test(t)
  );
}

/**
 * 找出訊息中連續的選項列（至少 2 項）。
 * 取最接近結尾的那一組（避免誤判內文例句）。
 */
export function parseChoiceOptions(content: string): ChatChoiceOption[] {
  if (!content.trim()) return [];
  const lines = content.split(/\r?\n/);
  let best: ChatChoiceOption[] = [];
  let current: ChatChoiceOption[] = [];

  const flush = () => {
    if (current.length >= 2) {
      best = current;
    }
    current = [];
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      flush();
      continue;
    }
    const m = line.match(OPTION_LINE);
    if (!m) {
      flush();
      continue;
    }
    const key = m[1].toUpperCase();
    const label = m[2].trim();
    current.push({
      key,
      label,
      sendText: `${key}. ${label}`,
      isOther: isOtherLabel(label),
    });
  }
  flush();

  // 若有選項但沒有「其他」，前端仍顯示；產圖前由 prompt 約束 AI 必須含其他
  return best;
}

/**
 * Lightweight markdown → styled React (no extra dependency).
 * Supports: # headings, lists, blockquotes, bold/italic, paragraphs, hr, inline code.
 */
import type { ReactNode } from 'react';

function inlineFormat(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      parts.push(text.slice(last, m.index));
    }
    const token = m[0];
    if (token.startsWith('**')) {
      parts.push(
        <strong key={key++} className="font-semibold text-gray-900">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('*')) {
      parts.push(
        <em key={key++} className="italic text-gray-800">
          {token.slice(1, -1)}
        </em>
      );
    } else {
      parts.push(
        <code
          key={key++}
          className="rounded bg-gray-100 px-1 py-0.5 text-[0.85em] font-mono text-brand-800"
        >
          {token.slice(1, -1)}
        </code>
      );
    }
    last = m.index + token.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

type Block =
  | { type: 'h'; level: number; text: string }
  | { type: 'p'; text: string }
  | { type: 'quote'; text: string }
  | { type: 'ul'; items: string[] }
  | { type: 'ol'; items: string[] }
  | { type: 'hr' };

function parseBlocks(src: string): Block[] {
  const lines = src.replace(/\r\n/g, '\n').split('\n');
  const blocks: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed) {
      i += 1;
      continue;
    }
    if (/^---+$/.test(trimmed) || /^\*\*\*+$/.test(trimmed)) {
      blocks.push({ type: 'hr' });
      i += 1;
      continue;
    }
    const h = /^(#{1,4})\s+(.+)$/.exec(trimmed);
    if (h) {
      blocks.push({ type: 'h', level: h[1].length, text: h[2].trim() });
      i += 1;
      continue;
    }
    if (trimmed.startsWith('> ')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ''));
        i += 1;
      }
      blocks.push({ type: 'quote', text: quoteLines.join(' ') });
      continue;
    }
    if (/^[-*]\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ''));
        i += 1;
      }
      blocks.push({ type: 'ul', items });
      continue;
    }
    if (/^\d+\.\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ''));
        i += 1;
      }
      blocks.push({ type: 'ol', items });
      continue;
    }
    const para: string[] = [trimmed];
    i += 1;
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^(#{1,4})\s+/.test(lines[i].trim()) &&
      !/^[-*]\s+/.test(lines[i].trim()) &&
      !/^\d+\.\s+/.test(lines[i].trim()) &&
      !lines[i].trim().startsWith('>') &&
      !/^---+$/.test(lines[i].trim())
    ) {
      para.push(lines[i].trim());
      i += 1;
    }
    blocks.push({ type: 'p', text: para.join(' ') });
  }
  return blocks;
}

const H_CLASS: Record<number, string> = {
  1: 'text-lg font-bold text-gray-900 tracking-tight mt-1',
  2: 'text-base font-bold text-gray-900 mt-3 first:mt-0',
  3: 'text-sm font-bold text-gray-800 mt-3',
  4: 'text-sm font-semibold text-gray-700 mt-2',
};

type Props = {
  text: string;
  streaming?: boolean;
  empty?: string;
};

export function SuggestionRichText({ text, streaming, empty }: Props) {
  const trimmed = text.trim();
  if (!trimmed) {
    return (
      <p className="text-sm text-gray-400">{empty || '（尚無建議）'}</p>
    );
  }
  const blocks = parseBlocks(trimmed);
  return (
    <div className="space-y-2 text-sm text-gray-700 leading-relaxed">
      {blocks.map((b, idx) => {
        if (b.type === 'h') {
          const cls = H_CLASS[b.level] || H_CLASS[3];
          if (b.level <= 1) {
            return (
              <h2 key={idx} className={cls}>
                {inlineFormat(b.text)}
              </h2>
            );
          }
          if (b.level === 2) {
            return (
              <h3 key={idx} className={cls}>
                {inlineFormat(b.text)}
              </h3>
            );
          }
          return (
            <h4 key={idx} className={cls}>
              {inlineFormat(b.text)}
            </h4>
          );
        }
        if (b.type === 'quote') {
          return (
            <blockquote
              key={idx}
              className="border-l-4 border-amber-300 bg-amber-50/80 text-amber-950 rounded-r-xl px-3 py-2 text-xs"
            >
              {inlineFormat(b.text)}
            </blockquote>
          );
        }
        if (b.type === 'ul') {
          return (
            <ul key={idx} className="list-disc pl-5 space-y-1.5">
              {b.items.map((item, j) => (
                <li key={j}>{inlineFormat(item)}</li>
              ))}
            </ul>
          );
        }
        if (b.type === 'ol') {
          return (
            <ol key={idx} className="list-decimal pl-5 space-y-1.5">
              {b.items.map((item, j) => (
                <li key={j}>{inlineFormat(item)}</li>
              ))}
            </ol>
          );
        }
        if (b.type === 'hr') {
          return <hr key={idx} className="border-gray-200 my-2" />;
        }
        return (
          <p key={idx} className="text-gray-700">
            {inlineFormat(b.text)}
          </p>
        );
      })}
      {streaming ? (
        <span className="inline-block w-2 h-4 align-middle bg-brand-600 animate-pulse rounded-sm" />
      ) : null}
    </div>
  );
}

/**
 * Strip light Markdown so Review Agent output shows as plain text layout.
 * Keeps line breaks; removes headings, emphasis, quotes, fences, list markers.
 */
export function toPlainSuggestionText(raw: string): string {
  if (!raw) return '';
  let s = raw.replace(/\r\n/g, '\n');
  s = s.replace(/```[\s\S]*?```/g, (block) =>
    block.replace(/^```[^\n]*\n?/, '').replace(/\n?```$/, ''),
  );
  s = s.replace(/^#{1,6}\s+/gm, '');
  s = s.replace(/^>\s?/gm, '');
  s = s.replace(/\*\*([^*]+)\*\*/g, '$1');
  s = s.replace(/__([^_]+)__/g, '$1');
  s = s.replace(/\*([^*\n]+)\*/g, '$1');
  s = s.replace(/`([^`]+)`/g, '$1');
  s = s.replace(/^[-*+]\s+/gm, '• ');
  s = s.replace(/\n{3,}/g, '\n\n');
  return s.trim();
}

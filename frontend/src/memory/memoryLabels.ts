/**
 * memoryLabels.ts — `U15` 記憶頁的顯式映射表（`frontend-components.md §九之一`）
 *
 * **API 值與 test id 片段不得互相代用**（`OPEN-MP15-4`）：
 *   - API 的封閉集合（`memory_types.py` 的 `MEMORY_KINDS`）是 `procedure`；
 *   - 已核可的 test id（`interaction-spec.md` Test ids）是 `memory-zone-procedural`。
 * 以 `procedure` 組 test id 會讓已核可的 id 永遠找不到元素；以 `procedural` 發請求
 * 會被伺服器的封閉集合拒絕（422）。兩者都不改，映射集中在本檔一處。
 */

/** 三區的 API 值，**順序即畫面順序**（`BR32.1`：語意 → 程序 → 情節）。 */
export const MEMORY_ZONE_KINDS = ['semantic', 'procedure', 'episodic'] as const;

export type MemoryKind = (typeof MEMORY_ZONE_KINDS)[number];

interface ZoneLabel {
  /** test id 片段（`memory-zone-{fragment}`）。 */
  testIdFragment: string;
  /** 區標題（`h2`）。 */
  title: string;
  /** 區標題旁的說明（`mockups.md` M6 的括號說明）。 */
  hint: string;
  /** `empty` 態的第二行：說明何時會開始累積（`BR32.3`）。 */
  emptyHint: string;
}

const ZONE_LABELS: Record<MemoryKind, ZoneLabel> = {
  semantic: {
    testIdFragment: 'semantic',
    title: '語意記憶',
    hint: '你的偏好與慣用說法',
    emptyHint: '你在對話中表達偏好或慣用說法之後，大腦會開始記住它們。',
  },
  procedure: {
    testIdFragment: 'procedural',
    title: '程序記憶',
    hint: '你常走的工作流程',
    emptyHint: '大腦觀察到你重複走過的工作流程之後，會開始記住它們。',
  },
  episodic: {
    testIdFragment: 'episodic',
    title: '情節記憶',
    hint: '過往對話',
    emptyHint: '你與大腦對話之後，對話主題會記在這裡，保存 90 天。',
  },
};

export function zoneLabel(kind: MemoryKind): ZoneLabel {
  return ZONE_LABELS[kind];
}

/** `empty` 態的第一行（三區共用，`interaction-spec.md` States 表逐字）。 */
export const EMPTY_TITLE = '大腦還沒記住關於你的事';

/**
 * 可見範圍 → 顯示文字（`BR35.1`）。未知值原樣顯示、不吞掉——伺服器是真相來源，
 * 把未知值顯示成某個已知文字會讓畫面說謊。
 */
export function scopeLabel(scope: string): string {
  if (scope === 'owner') return '僅你可見';
  if (scope === 'platform') return '平台可見';
  return scope;
}

/** 非擁有者的列取代刪除入口的標記（`BR35.2`）。 */
export const OTHERS_MEMORY_MARKER = '平台可見（他人的記憶）';

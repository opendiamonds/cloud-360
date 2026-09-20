import { createRoot } from 'react-dom/client';
import type { Root } from 'react-dom/client';

type SlotName = 'cost-overspend' | 'cost-banner';

const roots = new Map<SlotName, Root>();

export function mountCostSlot(slot: SlotName, node: React.ReactNode): () => void {
  const el = document.querySelector(`[data-slot="${slot}"]`);
  if (!el) return () => undefined;
  const root = createRoot(el);
  roots.set(slot, root);
  root.render(node);
  return () => {
    root.unmount();
    roots.delete(slot);
  };
}

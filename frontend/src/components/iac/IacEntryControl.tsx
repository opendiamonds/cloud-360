type Props = {
  canView: boolean;
  onOpen: () => void;
};

export function IacEntryControl({ canView, onOpen }: Props) {
  return (
    <div className="flex items-center gap-2 shrink-0">
      <button
        type="button"
        data-testid="iac-entry"
        disabled={!canView}
        onClick={onOpen}
        className="text-[11px] font-bold text-white bg-gradient-to-r from-brand-600 to-indigo-600 px-2 py-1 rounded-lg shadow-sm disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
      >
        生成 IaC 代碼
      </button>
      {!canView && (
        <span
          data-testid="iac-entry-hint"
          className="text-[11px] font-medium text-amber-800 whitespace-nowrap"
        >
          缺少 D1 view 權限，無法進入 IaC 工作區。
        </span>
      )}
    </div>
  );
}

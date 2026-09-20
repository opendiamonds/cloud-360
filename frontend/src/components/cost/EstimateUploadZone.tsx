import { useCallback, useRef, useState } from 'react';
import { apiUrl } from '../../config/api';
import { authHeaders, type CloudId } from './types';

type Props = {
  disabled?: boolean;
  canEdit: boolean;
  compact?: boolean;
  onUploaded: (detail: unknown) => void;
  onError: (message: string) => void;
};

const CLOUDS: CloudId[] = ['aws', 'gcp', 'azure'];

export function EstimateUploadZone({
  disabled,
  canEdit,
  compact,
  onUploaded,
  onError,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [overrides, setOverrides] = useState<(CloudId | '')[]>([]);

  const pickFiles = useCallback((list: FileList | null) => {
    if (!list) return;
    const next = Array.from(list).slice(0, 3);
    setFiles(next);
    setOverrides(next.map(() => ''));
  }, []);

  const upload = async () => {
    if (!canEdit || files.length === 0) return;
    setBusy(true);
    onError('');
    try {
      const body = new FormData();
      files.forEach((f) => body.append('files', f));
      if (overrides.some(Boolean)) {
        body.append(
          'cloud_overrides',
          JSON.stringify(overrides.map((o) => (o ? o : null)))
        );
      }
      const res = await fetch(apiUrl('/api/cost/v1/sets'), {
        method: 'POST',
        headers: authHeaders(),
        body,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        onError(typeof data.detail === 'string' ? data.detail : '上傳失敗');
        return;
      }
      setFiles([]);
      setOverrides([]);
      onUploaded(data);
    } catch {
      onError('上傳失敗');
    } finally {
      setBusy(false);
    }
  };

  if (!canEdit) {
    return (
      <p className="text-sm text-gray-500" data-testid="estimate-upload-zone">
        您沒有上傳估價表的權限（需要 C1.edit）。
      </p>
    );
  }

  return (
    <div
      data-testid="estimate-upload-zone"
      className={`rounded-xl border border-dashed border-gray-200 bg-gray-50/60 ${
        compact ? 'p-3' : 'p-4'
      }`}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        if (!disabled && !busy) pickFiles(e.dataTransfer.files);
      }}
    >
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="px-4 py-2 rounded-xl bg-brand-600 text-white text-sm font-bold disabled:opacity-40"
          disabled={disabled || busy}
          onClick={() => inputRef.current?.click()}
        >
          {compact ? '＋ 再上傳一份估價表' : '選擇估價表檔案'}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx"
          multiple
          className="hidden"
          onChange={(e) => pickFiles(e.target.files)}
        />
        <span className="text-xs text-gray-500">最多 3 檔，CSV／XLSX，各 ≤ 5MB</span>
      </div>

      {files.length > 0 && (
        <ul className="mt-4 space-y-2">
          {files.map((f, i) => (
            <li key={`${f.name}-${i}`} className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-medium text-gray-800">{f.name}</span>
              <select
                data-testid="cloud-override-picker"
                className="border border-gray-200 rounded-xl px-2 py-1 text-xs font-semibold text-gray-800"
                value={overrides[i] || ''}
                onChange={(e) => {
                  const v = e.target.value as CloudId | '';
                  setOverrides((prev) => prev.map((x, j) => (j === i ? v : x)));
                }}
              >
                <option value="">自動判定雲別</option>
                {CLOUDS.map((c) => (
                  <option key={c} value={c}>
                    {c.toUpperCase()}
                  </option>
                ))}
              </select>
            </li>
          ))}
          <li>
            <button
              type="button"
              data-testid="estimate-upload-submit"
              className="mt-2 px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm font-bold disabled:opacity-40"
              disabled={busy}
              onClick={upload}
            >
              {busy ? '上傳中…' : '開始上傳'}
            </button>
          </li>
        </ul>
      )}
    </div>
  );
}

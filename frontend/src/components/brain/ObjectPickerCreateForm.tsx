import React, { useEffect, useId, useRef, useState } from 'react';
import { ObjectCreateError, objectCreateAction } from '../../projects/objectCreateAction';
import type { ProjectOut, SystemOut } from '../../projects/projectsApi';

/**
 * ObjectPickerCreateForm — 選單內就地建立專案／系統的單欄表單（`BR14.1`、`BR14.4`；`frontend-components.md`
 * 的 `ObjectCreateForm` 改名，使其落入選單檔案集合的 lint 區塊，`nfr-requirements-corrections.md` `N-03`）
 *
 * - 建立**只**經 `objectCreateAction`（`INV-2`）；本檔不匯入 `createProject`／`createSystem`（lint 擋下）。
 * - **單發鎖用 `useRef`**（`performance-design.md` §三、`OPN-03`）：在呼叫 `objectCreateAction` 之前同步設真、
 *   `finally` 設回。`pending` state 只負責畫面（停用送出鈕）——同一個 JS 任務內連續兩次送出時，第二次仍讀到
 *   舊的 state，只有 ref 擋得住（`nfr-design-corrections.md` `D-02`）。
 * - 失敗就地顯示 `ObjectCreateError` 的文案（名稱重複／無權限／其他；空白名稱不發請求），名稱保留、表單不收；
 *   錯誤文字以 `aria-describedby` 連到名稱欄。
 * - Escape 與取消由父層（`ObjectPicker`）統一處理：收起表單並把焦點還給開啟它的建立入口。
 */
export interface ObjectPickerCreateFormProps {
  kind: 'project' | 'system';
  /** `kind === 'system'` 時的父專案（即所在群組，無「所屬專案」欄位）。 */
  projectId?: number;
  token: string;
  onCreated: (created: ProjectOut | SystemOut) => void;
  onCancel: () => void;
  /**
   * 建立失敗的文案，交給選單內播報區（`F-04`）。送出時**不**先清空（`review-02` `R-09`：清空會讓播報區退回
   * 清單狀態文字，每次重試都多唸一句「已載入 N 個專案」）；相同錯誤的重唸由父層以零寬字元處理（`review-01` `R-06`）。
   */
  onFailure: (message: string) => void;
}

export const ObjectPickerCreateForm: React.FC<ObjectPickerCreateFormProps> = ({
  kind,
  projectId,
  token,
  onCreated,
  onCancel,
  onFailure,
}) => {
  const [name, setName] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submittingRef = useRef(false);
  const mountedRef = useRef(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const errorId = useId();

  useEffect(() => {
    mountedRef.current = true;
    inputRef.current?.focus();
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submittingRef.current) return;
    submittingRef.current = true;
    setPending(true);
    setError(null);
    const request: Promise<ProjectOut | SystemOut> =
      kind === 'project'
        ? objectCreateAction(token, 'project', name)
        : objectCreateAction(token, 'system', name, projectId ?? Number.NaN);
    request
      .then((created) => {
        if (mountedRef.current) onCreated(created);
      })
      .catch((err: unknown) => {
        if (!mountedRef.current) return;
        const message =
          err instanceof ObjectCreateError ? err.message : kind === 'project' ? '建立專案失敗，請稍後再試' : '建立系統失敗，請稍後再試';
        setError(message);
        onFailure(message);
      })
      .finally(() => {
        submittingRef.current = false;
        if (mountedRef.current) setPending(false);
      });
  };

  const label = kind === 'project' ? '新專案名稱' : '新系統名稱';
  return (
    <form
      onSubmit={submit}
      data-testid={`brain-object-create-form-${kind}`}
      className="mt-2 flex flex-col gap-2 rounded border border-gray-200 bg-gray-50 p-2"
    >
      <label className="text-xs font-semibold text-gray-700">
        {label}
        <input
          ref={inputRef}
          type="text"
          data-testid="brain-object-create-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          aria-invalid={error !== null}
          aria-describedby={error !== null ? errorId : undefined}
          className="mt-1 block w-full rounded border border-gray-300 bg-white px-2 py-1 text-sm font-normal text-gray-900"
        />
      </label>
      {error !== null && (
        <p id={errorId} data-testid="brain-object-create-error" className="text-xs text-red-700">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button
          type="submit"
          data-testid="brain-object-create-submit"
          disabled={pending}
          className="rounded bg-brand-600 px-3 py-1 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {pending ? '建立中…' : '建立並切換'}
        </button>
        <button
          type="button"
          data-testid="brain-object-create-cancel"
          onClick={onCancel}
          className="rounded border border-gray-300 bg-white px-3 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-100"
        >
          取消
        </button>
      </div>
    </form>
  );
};

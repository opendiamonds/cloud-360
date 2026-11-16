import React, { useId, useRef, useState } from 'react';
import { useAuth } from '../../context/auth-context';
import { objectCreateAction, ObjectCreateError } from '../../projects/objectCreateAction';
import type { ProjectOut } from '../../projects/projectsApi';

/**
 * SystemCreateAction — 「建立系統」動作（`AC11.1.1`、`AC11.1.3`、`BR82.1`–`BR82.4`）
 *
 * **渲染條件**（`BR82.4`）：`ProjectOut.owner_user_id === 目前使用者 id` **且**
 * `can('K2','edit')`——與伺服器建立系統的擁有者檢查逐字相同，不是另行推導。
 * 本單元前端程式中 `owner_user_id` **只出現在這裡**（`PPN-16`）：它是畫面把關的依據，
 * 不得被拿去推導其他權限結論。伺服器照樣判定（含可見性守門），本條只是呈現。
 *
 * 兩處渲染（總覽計數旁、需求籤空狀態），兩處都經 `objectCreateAction` 寫入。
 * 成功後呼叫 `onCreated()`，由頁面**重讀系統清單**——「系統 N」由清單長度得出，
 * 不在前端本地加一；且**不導航**（pathname 不變，`NFR11.100`）。
 */
export const SystemCreateAction: React.FC<{
  project: ProjectOut;
  describedById?: string;
  onCreated: () => void;
}> = ({ project, describedById, onCreated }) => {
  const { token, user, can } = useAuth();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);
  const baseId = useId();

  const visible = user?.id !== undefined && project.owner_user_id === user.id && can('K2', 'edit');
  if (!visible) return null;

  const inputId = `${baseId}-name`;
  const errorId = `${baseId}-error`;

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!token || inFlight.current) return;
    inFlight.current = true;
    setPending(true);
    setError(null);
    objectCreateAction(token, 'system', name, project.id)
      .then(() => {
        setOpen(false);
        setName('');
        onCreated();
      })
      .catch((err: unknown) => {
        setError(err instanceof ObjectCreateError ? err.message : '建立系統失敗，請稍後再試');
      })
      .finally(() => {
        inFlight.current = false;
        setPending(false);
      });
  };

  if (!open) {
    return (
      <button
        type="button"
        data-testid="system-create-action"
        aria-describedby={describedById}
        onClick={() => setOpen(true)}
        className="rounded-xl border border-brand-200 px-3 py-1 text-sm font-bold text-brand-700 hover:bg-brand-50"
      >
        <span aria-hidden="true">+ </span>建立系統
      </button>
    );
  }

  return (
    <form
      data-testid="system-create-form"
      onSubmit={handleSubmit}
      noValidate
      className="inline-flex flex-wrap items-start gap-2"
    >
      <div>
        <label htmlFor={inputId} className="sr-only">
          系統名稱
        </label>
        <input
          id={inputId}
          data-testid="system-create-name"
          type="text"
          placeholder="系統名稱"
          value={name}
          onChange={(e) => setName(e.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          className="rounded-xl border border-gray-300 px-3 py-1 text-sm"
        />
        {error && (
          <p id={errorId} data-testid="system-create-error" className="mt-1 text-sm font-bold text-red-700">
            {error}
          </p>
        )}
      </div>
      <button
        type="submit"
        data-testid="system-create-submit"
        aria-disabled={pending ? true : undefined}
        className="rounded-xl bg-brand-600 px-3 py-1 text-sm font-bold text-white hover:bg-brand-700"
      >
        {pending ? '建立中…' : '建立系統'}
      </button>
      <button
        type="button"
        data-testid="system-create-cancel"
        onClick={() => {
          setOpen(false);
          setError(null);
        }}
        className="rounded-xl px-3 py-1 text-sm text-gray-600 hover:bg-gray-50"
      >
        取消
      </button>
    </form>
  );
};

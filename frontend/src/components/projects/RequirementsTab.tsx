import React, { useState, type Dispatch, type SetStateAction } from 'react';
import type { ProjectOut, SystemOut } from '../../projects/projectsApi';
import { writeField, type FieldSetView } from '../../projects/requirementsApi';
import { RequirementField } from './RequirementField';
import { SystemCreateAction } from './SystemCreateAction';

/**
 * RequirementsTab — 需求籤（`AC11.1.2`、`AC11.2.1`–`AC11.2.3`；`BR84.1`–`BR84.7`、`BR85.3`、`BR85.6`）
 *
 * **不持有欄位資料，也不持有使用者輸入**：伺服器值只在頁面的 `fieldsBySystem`（`BR85.1`，
 * 總覽與本籤讀同一份）；使用者輸入的 `drafts`、各欄的 `PUT` 錯誤、「已儲存、重新整理失敗」
 * 標記與目前選取的系統也由頁面持有（程式審查 `R-02`）——頁面只渲染目前籤，本籤在切到總覽
 * 或記憶摘要時會卸載；若這些狀態留在本籤，儲存失敗的輸入值與「未儲存」標記在使用者去總覽
 * 看一眼再回來時就消失，正是 `AC11.2.3`／`BR84.5`／`BR85.6` 要防的結果。本籤只保留
 * 「儲存中」「重新整理中」兩個暫態。
 *
 * **儲存**（`BR84.5`）：單一 `[儲存]` 對每個已改動欄位各發一次 `PUT`（彼此獨立）→ 全部回應
 * 到齊後由頁面重讀一次該系統（`onReload`，`BR85.3`：計數只能來自重讀，不在本地加減）。
 * - 重讀成功：成功欄位清除草稿、呈現重讀值；**失敗欄位保留草稿**、標「未儲存」與 `detail`。
 * - 重讀失敗（`BR85.6`）：成功欄位**也不清除草稿**、改標「已儲存、重新整理失敗」；頁面把該系統
 *   標為 `'failed'`（總覽顯示「無法取得」）；本籤以最後一份成功讀到的欄位結構繼續呈現，並提供
 *   `[重新整理]`（只重發該系統的 `GET`）。
 *
 * **清空**：把欄位改為空白並儲存即清空（空值 `PUT`、不帶代寫標示，`BR84.6`）；不提供專屬控件。
 * **無 `K4 edit`**（`BR84.7`）：欄位唯讀、不渲染 `[儲存]`、不建立草稿，並顯示一行說明。
 */

type ReloadOutcome = 'ok' | 'reload-failed';

const draftKey = (systemId: number, groupKey: string, fieldKey: string) =>
  `${systemId}:${groupKey}:${fieldKey}`;

interface WriteResult {
  key: string;
  ok: boolean;
  message: string;
}

/** 需求籤的使用者輸入狀態。由頁面持有，切籤不遺失（程式審查 `R-02`）。 */
export interface RequirementsInputState {
  selected: number | null;
  setSelected: Dispatch<SetStateAction<number | null>>;
  drafts: Map<string, string>;
  setDrafts: Dispatch<SetStateAction<Map<string, string>>>;
  fieldErrors: Map<string, string>;
  setFieldErrors: Dispatch<SetStateAction<Map<string, string>>>;
  savedStale: Set<string>;
  setSavedStale: Dispatch<SetStateAction<Set<string>>>;
}

export const RequirementsTab: React.FC<{
  token: string;
  project: ProjectOut;
  systems: SystemOut[];
  fieldsBySystem: Map<number, FieldSetView | 'failed'>;
  /** 每個系統最後一份成功讀到的欄位（重讀失敗時仍要呈現結構與草稿，`BR85.6`）。 */
  lastGoodFields: Map<number, FieldSetView>;
  canEdit: boolean;
  currentUserId: number | undefined;
  onReload: (systemId: number) => Promise<ReloadOutcome>;
  onSystemCreated: () => void;
  onLiveMessage: (message: string) => void;
  input: RequirementsInputState;
}> = ({
  token,
  project,
  systems,
  fieldsBySystem,
  lastGoodFields,
  canEdit,
  currentUserId,
  onReload,
  onSystemCreated,
  onLiveMessage,
  input,
}) => {
  const {
    selected,
    setSelected,
    drafts,
    setDrafts,
    fieldErrors,
    setFieldErrors,
    savedStale,
    setSavedStale,
  } = input;
  const [saving, setSaving] = useState(false);
  const [reloading, setReloading] = useState(false);

  if (systems.length === 0) {
    return (
      <div data-testid="requirements-empty" className="rounded-xl border border-gray-100 p-6">
        <p className="text-sm text-gray-700">這個專案還沒有系統。</p>
        <p className="mt-1 text-sm text-gray-600">
          需求欄位是按系統填寫的——先建立一個系統。系統由專案擁有者建立。
        </p>
        <div className="mt-3">
          <SystemCreateAction project={project} onCreated={onSystemCreated} />
        </div>
      </div>
    );
  }

  const ordered = [...systems].sort((a, b) => a.id - b.id);
  const systemId = ordered.some((s) => s.id === selected) ? (selected as number) : ordered[0].id;
  const current = fieldsBySystem.get(systemId);
  const view: FieldSetView | undefined =
    current && current !== 'failed' ? current : lastGoodFields.get(systemId);
  const reloadFailed = current === 'failed';
  const groupTitles = new Map((view?.groups ?? []).map((g) => [g.group_key, g.title] as const));

  const handleReload = () => {
    if (reloading) return;
    setReloading(true);
    onReload(systemId)
      .then((outcome) => {
        if (outcome === 'ok') {
          const prefix = `${systemId}:`;
          setDrafts((prev) => {
            const next = new Map(prev);
            for (const key of savedStale) if (key.startsWith(prefix)) next.delete(key);
            return next;
          });
          setSavedStale((prev) => new Set([...prev].filter((k) => !k.startsWith(prefix))));
          onLiveMessage('已重新整理');
        } else {
          onLiveMessage('重新整理失敗');
        }
      })
      .finally(() => setReloading(false));
  };

  const handleSave = () => {
    if (!canEdit || saving || !view) return;
    const changed: { key: string; groupKey: string; fieldKey: string; value: string }[] = [];
    for (const group of view.groups) {
      for (const field of group.fields) {
        const key = draftKey(systemId, field.group_key, field.field_key);
        const draft = drafts.get(key);
        if (draft !== undefined && (draft !== (field.value ?? '') || fieldErrors.has(key))) {
          changed.push({ key, groupKey: field.group_key, fieldKey: field.field_key, value: draft });
        }
      }
    }
    if (changed.length === 0) {
      onLiveMessage('沒有要儲存的變更');
      return;
    }
    setSaving(true);
    Promise.all(
      changed.map(
        (c): Promise<WriteResult> =>
          writeField(token, systemId, c.groupKey, c.fieldKey, c.value)
            .then(() => ({ key: c.key, ok: true, message: '' }))
            .catch((err: unknown) => ({
              key: c.key,
              ok: false,
              message: err instanceof Error ? err.message : '儲存失敗',
            }))
      )
    )
      .then(async (results) => {
        const okKeys = results.filter((r) => r.ok).map((r) => r.key);
        const failed = results.filter((r) => !r.ok);
        setFieldErrors((prev) => {
          const next = new Map(prev);
          for (const key of okKeys) next.delete(key);
          for (const r of failed) next.set(r.key, r.message);
          return next;
        });
        const outcome = await onReload(systemId);
        if (outcome === 'ok') {
          const prefix = `${systemId}:`;
          setDrafts((prev) => {
            const next = new Map(prev);
            for (const key of okKeys) next.delete(key);
            for (const key of savedStale) if (key.startsWith(prefix)) next.delete(key);
            return next;
          });
          setSavedStale(
            (prev) => new Set([...prev].filter((k) => !k.startsWith(prefix) && !okKeys.includes(k)))
          );
          onLiveMessage(failed.length > 0 ? `有 ${failed.length} 個欄位未儲存` : '已儲存');
        } else {
          setSavedStale((prev) => new Set([...prev, ...okKeys]));
          onLiveMessage('已儲存，但重新整理失敗');
        }
      })
      .finally(() => setSaving(false));
  };

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="requirements-system-select" className="block text-sm font-bold text-gray-700">
          對象
        </label>
        <select
          id="requirements-system-select"
          data-testid="requirements-system-select"
          value={systemId}
          onChange={(e) => setSelected(Number(e.target.value))}
          className="mt-1 rounded-xl border border-gray-300 px-3 py-2 text-sm"
        >
          {ordered.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>

      {!canEdit && (
        <p data-testid="requirements-readonly-notice" className="text-sm text-gray-700">
          你可以檢視需求欄位，但沒有編輯權限
        </p>
      )}

      {reloadFailed && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <p>這個系統的需求欄位目前讀不到最新內容。</p>
          <button
            type="button"
            data-testid="requirements-reload"
            aria-disabled={reloading ? true : undefined}
            onClick={handleReload}
            className="mt-2 rounded-xl border border-amber-300 bg-white px-3 py-1 font-bold hover:bg-amber-100"
          >
            {reloading ? '重新整理中…' : '重新整理'}
          </button>
        </div>
      )}

      {!view && !reloadFailed && <p className="text-sm text-gray-500">正在載入需求欄位…</p>}

      {view && (
        <>
          <p data-testid="requirements-input-hint" className="text-sm text-gray-600">
            {view.input_hint}
          </p>
          {view.groups.map((group) => (
            <fieldset
              key={group.group_key}
              data-testid={`requirements-group-${group.group_key}`}
              className="rounded-xl border border-gray-200 p-4"
            >
              <legend className="px-1 text-sm font-bold text-gray-900">
                {group.title}
                <span className="ml-3 font-normal text-gray-600">
                  {group.filled_count}/{group.total_count} 已填
                </span>
              </legend>
              <div className="space-y-3">
                {group.fields.map((field) => {
                  const key = draftKey(systemId, field.group_key, field.field_key);
                  return (
                    <RequirementField
                      key={key}
                      systemId={systemId}
                      field={field}
                      draft={drafts.get(key)}
                      error={fieldErrors.get(key)}
                      stale={savedStale.has(key)}
                      readOnly={!canEdit}
                      requesterTitle={
                        field.updated_on_behalf_of
                          ? (groupTitles.get(field.updated_on_behalf_of) ?? null)
                          : null
                      }
                      currentUserId={currentUserId}
                      onChange={(value) =>
                        setDrafts((prev) => new Map(prev).set(key, value))
                      }
                    />
                  );
                })}
              </div>
            </fieldset>
          ))}
          {canEdit && (
            <button
              type="button"
              data-testid="requirements-save"
              aria-disabled={saving ? true : undefined}
              onClick={handleSave}
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700"
            >
              {saving ? '儲存中…' : '儲存'}
            </button>
          )}
        </>
      )}
    </div>
  );
};

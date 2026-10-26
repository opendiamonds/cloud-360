import React from 'react';
import type { FieldView } from '../../projects/requirementsApi';

/**
 * RequirementField — 需求籤的單一欄位（`AC11.2.1`、`BR84.2`、`BR84.4`、`BR84.5`、`BR84.7`、`BR85.6`）
 *
 * - 標籤在輸入框上方；「未填」「未儲存」「已儲存、重新整理失敗」與更新者都是**文字**，
 *   並經 `aria-describedby` 成為該欄位的可及描述（顏色與鄰近文字對螢幕閱讀器使用者
 *   都不存在）。
 * - 「未填」一律取自回應的 `filled_state`（非 `filled` 即未填，與伺服器 `unfilled_count`
 *   同一判準），不由前端以值是否為空自行判斷。
 * - 無 `K4 edit` 時為 `readOnly`（不用 `disabled`：唯讀仍可聚焦、可被讀出值與描述）。
 * - 更新者三值（`BR84.4`）：`updated_at` 為空 →「從未更新」；`updated_on_behalf_of` 非空 →
 *   「由大腦（<請求組標題> 請求）」，標題由頁面以該 key 對回應 `groups[].group_key` 比對取得，
 *   比對不到時 `requesterTitle` 為 `null` → 降級為「由大腦」；否則依 `updated_by` 為
 *   「由你」或「由其他成員」。
 */

export interface RequirementFieldProps {
  systemId: number;
  field: FieldView;
  /** 未儲存的草稿；`undefined` 表示無草稿、顯示伺服器值。 */
  draft: string | undefined;
  /** `PUT` 失敗的原因（伺服器 `detail`）；有值即標「未儲存」。 */
  error: string | undefined;
  /** `PUT` 成功但其後的重讀失敗（`BR85.6`）。 */
  stale: boolean;
  readOnly: boolean;
  /** `updated_on_behalf_of` 對回應 `groups` 比對到的組標題；`null` ＝比對不到。 */
  requesterTitle: string | null;
  currentUserId: number | undefined;
  onChange: (value: string) => void;
}

function formatDate(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function updaterText(
  field: FieldView,
  requesterTitle: string | null,
  currentUserId: number | undefined
): string {
  if (!field.updated_at) return '從未更新';
  const date = formatDate(field.updated_at);
  const prefix = date ? `最後更新：${date} ` : '最後更新：';
  if (field.updated_on_behalf_of) {
    return requesterTitle ? `${prefix}由大腦（${requesterTitle} 請求）` : `${prefix}由大腦`;
  }
  if (currentUserId !== undefined && field.updated_by === currentUserId) return `${prefix}由你`;
  return `${prefix}由其他成員`;
}

export const RequirementField: React.FC<RequirementFieldProps> = ({
  systemId,
  field,
  draft,
  error,
  stale,
  readOnly,
  requesterTitle,
  currentUserId,
  onChange,
}) => {
  const suffix = `${field.group_key}-${field.field_key}`;
  const inputId = `requirements-input-${systemId}-${suffix}`;
  const unfilled = field.filled_state !== 'filled';
  const ids = {
    unfilled: `${inputId}-unfilled`,
    error: `${inputId}-unsaved`,
    stale: `${inputId}-stale`,
    updater: `${inputId}-updater`,
  };
  const describedBy = [
    unfilled ? ids.unfilled : null,
    error !== undefined ? ids.error : null,
    stale ? ids.stale : null,
    ids.updater,
  ]
    .filter(Boolean)
    .join(' ');
  const value = draft !== undefined ? draft : (field.value ?? '');

  return (
    <div className="space-y-1">
      <label htmlFor={inputId} className="block text-sm font-bold text-gray-700">
        {field.label}
      </label>
      <input
        id={inputId}
        data-testid={`requirements-field-${suffix}`}
        type="text"
        value={value}
        readOnly={readOnly}
        onChange={readOnly ? undefined : (e) => onChange(e.target.value)}
        aria-describedby={describedBy}
        aria-invalid={error !== undefined ? true : undefined}
        className={`w-full rounded-xl border px-3 py-2 text-sm ${
          readOnly ? 'border-gray-200 bg-gray-50 text-gray-700' : 'border-gray-300'
        }`}
      />
      <div className="flex flex-wrap gap-x-3 text-xs">
        {unfilled && (
          <span id={ids.unfilled} data-testid={`requirements-unfilled-${suffix}`} className="font-bold text-amber-800">
            未填
          </span>
        )}
        {error !== undefined && (
          <span id={ids.error} data-testid={`requirements-unsaved-${suffix}`} className="font-bold text-red-700">
            未儲存：{error}
          </span>
        )}
        {stale && (
          <span id={ids.stale} data-testid={`requirements-saved-stale-${suffix}`} className="font-bold text-amber-800">
            已儲存、重新整理失敗
          </span>
        )}
        <span id={ids.updater} data-testid={`requirements-updater-${suffix}`} className="text-gray-500">
          {updaterText(field, requesterTitle, currentUserId)}
        </span>
      </div>
    </div>
  );
};

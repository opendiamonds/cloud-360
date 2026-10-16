/**
 * requirementsApi.ts — `U23` 的需求欄位抓取函式層（消費 `U20` 的既有契約）
 *
 * 純抓取（`BR88.1`），沿用 `projectsApi.ts` 的請求殼與錯誤型別。
 *
 * **清空的唯一方式是空值 `PUT`**（`BR84.6`）：本單元**不呼叫** `DELETE`，且使用者自填時
 * **不帶 `on_behalf_of`**——伺服器把「不帶代寫標示且值只有空白」視為使用者清空；帶了
 * 代寫標示時空值會被拒。
 */

import type { components } from '../types/api';
import { requestJson } from './projectsApi';

export type FieldSetView = components['schemas']['FieldSetView'];
export type FieldGroupView = components['schemas']['FieldGroupView'];
export type FieldView = components['schemas']['FieldView'];

const BASE = '/api/requirements/systems';

/** 端點 5：某系統的全部需求欄位（含未填計數；總覽與需求籤讀同一份回應）。 */
export async function readFields(token: string, systemId: number): Promise<FieldSetView> {
  const body = await requestJson(
    token,
    `${BASE}/${systemId}/fields`,
    { method: 'GET' },
    '讀取需求欄位失敗'
  );
  return body as FieldSetView;
}

/**
 * 端點 6：寫入一個欄位（`PUT`，冪等）。本體只有 `value`——**不帶 `on_behalf_of`**。
 * 失敗時拋 `ApiError`，其訊息為伺服器的字串 `detail`（422 的原因逐字顯示於該欄下方）。
 */
export async function writeField(
  token: string,
  systemId: number,
  groupKey: string,
  fieldKey: string,
  value: string
): Promise<FieldView> {
  const body = await requestJson(
    token,
    `${BASE}/${systemId}/fields/${encodeURIComponent(groupKey)}/${encodeURIComponent(fieldKey)}`,
    { method: 'PUT', body: JSON.stringify({ value }) },
    '儲存失敗'
  );
  return body as FieldView;
}

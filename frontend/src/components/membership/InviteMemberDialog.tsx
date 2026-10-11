import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../context/auth-context';
import { LiveRegion } from '../LiveRegion';
import {
  InviteRejectedError,
  MembershipForbiddenError,
  PROJECT_ROLE_OPTIONS,
  inviteMember,
  type MemberView,
  type ProjectRole,
} from '../../membership/membershipApi';

/**
 * InviteMemberDialog — 邀請成員（`US12.6`／`AC12.6.1`、`US12.5`／`AC12.5.1`）
 *
 * **狀態機**（`functional-spec.md` §六之二）：
 *   `open`（焦點移入第一個欄位）→ `submitting`（按鈕停用）→
 *     `closed`（201，清單多一列）
 *   ｜ `rejected`（422 且 `detail` 為字串，**停在 open 並顯示理由**）
 *   ｜ `closed`（403，由清單頁顯示權限訊息）
 *
 * **`rejected` 不是 `closed` 的一種**：`AC12.5.3` 要求拒絕時清單不新增任何列，
 * 而關閉對話框會讓使用者以為動作完成了。
 *
 * **前端不驗受邀者的全域功能權限**（`BR27.2`／`SEC-U24-3`）：`FR12.6a` 的判定
 * 在伺服器。前端若先猜一次，就會出現「畫面說不行但伺服器說可以」或反之的
 * 兩種不一致，而兩者都比多一次請求糟。故送出鈕**只因欄位未填或送出中**而停用，
 * 絕不因權限而停用。
 */

interface InviteMemberDialogProps {
  projectId: number;
  /** 201 的回應。呼叫端據此**就地新增一列**。 */
  onInvited: (member: MemberView) => void;
  /** 403：呼叫端走終態（關閉、播報、不重試）。 */
  onForbidden: (message: string) => void;
  onClose: () => void;
}

export const InviteMemberDialog: React.FC<InviteMemberDialogProps> = ({
  projectId,
  onInvited,
  onForbidden,
  onClose,
}) => {
  const { token } = useAuth();
  const [userIdText, setUserIdText] = useState('');
  const [role, setRole] = useState<ProjectRole>('member');
  const [submitting, setSubmitting] = useState(false);
  /** 422＋字串 `detail`：伺服器回傳的理由。**畫面不自行組字**。 */
  const [rejectionReason, setRejectionReason] = useState<string | null>(null);
  /** 其他錯誤（含 422 的物件陣列分支）的通用文案。 */
  const [error, setError] = useState<string | null>(null);
  const [liveMsg, setLiveMsg] = useState('');

  const firstFieldRef = useRef<HTMLInputElement>(null);

  // 開啟時焦點移入第一個欄位（`interaction-design-patterns.md` 的既有規定）。
  useEffect(() => {
    firstFieldRef.current?.focus();
  }, []);

  const parsedUserId = Number(userIdText);
  const userIdValid = userIdText.trim() !== '' && Number.isInteger(parsedUserId) && parsedUserId > 0;
  // 只因「必填未填」與「送出中」停用——**不因權限停用**（見檔頭）。
  const submitDisabled = !userIdValid || submitting;

  const handleSubmit = () => {
    if (!token || submitDisabled) return;
    setSubmitting(true);
    setRejectionReason(null);
    setError(null);
    setLiveMsg('正在送出邀請');
    // 兩層形狀：純抓取函式不碰 state，state 更新全在 .then/.catch/.finally。
    inviteMember(token, projectId, parsedUserId, role)
      .then((member) => {
        setLiveMsg(`已邀請 ${member.display_name}`);
        onInvited(member);
      })
      .catch((err: unknown) => {
        if (err instanceof InviteRejectedError) {
          // **停在 open 並顯示伺服器回傳的那個字串**，清單不新增任何列。
          setRejectionReason(err.message);
          setLiveMsg(err.message);
          return;
        }
        if (err instanceof MembershipForbiddenError) {
          onForbidden(err.message);
          return;
        }
        // 一般錯誤路徑（含 422 的 pydantic 物件陣列分支）：顯示通用文案。
        // **不把陣列當文案顯示**——`SEC-U24-4` 禁止，且會渲染出
        // `[object Object]` 或 JSON 片段。抓取層已把它轉成人話。
        const msg = err instanceof Error ? err.message : '邀請成員失敗';
        setError(msg);
        setLiveMsg(msg);
      })
      .finally(() => setSubmitting(false));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div
        data-testid="invite-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="邀請成員"
        className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl"
      >
        <LiveRegion message={liveMsg} />
        <h2 className="mb-4 text-base font-bold text-gray-900">邀請成員</h2>

        <label className="mb-1 block text-xs font-bold text-gray-600" htmlFor="invite-user-id">
          受邀者的使用者 ID
        </label>
        <input
          id="invite-user-id"
          ref={firstFieldRef}
          data-testid="invite-dialog-user-id"
          value={userIdText}
          onChange={(e) => setUserIdText(e.target.value)}
          // 送出中不可改內容（配合 modal 不可關閉），防重複送出的另一面。
          disabled={submitting}
          className="mb-3 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm"
          placeholder="例如 42"
        />

        <label className="mb-1 block text-xs font-bold text-gray-600" htmlFor="invite-role">
          專案角色
        </label>
        {/*
          **只提供封閉列舉內的選項**，不接受自由輸入（`SEC-U24-4` 的前置）。
          列舉外的值會由 Pydantic 回 422（物件陣列型 detail），該路徑仍可處理
          ——但經設計的 UI 下不可達。
        */}
        <select
          id="invite-role"
          data-testid="invite-dialog-role"
          value={role}
          onChange={(e) => setRole(e.target.value as ProjectRole)}
          disabled={submitting}
          className="mb-4 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm"
        >
          {PROJECT_ROLE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {rejectionReason && (
          <p
            data-testid="invite-dialog-rejection-reason"
            className="mb-3 rounded-xl bg-amber-50 px-3 py-2 text-sm font-bold text-amber-900"
          >
            {rejectionReason}
          </p>
        )}
        {error && (
          <p data-testid="invite-dialog-error" className="mb-3 text-sm font-bold text-red-700">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            data-testid="invite-dialog-cancel"
            onClick={onClose}
            // 送出中 modal 不可關閉（`functional-spec.md` §五 W3 第 3 步）。
            disabled={submitting}
            className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            取消
          </button>
          <button
            type="button"
            data-testid="invite-dialog-submit"
            onClick={handleSubmit}
            disabled={submitDisabled}
            className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {submitting ? '送出中…' : '送出邀請'}
          </button>
        </div>
      </div>
    </div>
  );
};

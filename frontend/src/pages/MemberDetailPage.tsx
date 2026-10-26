import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../context/auth-context';
import { LiveRegion } from '../components/LiveRegion';
import { useDialogKeyboard } from '../hooks/useDialogKeyboard';
import { emitFailureSignal } from '../membership/failureSignal';
import {
  LastAdminGuardError,
  MembershipForbiddenError,
  PROJECT_NOT_FOUND_MESSAGE,
  PROJECT_ROLE_OPTIONS,
  changeMemberRole,
  fetchMembers,
  projectRoleLabel,
  removeMember,
  type LastAdminGuardReport,
  type MemberView,
  type ProjectRole,
} from '../membership/membershipApi';

/**
 * MemberDetailPage — 成員詳情（`US12.2`／`AC12.2.1`、`US12.5`／`US12.6`／`AC12.6.2`）
 *
 * **路由**：`/projects/:projectId/members/:userId`。
 *
 * **三個狀態機**（`functional-spec.md` §六之三）：
 *   角色下拉 `idle` → `dirty`（值被改但未存）→ `saving` →
 *     `idle`（200，就地更新）｜ `idle`（409，**下拉還原為原值** ＋ 顯示守門理由）
 *
 * **409 必須還原**：留著使用者選的新值會讓畫面顯示一個伺服器拒絕過的狀態，
 * 而下一次重新載入它會跳回舊值——那是一個無聲的不一致（`BR24.2`）。
 *
 * **`canManage` 兩段式**：與 `MembersListPage` 同一個判定（見該檔的長註解）。
 * 本頁重算而非由 props 傳入，因為它可被直接以 URL 進入（無清單頁的 state）。
 */

export const MemberDetailPage: React.FC = () => {
  const { projectId: projectIdParam, userId: userIdParam } = useParams<{
    projectId: string;
    userId: string;
  }>();
  const projectId = Number(projectIdParam);
  const userId = Number(userIdParam);
  /**
   * 網址的 `projectId` 不是有限數字（如 `/projects/abc/members/1`）——合併前必修
   * 第 23 項補修（審查 `R-11`）。與 `MembersListPage` 同形：這種網址不可能對應任何
   * 專案，故與 404 同一個結論，顯示固定句「查不到這個專案」、不發請求、不停在
   * 「載入中…」，並經 `emitFailureSignal()` 發一筆訊號（`SEC-U24-6`）。
   *
   * 只看 `projectId`：`userId` 非數字時抓取照常進行，`find` 找不到該列，畫面顯示
   * 「找不到這位成員」——那條路徑本來就不會卡住。
   *
   * **以導出值呈現而非 effect 內 setState**（`react-hooks/set-state-in-effect` 為
   * error 級）：畫面狀態在渲染時由 `invalidProjectId` 直接決定。
   */
  const invalidProjectId = !Number.isFinite(projectId);
  const { token, user, can } = useAuth();
  const navigate = useNavigate();

  const [members, setMembers] = useState<MemberView[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // **寫入／權限錯誤與抓取錯誤必須分開**（審查 `R-01`／Major）。`error` 閘住
  // 主內容是對的：抓取失敗時沒有資料可顯示。但寫入失敗時資料還在，若共用同一
  // 個 state，整個成員區塊（含角色下拉與移出鈕）會被卸載，而唯一能清掉它的
  // handler 就掛在那些剛被卸載的控件上——形成只能靠離開頁面脫離的死狀態。
  const [actionError, setActionError] = useState<string | null>(null);
  // 同 `MembersListPage`：載入訊息以初始值帶入，不在 effect body 內 setState
  // （`react-hooks/set-state-in-effect` 為 error 級）。
  const [liveMsg, setLiveMsg] = useState('正在載入成員資料');
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [guardReport, setGuardReport] = useState<LastAdminGuardReport | null>(null);
  /** 下拉的當前值。409 時還原為 `member.role`（伺服器的真相）。 */
  const [selectedRole, setSelectedRole] = useState<ProjectRole | ''>('');

  const cancelButtonRef = useRef<HTMLButtonElement>(null);
  /** 移出確認框本身與它的觸發按鈕（合併前必修第 23 項 (c)）。 */
  const confirmDialogRef = useRef<HTMLDivElement>(null);
  const removeButtonRef = useRef<HTMLButtonElement>(null);

  /**
   * 關閉移出確認框，並把焦點**還給「移出專案」鈕**。取消、Escape、409 守門、
   * 403、其他錯誤五條「留在本頁」的關閉路徑都經這裡；204 成功會導回清單頁，
   * 觸發按鈕隨頁面卸載，故不經這裡。
   */
  const closeConfirm = useCallback(() => {
    setConfirmOpen(false);
    removeButtonRef.current?.focus();
  }, []);

  // 鍵盤上真的是 modal：Escape 關閉、Tab／Shift+Tab 不離開對話框。
  // 移出中 Escape 不關閉，與停用的「取消」鈕一致。
  useDialogKeyboard(confirmDialogRef, {
    open: confirmOpen,
    onEscape: closeConfirm,
    escapeDisabled: removing,
  });

  // 兩層抓取形狀（`TS-U24-4`）。本頁沿用 `list_members`——**沒有單一成員的
  // 端點**（實測六個路由，見 `functional-spec.md` §四），故以清單回應取該列。
  // 這同時讓 `canManage` 的第一段（`BR22.3`）有資料可依。
  useEffect(() => {
    if (!token || invalidProjectId) return;
    let cancelled = false;
    fetchMembers(token, projectId)
      .then((data) => {
        if (cancelled) return;
        setMembers(data);
        setError(null);
        const target = data.find((m) => m.user_id === userId);
        setSelectedRole(target ? (target.role as ProjectRole) : '');
        setLiveMsg(target ? `已載入 ${target.display_name} 的資料` : '找不到這位成員');
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : '讀取成員失敗';
        setError(msg);
        setLiveMsg(msg);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, projectId, userId, invalidProjectId]);

  // 非數字 `projectId` 的失敗訊號（`SEC-U24-6`）。種類與端點沿用 404 走的同一組
  // （`membershipApi.ts` 的 `fetchMembers`）；訊號只含兩個封閉欄位，網址裡的原字串
  // **不會**進 console（`SEC-U24-1`）。effect 內只做這個副作用，不 setState。
  useEffect(() => {
    if (!invalidProjectId) return;
    emitFailureSignal({ kind: 'members-fetch-failed', endpoint: 'GET /projects/:id/members' });
  }, [invalidProjectId]);

  const showLoading = isLoading && !invalidProjectId;
  const shownError = invalidProjectId ? PROJECT_NOT_FOUND_MESSAGE : error;
  const shownLiveMsg = invalidProjectId ? PROJECT_NOT_FOUND_MESSAGE : liveMsg;

  const member = members.find((m) => m.user_id === userId);

  // `canManage` 兩段式（`security-design.md` §一之三）：per-project 角色結論
  // **AND** 全域 `can("K3","edit")`。缺第二段時四個控件全不渲染——否則每次寫入
  // 永久 403，而「403 就重抓」是無上界的死循環。不增加請求數。
  const ownRole = members.find((m) => m.user_id === user?.id)?.role;
  // **只比 `project_admin`**（審查 `R-04`）：`project_owner` 不是成員角色。
  // `ck_project_members_role`（`schema_rbac.sql:598`）把 `project_members.role`
  // 限定為 `('project_admin','member')`，而 `membership_types.py` 的
  // `ProjectRole` docstring 逐字說 owner 是 `projects.owner_user_id` 承載的
  // **專案屬性**。留著那個 disjunct 是授權述詞裡的死分支：若該 CHECK 日後被
  // 放寬，它會讓一個伺服器不接受的角色值取得管理者控件——正是兩段式要消除的
  // 永久 403。無功能損失：建立者在同一交易被寫成 `project_admin`。
  const isProjectManager = ownRole === 'project_admin';
  const canManage = isProjectManager && can('K3', 'edit');

  const dirty = !!member && selectedRole !== '' && selectedRole !== member.role;

  /** 403 → **終態**：播報並停止該操作，**不重抓**（重抓改不了 role）。 */
  const handleForbidden = useCallback((message: string) => {
    setActionError(message);
    setLiveMsg(message);
    setConfirmOpen(false);
  }, []);

  const handleSaveRole = () => {
    // 逐條直接縮小型別，不倚賴 `dirty` 的 aliased narrowing：後者讓
    // `selectedRole === ''` 被 tsc 判為不可能的比較（TS2367），而把那個檢查
    // 拿掉又會讓 `''` 流進只接受 `ProjectRole` 的抓取函式。
    if (!token || !member) return;
    if (selectedRole === '' || selectedRole === member.role) return;
    const previousRole = member.role;
    setSaving(true);
    setGuardReport(null);
    setActionError(null);
    setLiveMsg('正在變更角色');
    changeMemberRole(token, projectId, userId, selectedRole)
      .then((updated) => {
        // 就地更新，不整份重抓（`BR24.1`／`UIP-3`）。不可就地修改既有物件
        // （`react-hooks/immutability` 為 error 級）。
        setMembers((prev) => prev.map((m) => (m.user_id === updated.user_id ? updated : m)));
        setSelectedRole(updated.role as ProjectRole);
        setLiveMsg(`已將角色變更為 ${projectRoleLabel(updated.role)}`);
      })
      .catch((err: unknown) => {
        if (err instanceof LastAdminGuardError) {
          // **還原為原值** ＋ 列出守門帶回的**每一個**專案（`BR24.2`）。
          setSelectedRole(previousRole as ProjectRole);
          setGuardReport(err.report);
          setLiveMsg(err.message);
          return;
        }
        if (err instanceof MembershipForbiddenError) {
          handleForbidden(err.message);
          return;
        }
        const msg = err instanceof Error ? err.message : '變更角色失敗';
        setActionError(msg);
        setLiveMsg(msg);
      })
      .finally(() => setSaving(false));
  };

  const handleRemove = () => {
    if (!token || !member) return;
    setRemoving(true);
    setGuardReport(null);
    setActionError(null);
    setLiveMsg('正在移出成員');
    removeMember(token, projectId, userId)
      .then(() => {
        setConfirmOpen(false);
        setLiveMsg(`已將 ${member.display_name} 移出專案`);
        // 導回清單頁。清單頁會重新抓取，故該成員不在清單上（`BR25.2`
        // 的「少一列」在清單頁自己的回應中成立）。
        navigate(`/projects/${projectId}/members`);
      })
      .catch((err: unknown) => {
        if (err instanceof LastAdminGuardError) {
          // 留在詳情頁，顯示守門理由與專案清單（`functional-spec.md` §五 W5 第 5 步）。
          closeConfirm();
          setGuardReport(err.report);
          setLiveMsg(err.message);
          return;
        }
        if (err instanceof MembershipForbiddenError) {
          closeConfirm();
          handleForbidden(err.message);
          return;
        }
        const msg = err instanceof Error ? err.message : '移出成員失敗';
        closeConfirm();
        setActionError(msg);
        setLiveMsg(msg);
      })
      .finally(() => setRemoving(false));
  };

  // 二次確認對話框開啟時，焦點預設在**取消**（`BR25.1`：破壞性動作）。
  useEffect(() => {
    if (confirmOpen) cancelButtonRef.current?.focus();
  }, [confirmOpen]);

  return (
    <div className="p-6" data-testid="member-detail-page">
      <LiveRegion message={shownLiveMsg} />

      <button
        type="button"
        onClick={() => navigate(`/projects/${projectId}/members`)}
        className="mb-4 text-sm font-bold text-brand-700 hover:underline"
      >
        ← 回成員清單
      </button>

      {showLoading && <p className="text-sm text-gray-500">載入中…</p>}

      {!showLoading && shownError && (
        <p data-testid="member-detail-error" className="text-sm font-bold text-red-700">
          {shownError}
        </p>
      )}

      {/* 寫入／權限錯誤：**不閘住任何內容**，控件保持可用以便重試（審查 `R-01`）。 */}
      {actionError && (
        <p data-testid="member-detail-action-error" className="mb-3 text-sm font-bold text-red-700">
          {actionError}
        </p>
      )}

      {!isLoading && !error && !member && (
        <p className="text-sm font-bold text-gray-600">找不到這位成員。</p>
      )}

      {!isLoading && !error && member && (
        <>
          <h1 className="mb-1 text-xl font-bold text-gray-900">{member.display_name}</h1>
          <p className="mb-5 text-sm text-gray-500">
            加入時間：{new Date(member.joined_at).toLocaleString()}
          </p>

          <section className="mb-6">
            <h2 className="mb-2 text-sm font-bold text-gray-700">專案角色</h2>
            {canManage ? (
              <div className="flex flex-wrap items-center gap-2">
                <select
                  data-testid="member-detail-role-select"
                  aria-label="專案角色"
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value as ProjectRole)}
                  disabled={saving}
                  className="rounded-xl border border-gray-300 px-3 py-2 text-sm"
                >
                  {PROJECT_ROLE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  data-testid="member-detail-save"
                  onClick={handleSaveRole}
                  // 與當前值相同時停用存檔鈕（`frontend-components.md` §六）。
                  disabled={!dirty || saving}
                  className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700 disabled:opacity-50"
                >
                  {saving ? '儲存中…' : '儲存'}
                </button>
              </div>
            ) : (
              <p className="text-sm text-gray-700">{projectRoleLabel(member.role)}</p>
            )}
          </section>

          {/*
            守門回報（`BR24.2`）。409 的回應本體**就是** `LastAdminGuardReport`，
            含每個專案的 `project_id` 與 `name`——必須列出**每一個**，
            而 `guard-report-projects` 內的列數應等於回應中 `projects` 的長度。
            守門本身的三條 AC（`AC12.3.1`–`.3`）屬 `US12.3`、不在本單元承載的
            五則內，故這段呈現在上游既沒有 AC 也沒有斷言目標——這份資訊若沒被
            渲染或渲染錯了，不會有任何東西變紅。testid 由審查 `R-14` 補上。
          */}
          {guardReport && (
            <section
              data-testid="guard-report"
              className="mb-6 rounded-xl bg-amber-50 px-4 py-3"
            >
              <p className="mb-2 text-sm font-bold text-amber-900">
                此操作會讓下列專案失去最後一位專案管理者，因此未執行：
              </p>
              <ul data-testid="guard-report-projects" className="space-y-1">
                {guardReport.projects.map((p) => (
                  <li key={p.project_id} className="text-sm text-amber-900">
                    {p.name}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/*
            變更紀錄（`AC12.2.2`）。

            **`OPEN-MP24-7`：取得變更紀錄的端點不存在。** 資料**存在**
            （`reselection_events`——`U19/[FD3]=A` 把人工變更與自動改選兩類都
            收進同一張表，正是為了讓 `AC12.2.2` 以一個查詢讀出），但沒有任何
            端點或 facade 方法可以取它：六個路由與 17 個 facade 方法逐一核對過，
            最接近的 `list_members` 只回四欄的 `MemberView`、
            `list_my_pending_reselections` 過濾 `cause == 'auto_reselection'`
            且 `acknowledged_at IS NULL` 且限本人——皆不符。
            `models.py` 的 `Index("ix_reselection_events_project_id", ...)` 註解
            逐字寫「成員詳情頁的變更紀錄讀取端」——**索引為該讀取而建，
            讀取端卻不存在**。

            故此處渲染一個**明確的佔位**：不捏造資料（假的稽核紀錄比沒有紀錄
            更危險），也不留空白區塊（空白會被下一個人讀成漏寫而非判斷）。
            真正的修法是 `U19` 的契約擴充，而 `U19` 的 `code-generation` 已完成
            且在游標之前——本 intent 內**無自然承接站**，已於核可關卡揭露。
            `AC12.2.2` 因此在 `traceability.json` 標為 **Deferred**，不洗成 OK。
          */}
          <section>
            <h2 className="mb-2 text-sm font-bold text-gray-700">變更紀錄</h2>
            <p
              data-testid="member-change-log-unavailable"
              className="rounded-xl bg-gray-50 px-4 py-3 text-sm text-gray-600"
            >
              尚無法取得變更紀錄（後端尚未提供查詢端點，OPEN-MP24-7）。
            </p>
          </section>

          {canManage && (
            <section className="mt-6 border-t border-gray-200 pt-4">
              <button
                type="button"
                ref={removeButtonRef}
                data-testid="member-detail-remove"
                onClick={() => setConfirmOpen(true)}
                className="rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-bold text-red-700 hover:bg-red-50"
              >
                移出專案
              </button>
            </section>
          )}

          {/* 二次確認（`BR25.1`）：破壞性動作，焦點預設在取消。 */}
          {confirmOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
              <div
                ref={confirmDialogRef}
                data-testid="remove-confirm-dialog"
                role="dialog"
                aria-modal="true"
                aria-label="確認移出成員"
                className="w-full max-w-sm rounded-2xl bg-white p-5 shadow-xl"
              >
                <p className="mb-4 text-sm text-gray-800">
                  確定要將 {member.display_name} 移出這個專案？
                </p>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    ref={cancelButtonRef}
                    data-testid="remove-confirm-cancel"
                    onClick={closeConfirm}
                    disabled={removing}
                    className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    取消
                  </button>
                  <button
                    type="button"
                    data-testid="remove-confirm-accept"
                    onClick={handleRemove}
                    disabled={removing}
                    className="rounded-xl bg-red-600 px-4 py-2 text-sm font-bold text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    {removing ? '移出中…' : '確認移出'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../context/auth-context';
import { LiveRegion } from '../components/LiveRegion';
import { InviteMemberDialog } from '../components/membership/InviteMemberDialog';
import {
  PROJECT_NOT_FOUND_MESSAGE,
  fetchMembers,
  projectRoleLabel,
  type MemberView,
} from '../membership/membershipApi';
import { emitFailureSignal } from '../membership/failureSignal';

/**
 * MembersListPage — 專案成員清單（`US12.1`／`AC12.1.1`、`US12.6`／`AC12.6.1`）
 *
 * **路由**：`/projects/:projectId/members`，由 `App.tsx` 以既有 `CapabilityRoute`
 * （`K3`／`view`）包覆做**能力層**把關。per-project 那一層不能用它表達。
 *
 * **清單上沒有任何可直接改角色的控件**（`AC12.2.3`／`BR22.2`）：角色只在
 * 成員詳情頁變更（`[M2]`=C）。
 */

/**
 * 前端分頁的每頁列數（`UIP-1`；合併前必修第 9 項，使用者裁決「前端分頁顯示全部」）。
 *
 * **為什麼是前端分頁**：`list_members`（`membership_router.py`）沒有任何
 * `page`／`limit`／`offset` 參數，一次回傳全部成員。本頁以那一份回應在前端切頁，
 * 所以**每一位成員都可經由翻頁到達**——本頁是管理成員的唯一入口，任何「超過
 * 上限就不渲染」的閘都會讓超出的成員無法被管理（先前的 100 列整表隱藏閘即是此
 * 缺陷，已移除）。切頁不發任何請求，故 `UIP-4`（首次可互動前恰 1 次請求）不變。
 *
 * **仍開放**：`OPEN-MP24-6`（伺服器分頁）屬 `U19` 的契約擴充，不在本單元範圍。
 * 前端分頁只解決「可到達」，不解決「伺服器一次回傳全部」的傳輸量。
 */
const MEMBERS_PER_PAGE = 50;

export const MembersListPage: React.FC = () => {
  const { projectId: projectIdParam } = useParams<{ projectId: string }>();
  const projectId = Number(projectIdParam);
  /**
   * 網址的 `projectId` 不是有限數字（如 `/projects/abc/members`）——合併前必修第 23 項。
   *
   * 這種網址**不可能**對應任何專案，故與 404 同一個結論：顯示固定句「查不到這個專案」
   * （`PROJECT_NOT_FOUND_MESSAGE`），不發請求、不停在「載入中…」。先前抓取 effect 直接
   * return、`isLoading` 永遠為 true，畫面卡在載入中且沒有任何訊號，違反 `SEC-U24-6`。
   *
   * **以導出值呈現而非 effect 內 setState**（`react-hooks/set-state-in-effect` 為 error 級，
   * `team.md` 的兩層抓取形狀）：畫面狀態在渲染時由 `invalidProjectId` 直接決定；effect
   * 只做「發出失敗訊號」這一個副作用。
   */
  const invalidProjectId = !Number.isFinite(projectId);
  const { token, user, can } = useAuth();

  const [members, setMembers] = useState<MemberView[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // 與詳情頁同一處更正（審查 `R-01`／Major）：邀請收到 403 時清單資料還在，
  // 共用 `error` 會讓整張成員表被卸載，而邀請鈕仍在畫面上——使用者看到的是
  // 「可以邀請但看不到任何成員」，且沒有任何互動能把表格帶回來。
  const [actionError, setActionError] = useState<string | null>(null);
  // 載入訊息以**初始值**帶入，不在 effect body 內 setState——
  // `react-hooks/set-state-in-effect` 是 error 級（違反即 CI 紅燈），而
  // 「進入載入態要播報」（`BR27.1`）在初始值這個形式下同樣成立。
  const [liveMsg, setLiveMsg] = useState('正在載入成員清單');
  const [inviteOpen, setInviteOpen] = useState(false);
  /** 邀請對話框的觸發按鈕；對話框關閉時焦點回到這裡（合併前必修第 23 項）。 */
  const inviteButtonRef = useRef<HTMLButtonElement>(null);
  // 使用者**要求**的頁次（1 起算）。實際顯示的頁次是下方的導出值 `currentPage`。
  const [requestedPage, setRequestedPage] = useState(1);

  // 兩層抓取形狀（`TS-U24-4`）：純抓取函式不碰 state；state 更新在呼叫端的
  // .then/.catch/.finally；`useEffect` 內以 `cancelled` flag 防卸載後 setState。
  useEffect(() => {
    if (!token || invalidProjectId) return;
    let cancelled = false;
    fetchMembers(token, projectId)
      .then((data) => {
        if (cancelled) return;
        setMembers(data);
        setError(null);
        setLiveMsg(`已載入 ${data.length} 位成員`);
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
  }, [token, projectId, invalidProjectId]);

  // 非數字 `projectId` 的失敗訊號（`SEC-U24-6`）。種類與端點沿用 404 走的同一組
  // （`membershipApi.ts` 的 `fetchMembers`）：兩者是同一個使用者可見結論。
  // 訊號只含兩個封閉欄位，網址裡的原字串**不會**進 console（`SEC-U24-1`）。
  useEffect(() => {
    if (!invalidProjectId) return;
    emitFailureSignal({ kind: 'members-fetch-failed', endpoint: 'GET /projects/:id/members' });
  }, [invalidProjectId]);

  const showLoading = isLoading && !invalidProjectId;
  const shownError = invalidProjectId ? PROJECT_NOT_FOUND_MESSAGE : error;
  const shownLiveMsg = invalidProjectId ? PROJECT_NOT_FOUND_MESSAGE : liveMsg;

  /**
   * `canManage` —— **兩段式**（`security-design.md` §一之三／審查 `R-01`）：
   *
   *   （自己那一列的 `role` ∈ {`project_owner`, `project_admin`}）**AND** `can("K3","edit")`
   *
   * **第一段**依 `BR22.3`：以**自身 `user_id`** 在 `list_members` 的回應中找到
   * 自己那一列、讀它的 `role`。讀的是**伺服器給的結論**，不是拿全域角色自己算，
   * 故不違反不變量 `I-5`。找不到自身即為 false——`list_members` 對非成員回 404
   * （合併前必修第 14 項起，與「專案不存在」同一個回應；畫面顯示固定句「查不到這個專案」），
   * 故 200 的結果裡理應有自己；若沒有，那是一個不該默默當成管理者的異常。
   *
   * **第二段為什麼必要**：「per-project 為 `project_admin` 但缺全域 `K3.edit`」
   * 是**已證實可達**的狀態，兩條獨立路徑都到得了——
   *   ① 被直接邀為 `project_admin`：受邀者把關只要求 view
   *      （`membership_service.py:72` 的 `REQUIRED_INVITEE_ACTION = "view"`），
   *      而 `FinOps_Analyst`／`Security_Reviewer`／`Platform_Owner` 的 `K3`
   *      實測為 `True, False, False`（view 有、edit 無）；
   *   ② 被自動改選升為 `project_admin`：`reselect_for_project` 直接
   *      `set_member_role(..., role=ROLE_PROJECT_ADMIN)`，**無任何 `K3.edit` 過濾**。
   * 只看 per-project `role` 的話，四個控件全部渲染 → 每次寫入永久 403 →
   * 而「403 就重抓清單（權限可能剛被改）」重抓回來的 `role` 不變、`canManage`
   * 仍為 true → **無上界的死循環，且對使用者沒有任何說明**。
   *
   * 這**不增加請求數**：`can()` 讀的是已載入的 `user.permissions`，
   * 故 `UIP-4`（首次可互動前恰 1 次請求）不變。
   *
   * 被排除的替代方案是「渲染控件但以 403 為終態」——它讓使用者看得到四個
   * 永遠失敗的控件，而本頁是管理成員的唯一入口。
   */
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

  /**
   * 關閉邀請對話框，並把焦點**還給「邀請成員」鈕**（合併前必修第 23 項 (c)）。
   * 取消、Escape、201、403 四條關閉路徑都經這裡——否則對話框卸載後焦點落到
   * `<body>`，鍵盤使用者要從頁首重新 Tab。按鈕在對話框開啟期間始終在 DOM 中
   * （`canManage` 為 true 才能開啟對話框），故可同步聚焦。
   */
  const closeInvite = useCallback(() => {
    setInviteOpen(false);
    inviteButtonRef.current?.focus();
  }, []);

  /**
   * 邀請成功 → **就地新增一列**，不整份重抓（`BR23.2`／`[F4]`=A／`UIP-3`）。
   * 不可就地修改既有陣列（`react-hooks/immutability` 為 error 級）。
   */
  const handleInvited = useCallback(
    (member: MemberView) => {
      setMembers((prev) => [...prev, member]);
      // 新列附加在清單尾端；跳到它所在的頁，使「就地新增一列」在任何頁數下都
      // 看得見（否則在第 1 頁邀請時，新列落在使用者看不到的最後一頁）。
      setRequestedPage(Math.ceil((members.length + 1) / MEMBERS_PER_PAGE));
      closeInvite();
      setLiveMsg(`已邀請 ${member.display_name}`);
    },
    [members.length, closeInvite],
  );

  /**
   * 邀請流程收到 403 → **終態**：關閉對話框、播報、**停止該操作**。
   *
   * **不重抓清單**（`security-design.md` §一之三 的同步更正）：重抓無法改變
   * per-project `role`，`canManage` 仍為 true，重抓就是上面那個死循環。
   */
  const handleForbidden = useCallback(
    (message: string) => {
      closeInvite();
      setActionError(message);
      setLiveMsg(message);
    },
    [closeInvite],
  );

  /**
   * 分頁的導出值。**頁次夾在 [1, totalPages] 之間是導出而非 effect 內 setState**：
   * 本地更新（就地新增／未來的就地移除）讓當前頁變空時，`currentPage` 自動退回
   * 最後一個非空頁——不需要 effect（`react-hooks/set-state-in-effect` 為 error 級），
   * 也不會有「先渲染一次空頁再跳回」的閃爍。總頁數至少為 1，使零成員時仍顯示
   * 「第 1／1 頁、共 0 位」而非 0／0。
   */
  const totalPages = Math.max(1, Math.ceil(members.length / MEMBERS_PER_PAGE));
  const currentPage = Math.min(Math.max(1, requestedPage), totalPages);
  const pageStart = (currentPage - 1) * MEMBERS_PER_PAGE;
  const visibleMembers = members.slice(pageStart, pageStart + MEMBERS_PER_PAGE);

  return (
    <div className="p-6" data-testid="members-list-page">
      {/* 載入／錯誤一律經 live region 播報；**不得**沿用 AdminPage.tsx:104 的
          4 秒 toast（實測無 role／aria-live）——`BR27.1`。 */}
      <LiveRegion message={shownLiveMsg} />

      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-bold text-gray-900">專案成員</h1>
        {canManage && (
          <button
            type="button"
            ref={inviteButtonRef}
            data-testid="member-list-invite-button"
            onClick={() => setInviteOpen(true)}
            className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700"
          >
            邀請成員
          </button>
        )}
      </div>

      {showLoading && <p className="text-sm text-gray-500">載入中…</p>}

      {!showLoading && shownError && (
        <p data-testid="member-list-error" className="text-sm font-bold text-red-700">
          {shownError}
        </p>
      )}

      {/* 邀請／權限錯誤：**不閘住清單**，表格保持在畫面上（審查 `R-01`）。 */}
      {actionError && (
        <p data-testid="member-list-action-error" className="mb-3 text-sm font-bold text-red-700">
          {actionError}
        </p>
      )}

      {/*
        清單**不設任何整表隱藏閘**：不論成員數多少，表格都渲染，只是一次顯示
        一頁（`MEMBERS_PER_PAGE` 列）。切頁發生在「資料→視圖」的轉換點
        （`visibleMembers`），列的 `map` 內部不做任何數量判斷（`UIP-1`）。
      */}
      {!showLoading && !shownError && (
        <table
          data-testid="member-list-table"
          className="w-full border-collapse text-left text-sm"
        >
          <thead>
            <tr className="border-b border-gray-200 text-xs uppercase tracking-wider text-gray-500">
              <th className="px-3 py-2">顯示名稱</th>
              <th className="px-3 py-2">專案角色</th>
              <th className="px-3 py-2">加入時間</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {visibleMembers.map((m) => (
              <tr
                key={m.user_id}
                data-testid={`member-list-row-${m.user_id}`}
                className="border-b border-gray-100"
              >
                <td className="px-3 py-2 font-bold text-gray-900">{m.display_name}</td>
                {/*
                  只顯示角色文字。**本列不含任何 select 或角色編輯入口**
                  （`AC12.2.3`／`BR22.2`）——清單頁的角色 select 命中數應為 0。
                */}
                <td className="px-3 py-2 text-gray-700">{projectRoleLabel(m.role)}</td>
                <td className="px-3 py-2 text-gray-500">
                  {new Date(m.joined_at).toLocaleString()}
                </td>
                <td className="px-3 py-2">
                  {canManage && (
                    <Link
                      data-testid="member-list-row-detail-link"
                      to={`/projects/${projectId}/members/${m.user_id}`}
                      className="font-bold text-brand-700 hover:underline"
                    >
                      詳情
                    </Link>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/*
        分頁控制放在表格**之外**（與既有 `PaginationControl.tsx` 的結構前提相同）。
        刻意不重用該元件：它是深色主題、`aria-label` 寫死為「使用者清單分頁」、
        且語意是伺服器分頁（`pageSize` 取自回應）——三者都與本頁不合，改它會
        波及 `AdminPage`。邊界一律**呈現但停用**（不隱藏），單頁時也看得到總數。
      */}
      {!showLoading && !shownError && (
        <nav
          aria-label="成員清單分頁"
          data-testid="member-list-pagination"
          className="mt-3 flex flex-wrap items-center gap-2 text-sm"
        >
          <button
            type="button"
            data-testid="member-list-prev-page"
            disabled={currentPage <= 1}
            onClick={() => setRequestedPage(currentPage - 1)}
            className="rounded-lg border border-gray-300 px-3 py-1 font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            上一頁
          </button>
          <span data-testid="member-list-page-info" className="text-gray-700">
            第 {currentPage}／{totalPages} 頁、共 {members.length} 位
          </span>
          <button
            type="button"
            data-testid="member-list-next-page"
            disabled={currentPage >= totalPages}
            onClick={() => setRequestedPage(currentPage + 1)}
            className="rounded-lg border border-gray-300 px-3 py-1 font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            下一頁
          </button>
        </nav>
      )}

      {inviteOpen && canManage && (
        <InviteMemberDialog
          projectId={projectId}
          onInvited={handleInvited}
          onForbidden={handleForbidden}
          onClose={closeInvite}
        />
      )}
    </div>
  );
};

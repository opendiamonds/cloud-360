import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../context/auth-context';
import { LiveRegion } from '../components/LiveRegion';
import { InviteMemberDialog } from '../components/membership/InviteMemberDialog';
import { fetchMembers, projectRoleLabel, type MemberView } from '../membership/membershipApi';

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
 * 清單渲染上限（`UIP-1`）。
 *
 * **100 不是憑空的數字**：它取自 `backend/services/user_router.py:146-147` 的
 * `MAX_PAGE_SIZE = 100`——本 repo 唯一的清單端點先例（`/api/auth/list`）。
 * 取同一個值使本頁的上限與既有先例一致，而不是另立一個沒有來源的門檻。
 *
 * **已知的功能邊界（`OPEN-MP24-6`，不埋起來）**：`list_members`
 * （`membership_router.py:164-178`）實測**沒有任何 `page`／`limit`／`offset`
 * 參數**，一次回傳全部成員，故本上限是**純前端的防護**——伺服器仍會傳 101 筆，
 * 前端只是不渲染。由此產生一個真實的邊界：**成員數超過 100 的專案，無法用
 * 本頁管理成員**，而本頁是管理成員的唯一入口。受影響的已核可 AC 為
 * `AC12.2.1`／`AC12.6.1`／`AC12.6.2`（皆斷言「清單內容改變」）。
 * 真正的修法是伺服器分頁，屬 `U19` 的契約擴充，而 `U19` 已完成且在游標之前
 * ——本 intent 內**無自然承接站**，已於核可關卡向使用者揭露。
 */
const MAX_RENDERED_MEMBERS = 100;

export const MembersListPage: React.FC = () => {
  const { projectId: projectIdParam } = useParams<{ projectId: string }>();
  const projectId = Number(projectIdParam);
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

  // 兩層抓取形狀（`TS-U24-4`）：純抓取函式不碰 state；state 更新在呼叫端的
  // .then/.catch/.finally；`useEffect` 內以 `cancelled` flag 防卸載後 setState。
  useEffect(() => {
    if (!token || !Number.isFinite(projectId)) return;
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
  }, [token, projectId]);

  /**
   * `canManage` —— **兩段式**（`security-design.md` §一之三／審查 `R-01`）：
   *
   *   （自己那一列的 `role` ∈ {`project_owner`, `project_admin`}）**AND** `can("K3","edit")`
   *
   * **第一段**依 `BR22.3`：以**自身 `user_id`** 在 `list_members` 的回應中找到
   * 自己那一列、讀它的 `role`。讀的是**伺服器給的結論**，不是拿全域角色自己算，
   * 故不違反不變量 `I-5`。找不到自身即為 false——`list_members` 對非成員回 403，
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
   * 邀請成功 → **就地新增一列**，不整份重抓（`BR23.2`／`[F4]`=A／`UIP-3`）。
   * 不可就地修改既有陣列（`react-hooks/immutability` 為 error 級）。
   */
  const handleInvited = useCallback((member: MemberView) => {
    setMembers((prev) => [...prev, member]);
    setInviteOpen(false);
    setLiveMsg(`已邀請 ${member.display_name}`);
  }, []);

  /**
   * 邀請流程收到 403 → **終態**：關閉對話框、播報、**停止該操作**。
   *
   * **不重抓清單**（`security-design.md` §一之三 的同步更正）：重抓無法改變
   * per-project `role`，`canManage` 仍為 true，重抓就是上面那個死循環。
   */
  const handleForbidden = useCallback((message: string) => {
    setInviteOpen(false);
    setActionError(message);
    setLiveMsg(message);
  }, []);

  const tooMany = members.length > MAX_RENDERED_MEMBERS;

  return (
    <div className="p-6" data-testid="members-list-page">
      {/* 載入／錯誤一律經 live region 播報；**不得**沿用 AdminPage.tsx:104 的
          4 秒 toast（實測無 role／aria-live）——`BR27.1`。 */}
      <LiveRegion message={liveMsg} />

      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-bold text-gray-900">專案成員</h1>
        {canManage && (
          <button
            type="button"
            data-testid="member-list-invite-button"
            onClick={() => setInviteOpen(true)}
            className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700"
          >
            邀請成員
          </button>
        )}
      </div>

      {isLoading && <p className="text-sm text-gray-500">載入中…</p>}

      {!isLoading && error && (
        <p data-testid="member-list-error" className="text-sm font-bold text-red-700">
          {error}
        </p>
      )}

      {/* 邀請／權限錯誤：**不閘住清單**，表格保持在畫面上（審查 `R-01`）。 */}
      {actionError && (
        <p data-testid="member-list-action-error" className="mb-3 text-sm font-bold text-red-700">
          {actionError}
        </p>
      )}

      {/*
        100 列渲染閘。閘門放在**「資料→視圖」的轉換點**，不是在列的 `map`
        內部——這讓「不渲染半套清單」成為結構保證而非逐列判斷的巧合（`UIP-1`）。
      */}
      {!isLoading && !error && tooMany && (
        <p data-testid="member-list-too-many" className="text-sm font-bold text-amber-800">
          成員過多，請聯絡管理者（本頁最多顯示 {MAX_RENDERED_MEMBERS} 位，
          目前共 {members.length} 位）
        </p>
      )}

      {!isLoading && !error && !tooMany && (
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
            {members.map((m) => (
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

      {inviteOpen && canManage && (
        <InviteMemberDialog
          projectId={projectId}
          onInvited={handleInvited}
          onForbidden={handleForbidden}
          onClose={() => setInviteOpen(false)}
        />
      )}
    </div>
  );
};

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/auth-context';
import { apiUrl } from '../config/api';
import { LastActivityCell } from '../components/LastActivityCell';
import { PaginationControl } from '../components/PaginationControl';
import type { components } from '../types/api';

// 型別**採用產生的型別**，不手寫。手寫的本地 interface 與後端回應形狀之間沒有
// 任何編譯期連結 —— 後端改欄位時 tsc 完全無感，那正是 openapi.json → api.d.ts
// 這條鏈要消除的落差。
type DbUser = components['schemas']['UserSchema'];
type UserListPage = components['schemas']['UserListPage'];

const AVAILABLE_ROLES = [
  'Project_Admin',
  'Platform_Admin',
  'Project_Architect',
  'SRE',
  'FinOps_Analyst',
  'Platform_Engineer',
  'Security_Reviewer',
  'Ops_Lead',
  'Project_Editor',
  'Developer',
  'Platform_Owner',
];

export const AdminPage: React.FC = () => {
  const { token, user: currentUser, can } = useAuth();
  const canEdit = can('J3a', 'edit');
  const [users, setUsers] = useState<DbUser[]>([]);
  const [page, setPage] = useState(1);
  // pageSize／total 直接取自最近一次回應，不寫死前端常數（後端是真相來源）。
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  // 切頁忙碌**與初次載入的 isLoading 分離**：isLoading 會把整個容器（含表格）
  // 替換為單一訊息，而分頁控制必須在切頁期間留在畫面上、焦點不被卸載。
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // 只有「最後發出」的抓取回應能寫入 state。既有的 cancelled flag 只防「元件卸載
  // 後 setState」，不防「兩個重疊請求以非發出順序返回」—— 後者會讓剛被刪除的列
  // 短暫重新出現。
  const requestSeq = useRef(0);

  // 純抓取，完全不碰 state。react-hooks/set-state-in-effect 會做過程間分析：
  // 只要 effect 同步呼叫的函式內部有 setState 就會被擋，因此把 state 更新一律
  // 留在呼叫端的 .then／.catch／.finally callback 內（規則允許的形式）。
  const fetchUserPage = useCallback(
    async (targetPage: number): Promise<UserListPage> => {
      const res = await fetch(apiUrl(`/api/auth/list?page=${targetPage}`), {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || '取得使用者列表失敗');
      }
      return data as UserListPage;
    },
    [token]
  );

  // 單一的 envelope 落地點：三個抓取路徑都經過它，避免「新增的路徑忘記處理某個
  // 欄位」——切頁是第三個呼叫點，分散處理必漏。
  //
  // **正規化不是多餘的**：產生的型別把兩個新欄位宣告為必填，但那是**編譯期**
  // 保證；`res.json()` 是執行期的 `any`，型別只是斷言。若後端映像比前端舊
  // （手動只重建一邊，`DEPLOY.md` 2.2.4 已警告），欄位會是 undefined，而
  // LastActivityCell 的 props 不含 undefined。收斂在這裡，三個路徑一體適用。
  const applyPage = useCallback((data: UserListPage) => {
    setUsers(
      (data.items ?? []).map((u) => ({
        ...u,
        last_activity_at: u.last_activity_at ?? null,
        is_overdue: u.is_overdue ?? false,
      }))
    );
    setTotal(data.total ?? 0);
    setPage(data.page ?? 1);
    setPageSize(data.page_size ?? 20);
  }, []);

  useEffect(() => {
    if (!token) return;
    // 初次載入時 isLoading 已是 true，不需要再設一次。
    let cancelled = false;
    const seq = (requestSeq.current += 1);
    fetchUserPage(1)
      .then((data) => { if (!cancelled && seq === requestSeq.current) applyPage(data); })
      .catch((err) => {
        if (!cancelled && seq === requestSeq.current) {
          setError(err instanceof Error ? err.message : '連線失敗');
        }
      })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [token, fetchUserPage, applyPage]);

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // 路徑 2：使用者主動切頁。容器內顯示載入訊息，但**分頁控制留在畫面上**。
  const handlePageChange = (targetPage: number) => {
    setIsBusy(true);
    setError(null);
    const seq = (requestSeq.current += 1);
    fetchUserPage(targetPage)
      .then((data) => { if (seq === requestSeq.current) applyPage(data); })
      // 失敗分支同樣要檢查序號：否則一個較舊的失敗回應會在較新的成功之後蓋上
      // 錯誤畫面，把已經正確載入的頁面換掉。
      .catch((err) => {
        if (seq === requestSeq.current) setError(err instanceof Error ? err.message : '連線失敗');
      })
      .finally(() => setIsBusy(false));
  };

  // 路徑 3：刪除後的背景重新同步。**不設任何載入旗標** —— 就地移除已經給了立即
  // 回饋，再閃一次載入畫面是純粹的退步；失敗時保留就地移除後的畫面，不回滾。
  const resyncCurrentPageInBackground = (targetPage: number) => {
    const seq = (requestSeq.current += 1);
    fetchUserPage(targetPage)
      .then((data) => { if (seq === requestSeq.current) applyPage(data); })
      .catch(() => {
        if (seq === requestSeq.current) showToast('清單同步失敗，畫面可能不是最新的', 'error');
      });
  };

  const handleRoleChange = async (userId: number, newRole: string) => {
    try {
      const res = await fetch(apiUrl(`/api/auth/${userId}/role`), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ role: newRole }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '更新角色失敗');
      // 套用整個回應（與 handleToggleActive 一致），不只 role —— 回應裡的
      // last_activity_at／is_overdue 是後端以當下時間重算的，只套 role 會讓該列
      // 停留在載入當時的逾期判定。
      const updated: DbUser = {
        ...(data as DbUser),
        last_activity_at: (data as DbUser).last_activity_at ?? null,
        is_overdue: (data as DbUser).is_overdue ?? false,
      };
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)));
      showToast(`✔ 已更新 '${data.username}' 角色為 '${newRole}'`, 'success');
    } catch (err) {
      // **不重抓** —— 操作失敗不得把使用者從目前頁次彈回第 1 頁。
      showToast(err instanceof Error ? err.message : '更新失敗', 'error');
    }
  };

  const handleToggleActive = async (u: DbUser) => {
    try {
      const res = await fetch(apiUrl(`/api/auth/${u.id}/active`), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_active: !u.is_active }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '更新狀態失敗');
      // 就地更新該列，**不整份重抓** —— 啟停用不改變總筆數與排序。
      const updated: DbUser = {
        ...(data as DbUser),
        last_activity_at: (data as DbUser).last_activity_at ?? null,
        is_overdue: (data as DbUser).is_overdue ?? false,
      };
      setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)));
      showToast(
        data.is_active ? `✔ 已啟用 ${data.username}` : `✔ 已停用 ${data.username}`,
        'success'
      );
    } catch (err) {
      showToast(err instanceof Error ? err.message : '更新失敗', 'error');
    }
  };

  const handleDelete = async (u: DbUser) => {
    if (!confirm(`確定刪除使用者 ${u.username}？此操作無法復原。`)) return;
    try {
      const res = await fetch(apiUrl(`/api/auth/${u.id}`), {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '刪除失敗');
      // 就地移除 + 總筆數本地遞減（立即回饋、頁次不變），接著背景重抓當前頁把
      // offset 位移補回來 —— 不重抓的話，下一頁會靜默略過一個帳號。
      setUsers((prev) => prev.filter((x) => x.id !== u.id));
      setTotal((prev) => Math.max(0, prev - 1));
      showToast(`✔ 已刪除 ${data.deleted_username}`, 'success');
      resyncCurrentPageInBackground(page);
    } catch (err) {
      showToast(err instanceof Error ? err.message : '刪除失敗', 'error');
    }
  };

  const renderLastActivity = (u: DbUser) => (
    <LastActivityCell lastActivityAt={u.last_activity_at} isOverdue={u.is_overdue} />
  );

  const renderRoleControl = (u: DbUser) =>
    u.authorization_status === 'approved' ? (
      <select
        value={u.role || ''}
        disabled={!canEdit}
        onChange={(e) => handleRoleChange(u.id, e.target.value)}
        className="bg-slate-900 border border-slate-800 text-slate-300 text-xs font-bold rounded-xl px-3 py-2 disabled:opacity-50"
      >
        {AVAILABLE_ROLES.map((roleOpt) => (
          <option key={roleOpt} value={roleOpt}>
            {roleOpt}
          </option>
        ))}
      </select>
    ) : (
      <Link to="/admin/authorization-requests" className="text-xs text-blue-400 hover:underline">
        至授權申請處理
      </Link>
    );

  const renderActiveControl = (u: DbUser) => (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span
          className={`w-2.5 h-2.5 rounded-full ${u.is_active ? 'bg-emerald-500' : 'bg-slate-500'}`}
        />
        <span className="text-xs text-slate-300">{u.is_active ? '啟用中' : '已停用'}</span>
      </div>
      {canEdit && u.username !== currentUser?.username && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => handleToggleActive(u)}
            className="min-w-11 min-h-11 md:min-w-0 md:min-h-0 px-2 py-1 text-[10px] font-bold rounded-lg bg-slate-800 border border-slate-700"
          >
            {u.is_active ? '停用' : '啟用'}
          </button>
          {!u.is_active && (
            <button
              type="button"
              onClick={() => handleDelete(u)}
              className="min-w-11 min-h-11 md:min-w-0 md:min-h-0 px-2 py-1 text-[10px] font-bold rounded-lg bg-red-900/40 border border-red-800 text-red-300"
            >
              刪除
            </button>
          )}
        </div>
      )}
    </div>
  );

  const renderAuthStatus = (u: DbUser) =>
    u.authorization_status === 'pending' ? (
      <span className="text-amber-300">
        待授權{u.requested_role ? `（${u.requested_role}）` : ''}
      </span>
    ) : (
      <span className="text-emerald-300">已核准</span>
    );

  return (
    <div className="relative min-h-full bg-slate-950 p-6 md:p-10 pb-16 text-white font-sans w-full">
      {toast && (
        <div
          className={`fixed top-6 left-1/2 -translate-x-1/2 z-50 px-6 py-4 rounded-2xl shadow-xl backdrop-blur-xl border flex items-center gap-3 ${
            toast.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
              : 'bg-red-500/10 border-red-500/20 text-red-300'
          }`}
        >
          <span className="font-semibold text-sm tracking-wide">{toast.message}</span>
        </div>
      )}

      <div className="flex flex-col gap-2 mb-8">
        <h1 className="text-3xl font-black tracking-tight text-white">使用者角色指派</h1>
        <p className="text-slate-400 text-sm font-medium">
          指定使用者角色、啟停用與刪除（J3a）。待授權申請請至{' '}
          <Link to="/admin/authorization-requests" className="text-blue-400 hover:underline">
            授權申請
          </Link>
          。
        </p>
      </div>

      <div className="bg-white/5 backdrop-blur-2xl border border-white/10 rounded-[2rem] shadow-2xl overflow-hidden">
        {isLoading ? (
          <div className="p-20 text-center text-slate-400 text-sm">載入中…</div>
        ) : error ? (
          <div className="p-20 text-center text-red-300 text-sm">{error}</div>
        ) : (
          <>
            {/* 容器內容區：切頁時只有這一塊變成載入訊息，分頁控制在它之外。 */}
            {isBusy ? (
              <div className="p-20 text-center text-slate-400 text-sm">載入中…</div>
            ) : users.length === 0 ? (
              // 第六態：空清單。分頁後才可達（清單不分頁時只要有帳號就有內容）。
              <div className="p-20 text-center text-slate-400 text-sm">
                這一頁沒有資料。{' '}
                <button
                  type="button"
                  onClick={() => handlePageChange(1)}
                  className="text-blue-400 hover:underline"
                >
                  回到第 1 頁
                </button>
              </div>
            ) : (
              <>
                {/* 桌面：表格。斷點以下隱藏，改用下方卡片。 */}
                <div className="hidden md:block overflow-auto max-h-[min(70vh,720px)]">
                  <table className="w-full text-left border-collapse">
                    <thead className="sticky top-0 z-20">
                      <tr className="bg-slate-950 border-b border-white/10 text-xs font-bold text-slate-400 tracking-wider uppercase">
                        <th className="px-6 py-5">使用者</th>
                        <th className="px-6 py-5">授權狀態</th>
                        <th className="px-6 py-5">角色</th>
                        <th className="px-6 py-5">最後活動時間</th>
                        <th className="px-6 py-5">操作</th>
                        <th className="px-6 py-5">啟用</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 font-medium">
                      {users.map((u) => (
                        <tr key={u.id} className="hover:bg-white/[0.02]">
                          <td className="px-6 py-4">
                            <span className="text-sm font-bold text-white">
                              {u.username}
                              {u.username === currentUser?.username && (
                                <span className="ml-2 px-2 py-0.5 bg-blue-500/20 text-blue-300 text-[10px] font-extrabold rounded-full">
                                  目前登入
                                </span>
                              )}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-xs">{renderAuthStatus(u)}</td>
                          <td className="px-6 py-4">
                            <span className="text-xs text-slate-300">{u.role || '—'}</span>
                          </td>
                          <td className="px-6 py-4">{renderLastActivity(u)}</td>
                          <td className="px-6 py-4">{renderRoleControl(u)}</td>
                          <td className="px-6 py-4">{renderActiveControl(u)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* 小螢幕（<768px）：一帳號一卡片，欄位以「標籤: 值」逐行呈現。
                    標示語彙與桌面完全相同 —— 同一個元件、同一組樣式。 */}
                <ul className="md:hidden divide-y divide-white/5">
                  {users.map((u) => (
                    <li key={u.id} className="p-5 flex flex-col gap-3">
                      <span className="text-sm font-bold text-white">
                        {u.username}
                        {u.username === currentUser?.username && (
                          <span className="ml-2 px-2 py-0.5 bg-blue-500/20 text-blue-300 text-[10px] font-extrabold rounded-full">
                            目前登入
                          </span>
                        )}
                      </span>
                      <div className="flex items-baseline gap-2">
                        <span className="text-[10px] uppercase tracking-wider text-slate-500 w-24 shrink-0">
                          授權狀態
                        </span>
                        <span className="text-xs">{renderAuthStatus(u)}</span>
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-[10px] uppercase tracking-wider text-slate-500 w-24 shrink-0">
                          角色
                        </span>
                        <span className="text-xs text-slate-300">{u.role || '—'}</span>
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-[10px] uppercase tracking-wider text-slate-500 w-24 shrink-0">
                          最後活動
                        </span>
                        {renderLastActivity(u)}
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-[10px] uppercase tracking-wider text-slate-500 w-24 shrink-0">
                          操作
                        </span>
                        {renderRoleControl(u)}
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-[10px] uppercase tracking-wider text-slate-500 w-24 shrink-0">
                          啟用
                        </span>
                        {renderActiveControl(u)}
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </div>

      {/* 分頁控制**在容器之外** —— 容器內容在載入／錯誤／切頁時會被整塊替換，
          控制項留在容器內就會跟著消失、鍵盤焦點也會被卸載。 */}
      {!isLoading && !error && (
        <PaginationControl
          page={page}
          pageSize={pageSize}
          total={total}
          isBusy={isBusy}
          onPageChange={handlePageChange}
        />
      )}
    </div>
  );
};

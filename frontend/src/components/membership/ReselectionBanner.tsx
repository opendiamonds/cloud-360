import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/auth-context';
import {
  acknowledgeReselection,
  fetchPendingReselections,
  type ReselectionOut,
} from '../../membership/membershipApi';

/**
 * ReselectionBanner — 交棒橫幅（`US12.4`／`AC12.4.3`／`AC12.4.4`）
 *
 * **四條不可違反的規定**（`functional-spec.md` §二之一／§二之二、`BR21.1`）：
 *
 * 1. **宿主無條件渲染**，即使 `events` 為空、即使抓取失敗、即使尚在載入。
 *    `aria-live` 掛在稍後才插入的元素上**不會被朗讀**——那是整條約束的由來。
 * 2. **`role="status"` 掛在宿主上**，不是掛在稍後插入的節點上。
 * 3. **載入中不渲染骨架**：橫幅是通知不是內容，骨架會變成一則假通知（`BR21.2`）。
 * 4. **宿主內不得放任何可互動內容**：`role="status"` 隱含 `aria-atomic="true"`，
 *    區域內任何變動都會重新播報**整個區域**。把可展開的專案清單與兩個動作鈕
 *    巢在宿主內，每按一次展開／收合，螢幕閱讀器就會把「你成了 N 個專案的
 *    管理者」加上 N 個專案名**整串重讀一次**。故兩者放在宿主的**兄弟節點**
 *    `<ReselectionBannerActions>`。**axe 不會回報這一類問題**，沒有任何機械
 *    閘門抓得到它——可觀察形式是展開／收合時宿主的 `textContent` **不變**。
 *
 * **掛載機制**：直接渲染於 `Layout.tsx` 的 React 樹內，**不走**
 * `src/cost/slotRegistry.tsx` 的 portal。三個理由（`logical-components.md` §三之一）：
 *   - 獨立 `createRoot` 的樹不在 `AuthProvider` 之下，`can()` 在那裡取不到；
 *   - `SlotName` 是封閉聯集，加第三個 slot 本來就要改那支檔；
 *   - **portal 失敗是靜默的**（`slotRegistry.tsx:9-10` 元素不存在時
 *     `return () => undefined`），而規定 1 要求無條件渲染。
 *
 * **已知缺口 `OPEN-MP24-1`：`ReselectionOut` 沒有專案名稱。** 實測它有九個欄位
 * （`id`／`project_id`／`cause`／`promoted_user_id`／`previous_owner_user_id`／
 * `previous_role`／`new_role`／`occurred_at`／`acknowledged_at`），其中不含名稱，
 * 而 `[D10]`=A 要求可展開「列出專案名」。本單元**不改 `U19` 已完成的回應模型**，
 * 也不對每筆事件再打一次專案端點（N+1 請求，本 repo 無此形狀先例）。
 * 處置：以「專案 #{project_id}」作為可識別的佔位，`project_id` 本身就是
 * `BR26.2` 導航所需的鍵，故功能不受影響、只有顯示名稱缺席。
 */

/** 宿主的 testid。三份上游產出統一使用這個值（`frontend-components.md` §九）。 */
const HOST_TESTID = 'reselection-banner-host';

/**
 * `BR21.3` 的**永久失敗閂**：收到 403 之後，本工作階段不再發出該請求。
 *
 * 這是規則逐字要求的（「視為永久失敗，本工作階段**不再**發出該請求」），
 * 與 `can("K3","view")` 前置條件處理的是**不同**情形：前置條件擋住「本來就
 * 沒權限」（計數 0），本閂處理「發出後才發現 403」（例如權限在工作階段中途
 * 被改掉）。少了它，那種情形下每一次換頁都會固定打一個必定 403 的請求。
 *
 * **模組層而非 state**：它要跨「同一份文件內的多次 `Layout` 掛載」存活，而
 * 每次 client-side 換頁都會換掉元件實例。**不得用瀏覽器儲存**（`NFR4.80`／
 * `SEC-U24-2` 明文禁止），故整頁重新載入時它會重置——那是這個限制下的必然
 * 結果，如實記載而不假裝是「永久」。
 *
 * **這不是快取**：它不保存任何回應資料，只記住「問過且被永久拒絕」。
 * `[N2]`=A 的「不快取」與 `performance-design.md` §二 不新增節流／去重的立場
 * 都不受影響——那兩條針對的是**成功**回應的重用，本閂針對的是永久失敗。
 */
// **以 token 為鍵，不是裸布林**（審查 `R-02`／Major）：`logout()` 只做
// `setToken(null)` ＋ `setUser(null)`（`AuthContext.tsx:56-61`），**不觸發整頁
// 導航**，所以模組不會重新載入。裸布林會讓甲（缺 `K3 view`）踩出的閂留給
// 同一個分頁裡接著登入的乙——乙即使有權限也永遠收不到橫幅，而 `AC12.4.3`
// 就這樣無聲消失。以 token 為鍵時，換人即換鍵，閂自動失效。
let bannerForbiddenForToken: string | null = null;

/**
 * 要被朗讀的那段文字。**只有文字**，不含任何節點。
 *
 * 零筆時回空字串——宿主仍在 DOM 裡但 `textContent` 為空（`BR21.2`、
 * `functional-spec.md:202` 逐字「此時為空」）。
 */
function summaryText(events: ReselectionOut[]): string {
  if (events.length === 0) return '';
  if (events.length === 1) return '你成了一個專案的管理者。';
  return `你成了 ${events.length} 個專案的管理者。`;
}

interface ActionsProps {
  events: ReselectionOut[];
  acknowledging: boolean;
  error: string | null;
  onAcknowledge: () => void;
  onViewMembers: (projectId: number) => void;
}

/**
 * 兩個動作鈕與可展開的專案清單。**位於宿主之外**（見檔頭規定 4）。
 *
 * `expanded` 是純呈現狀態：展開／收合**不改變**狀態機的狀態
 * （`functional-spec.md` §六之一），也不改變宿主的 `textContent`。
 */
const ReselectionBannerActions: React.FC<ActionsProps> = ({
  events,
  acknowledging,
  error,
  onAcknowledge,
  onViewMembers,
}) => {
  const [expanded, setExpanded] = useState(false);
  const aggregate = events.length >= 2;

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2">
      <button
        type="button"
        data-testid="reselection-banner-acknowledge"
        onClick={onAcknowledge}
        disabled={acknowledging}
        className="rounded-lg bg-amber-700 px-3 py-1.5 text-xs font-bold text-white hover:bg-amber-800 disabled:opacity-50"
      >
        {acknowledging ? '處理中…' : '知道了'}
      </button>
      <button
        type="button"
        data-testid="reselection-banner-view-members"
        // 單筆時直接導向該專案；彙總態改由展開清單逐項導向（`BR26.2`：
        // 不得導向任意一個或第一個），故此鈕在彙總態切換展開。
        onClick={() => (aggregate ? setExpanded((o) => !o) : onViewMembers(events[0].project_id))}
        aria-expanded={aggregate ? expanded : undefined}
        className="rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-bold text-amber-800 hover:bg-amber-50"
      >
        查看成員
      </button>
      {aggregate && (
        <button
          type="button"
          data-testid="reselection-banner-expand"
          onClick={() => setExpanded((o) => !o)}
          aria-expanded={expanded}
          className="rounded-lg px-2 py-1.5 text-xs font-bold text-amber-800 underline hover:text-amber-900"
        >
          {expanded ? '收合清單' : `展開 ${events.length} 個專案`}
        </button>
      )}
      {error && <span className="text-xs font-bold text-red-700">{error}</span>}
      {aggregate && expanded && (
        <ul data-testid="reselection-banner-projects" className="mt-1 w-full space-y-1">
          {events.map((ev) => (
            <li key={ev.id}>
              <button
                type="button"
                // 動態片段但是**容器級**的識別（同 `member-list-row-{userId}` 的
                // 形狀），不是以索引命名的 `button-${index}`。
                data-testid={`reselection-banner-project-${ev.project_id}`}
                onClick={() => onViewMembers(ev.project_id)}
                className="text-xs font-bold text-amber-800 underline hover:text-amber-900"
              >
                {/* OPEN-MP24-1：事件不帶專案名稱，以 id 作為可識別的佔位 */}
                專案 #{ev.project_id}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export const ReselectionBanner: React.FC = () => {
  const { token, can } = useAuth();
  const navigate = useNavigate();
  const [events, setEvents] = useState<ReselectionOut[]>([]);
  const [acknowledging, setAcknowledging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // **發出請求的前置條件**（`security-design.md` §一之二）：缺 `K3 view` 者
  // **不發請求**，計數為 0（`UIP-2`）。
  //
  // 這**不能**靠 `BR21.3` 代替：那是**重試**規則（「403 永久失敗，本工作階段
  // 不再發請求」），要先發一次並收到 403 才知道——實際計數會是 **1**，
  // 而 `UIP-2` 斷言的是 **0**。兩條規則並存不衝突：`can()` 擋住「本來就沒
  // 權限」的情形，`BR21.3` 處理「發出後才發現 403」與「有權限但失敗」。
  //
  // 實測缺 `K3 view` 的三個角色：`SRE`／`Ops_Lead`／`Platform_Engineer`
  // （`rbac_seed_data.py:343-345`）。宿主在 `Layout` 裡，故不設前置條件時
  // 這三個角色**每一次落地**都會打一個必定 403 的請求。
  const mayQuery = can('K3', 'view');

  useEffect(() => {
    // 三個發出前置條件：有 token、具 K3 view、且本工作階段未被永久拒絕。
    if (!token || !mayQuery || bannerForbiddenForToken === token) return;
    // 兩層抓取形狀：純抓取函式不碰 state，state 更新在 .then/.catch，
    // `cancelled` flag 防卸載後 setState（`TS-U24-4`）。
    let cancelled = false;
    fetchPendingReselections(token)
      .then((data) => {
        if (!cancelled) setEvents(data);
      })
      .catch((err: unknown) => {
        // `BR21.3`：**不對使用者顯示錯誤**。使用者沒有發起這個抓取，
        // 把它的失敗變成訊息會在每個落地頁產生一則無法處置的雜訊。
        // 訊號已由抓取層輸出（`SEC-U24-6`），此處刻意不設任何 state。
        //
        // 403 另外落閂：那是永久失敗，重試永遠不會成功。閂設在元件外的模組層
        // 而非 state——它要跨元件實例存活，才擋得住下一次換頁。**但它以 token
        // 為鍵**，所以同一分頁內換人登入時不會沿用前一位的結果（審查 `R-02`）。
        if (err instanceof Error && err.name === 'BannerForbidden') {
          bannerForbiddenForToken = token;
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token, mayQuery]);

  /**
   * 「知道了」→ **逐事件**各呼叫一次 acknowledge，並**逐筆**處置（`BR26.3`）。
   *
   * 已成功的（204 **或 404**）從本機移除，只有真正未成功的留下。
   * 這是 `BR26.3` 的核心：端點不冪等，而 404 等價於成功。
   */
  const handleAcknowledge = useCallback(() => {
    if (!token || events.length === 0) return;
    setAcknowledging(true);
    setError(null);
    const targets = events.slice();
    Promise.all(
      targets.map((ev) =>
        acknowledgeReselection(token, ev.id).then((ok) => ({ id: ev.id, ok }))
      )
    )
      .then((results) => {
        const failedIds = new Set(results.filter((r) => !r.ok).map((r) => r.id));
        // 就地移除已成功的，不整份重抓（`[F4]`=A 的同一形狀）。
        setEvents((prev) => prev.filter((ev) => failedIds.has(ev.id)));
        if (failedIds.size > 0) {
          setError(`${failedIds.size} 則通知未能標記為已讀，請稍後再試`);
        }
      })
      .finally(() => setAcknowledging(false));
  }, [token, events]);

  const handleViewMembers = useCallback(
    (projectId: number) => navigate(`/projects/${projectId}/members`),
    [navigate]
  );

  return (
    <div data-slot="reselection-banner">
      {/*
        宿主：無條件渲染、`role="status"` 寫死、**只放要被朗讀的文字**。
        `events` 為空時 `textContent` 為空字串，但元素本身仍在 DOM 裡。
      */}
      <div role="status" data-testid={HOST_TESTID} className="px-6 pt-3 text-sm text-amber-900">
        {summaryText(events)}
      </div>
      {events.length > 0 && (
        <div className="px-6 pb-2">
          <ReselectionBannerActions
            events={events}
            acknowledging={acknowledging}
            error={error}
            onAcknowledge={handleAcknowledge}
            onViewMembers={handleViewMembers}
          />
        </div>
      )}
    </div>
  );
};

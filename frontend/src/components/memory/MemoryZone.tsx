import React, { useCallback, useEffect, useRef, useState } from 'react';
import { deleteMemoryRecord, fetchMemoryRecords, type MemoryView } from '../../memory/memoryApi';
import { EMPTY_TITLE, zoneLabel, type MemoryKind } from '../../memory/memoryLabels';
import {
  EPISODIC_PAGE_SIZE,
  EPISODIC_PROBE_LIMIT,
  FULL_ZONE_LIMIT,
  computeEpisodicPage,
  episodicOffset,
  pageAfterEmptyRefetch,
  zoneCountLabel,
} from '../../memory/memoryPaging';
import { EpisodicPager } from './EpisodicPager';
import { MemoryItem } from './MemoryItem';

/**
 * MemoryZone — 記憶頁的一個區（語意／程序／情節各一個實例，`BR32.2`）
 *
 * 每區**各自抓取、各自擁有** `loading`／`default`／`empty`／`error`（`BR32.2`），
 * 故單一區失敗只有該區出現錯誤態。`empty` 與 `error` 是**不同的畫面**（`BR32.3`）：
 * 共用畫面時，讀取失敗會被讀成「我的記憶被清空了」。
 *
 * ## 防亂序：一個序號，管全部四條抓取路徑
 *
 * 初次載入、翻頁、重試、刪除後的背景重抓都遞增同一個 `requestSeq`，只有**最後
 * 發出**的那次回應能寫入 state（形狀照 `AdminPage.tsx` 的 `requestSeq`）。
 * effect 的 `cancelled` flag 只防卸載後 setState，**管不到**不經 effect 的背景
 * 重抓：使用者在背景重抓期間翻頁時，舊頁的重抓回應會把新頁蓋掉（nfr-design 審查
 * `R-02`）。`cancelled` 仍保留在初次載入的 effect 內，只負責卸載。
 *
 * ## 刪除後的背景重抓（情節區；偏離 `BR34.4` 字面「不發任何重抓」）
 *
 * offset 分頁之下，就地移除一列會讓伺服器端的第 `offset+20` 筆滑進本頁，而本頁
 * 不會知道——下一頁從新的 offset 起算，那一筆就被**漏掉**（functional-design 審查
 * `R-01`）。故刪除成功後**不切 loading** 地重抓目前頁（`BR34.3` 的「該區不進入
 * loading」照樣成立）；失敗時就地顯示「清單同步失敗」並播報，**不靜默**。
 *
 * **單一頁次調整者**：退頁（`BR34.6`）只由背景重抓的回應決定——回應為空且
 * `page > 1` 才退一頁。就地 `filter` 之後不立即退頁，否則同一次刪除會連退兩頁
 * （nfr-design 審查 `R-03`）。
 *
 * **不過濾任何一列**（`BR31.3`）：回應中的每一列都渲染；`canDelete` 只決定控件。
 *
 * ## 刪除完成時，使用者可能已經不在那一頁（code-generation 審查 `R-01`）
 *
 * `DELETE` 在途時「下一頁」並未停用（條目的 `deleting` 是它自己的 state）。若使用者
 * 此時翻頁，刪除完成的回呼帶的是**按下確認那一刻**的頁次。舊做法以那個頁次背景
 * 重抓：重抓會遞增序號而丟掉新頁的回應、把使用者拉回舊頁；重抓若失敗，該區停在
 * `loading` 且沒有重試鍵。故刪除完成後一律以**使用者目前所在的頁**為準
 * （`handleRemoved`），由三個 ref 記錄，不讀閉包裡的 `page`：
 *
 *   - 有翻頁／重試在途（`pendingLoadPageRef`）→ 以 `loadPage` **重發同一個目標頁**。
 *     在途的那次可能早於刪除生效、帶著已刪的列；重發仍走 `loadPage`，失敗即進
 *     `error`（有「重試」）——**不會**停在 `loading`。
 *   - 該區停在 `error`（`settledRef` 為 false）→ 不重抓；使用者手上已有「重試」。
 *   - 該區已穩定顯示某一頁（`shownPageRef`）→ 背景重抓**那一頁**（offset 位移對
 *     任何一頁都成立）。只在被刪的列就在畫面上那一頁時，才把焦點移到區標題；
 *     否則不搶焦點。
 *
 * 背景重抓只在**沒有**翻頁在途時發出，而唯一會把區切成 `loading` 的 `loadPage`
 * 會遞增序號使重抓的回應失效——故重抓的失敗分支執行時，該區必不在 `loading`。
 */

export interface MemoryZoneProps {
  kind: MemoryKind;
  token: string;
  /** 已確定為數字的目前使用者 id（`MemoryPage` 在它確定之前不掛載本元件）。 */
  currentUserId: number;
  announce: (message: string) => void;
  /** 初次載入（成功或失敗）結束時呼叫一次，供頁面播報「記憶已載入」。 */
  onInitialSettled: (kind: MemoryKind) => void;
}

type ZoneStatus = 'loading' | 'default' | 'empty' | 'error';

const SYNC_FAILED_TEXT = '清單同步失敗，畫面可能不是最新的';

export const MemoryZone: React.FC<MemoryZoneProps> = ({
  kind,
  token,
  currentUserId,
  announce,
  onInitialSettled,
}) => {
  const isEpisodic = kind === 'episodic';
  const label = zoneLabel(kind);
  const fragment = label.testIdFragment;
  const headingId = `memory-zone-${fragment}-heading`;

  const [status, setStatus] = useState<ZoneStatus>('loading');
  const [items, setItems] = useState<MemoryView[]>([]);
  const [page, setPage] = useState(1);
  /** 語意／程序區：**首次回應**是否滿載。黏著——刪除後仍顯示「N+ 則」（`R-06`）。 */
  const [wasFull, setWasFull] = useState(false);
  /** 至少成功載入過一次（翻頁期間保留分頁控件，使焦點不被卸載）。 */
  const [hasLoaded, setHasLoaded] = useState(false);
  /**
   * 情節區：**最近一次伺服器回應**是否還有下一頁。就地刪除一列之後，本地陣列少了
   * 探測用的第 21 筆，若由本地陣列重算會把「下一頁」錯誤停用——而伺服器端那些列
   * 仍在。故保留伺服器的判定，直到下一次伺服器回應覆蓋它。
   */
  const [serverHasNext, setServerHasNext] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncFailed, setSyncFailed] = useState(false);

  const requestSeq = useRef(0);
  const headingRef = useRef<HTMLHeadingElement>(null);
  /** 目前穩定顯示（`default`／`empty`）的頁次；只由 `applyLoaded` 寫入。 */
  const shownPageRef = useRef(1);
  /** 是否有一次成功回應正在顯示（`loading` 與 `error` 時為 false）。 */
  const settledRef = useRef(false);
  /** 在途的初次載入／翻頁／重試的目標頁；沒有在途時為 null。 */
  const pendingLoadPageRef = useRef<number | null>(null);

  const offsetFor = useCallback(
    (targetPage: number) => (isEpisodic ? episodicOffset(targetPage) : undefined),
    [isEpisodic]
  );
  const limit = isEpisodic ? EPISODIC_PROBE_LIMIT : FULL_ZONE_LIMIT;

  /** 單一落地點：所有成功回應都經過它。 */
  const applyLoaded = useCallback(
    (data: MemoryView[], targetPage: number, isFresh: boolean) => {
      shownPageRef.current = targetPage;
      settledRef.current = true;
      pendingLoadPageRef.current = null;
      setItems(data);
      setPage(targetPage);
      setStatus(data.length > 0 ? 'default' : 'empty');
      setHasLoaded(true);
      setServerHasNext(data.length > EPISODIC_PAGE_SIZE);
      setSyncing(false);
      setSyncFailed(false);
      if (!isEpisodic && isFresh) setWasFull(data.length >= FULL_ZONE_LIMIT);
    },
    [isEpisodic]
  );

  // 路徑 1：初次載入。純抓取函式 ＋ 只在 callback 內 setState（`team.md` 的兩層抓取）。
  useEffect(() => {
    let cancelled = false;
    const seq = (requestSeq.current += 1);
    pendingLoadPageRef.current = 1;
    settledRef.current = false;
    fetchMemoryRecords(token, kind, offsetFor(1), limit)
      .then((data) => {
        if (!cancelled && seq === requestSeq.current) applyLoaded(data, 1, true);
      })
      .catch(() => {
        if (!cancelled && seq === requestSeq.current) {
          pendingLoadPageRef.current = null;
          setStatus('error');
        }
      })
      .finally(() => {
        if (!cancelled) onInitialSettled(kind);
      });
    return () => {
      cancelled = true;
    };
  }, [token, kind, limit, offsetFor, applyLoaded, onInitialSettled]);

  // 路徑 2：翻頁與重試（該區進入 loading；失敗時頁次不前進，`W3` 第 5 步）。
  const loadPage = (targetPage: number) => {
    const seq = (requestSeq.current += 1);
    pendingLoadPageRef.current = targetPage;
    settledRef.current = false;
    setStatus('loading');
    setSyncing(false);
    setSyncFailed(false);
    fetchMemoryRecords(token, kind, offsetFor(targetPage), limit)
      .then((data) => {
        if (seq === requestSeq.current) applyLoaded(data, targetPage, true);
      })
      .catch(() => {
        if (seq === requestSeq.current) {
          pendingLoadPageRef.current = null;
          setStatus('error');
          announce(`${label.title}載入失敗`);
        }
      });
  };

  // 路徑 3：刪除後的背景重抓（僅情節區）。不切 loading；序號不符即丟棄。
  const resyncInBackground = (targetPage: number) => {
    const seq = (requestSeq.current += 1);
    setSyncing(true);
    setSyncFailed(false);
    fetchMemoryRecords(token, kind, offsetFor(targetPage), limit)
      .then((data) => {
        if (seq !== requestSeq.current) return;
        const nextPage = pageAfterEmptyRefetch(data.length, targetPage);
        if (nextPage !== targetPage) {
          // 唯一的退頁點（`BR34.6`）。只退一頁。
          loadPage(nextPage);
          return;
        }
        applyLoaded(data, targetPage, false);
      })
      .catch(() => {
        if (seq !== requestSeq.current) return;
        // 保留就地移除後的畫面：剛完成的刪除是成功的，不被一次補償失敗蓋掉。
        setSyncing(false);
        setSyncFailed(true);
        announce(SYNC_FAILED_TEXT);
      });
  };

  const deleteRecord = (memoryId: string) => deleteMemoryRecord(token, memoryId);

  /**
   * `rowPage`：被刪的列所在的頁（按下確認那一刻畫面上的頁）。只用來判定要不要
   * 搬焦點，**不**用來決定重抓哪一頁——那一律以 ref 記錄的目前頁為準（見檔頭）。
   */
  const handleRemoved = (memoryId: string, summary: string, rowPage: number) => {
    setItems((prev) => prev.filter((r) => r.memory_id !== memoryId));
    announce(`已刪除：${summary}`);
    if (!isEpisodic) {
      // 原焦點目標（該則的確認鍵）已不存在，焦點移到區標題（`W4` 第 5 步）。
      headingRef.current?.focus();
      return;
    }
    const inFlightPage = pendingLoadPageRef.current;
    if (inFlightPage !== null) {
      // 在途的那次可能早於刪除生效；重發同一個目標頁。列表此刻不在畫面上，不搶焦點。
      loadPage(inFlightPage);
      return;
    }
    if (!settledRef.current) return; // `error`：使用者已有「重試」。
    const currentPage = shownPageRef.current;
    if (rowPage === currentPage) headingRef.current?.focus();
    resyncInBackground(currentPage);
  };

  const episodicView = computeEpisodicPage(items, page);
  const hasNext = episodicView.hasNext || serverHasNext;
  const rendered = isEpisodic ? episodicView.rendered : items;
  const countLabel = isEpisodic
    ? zoneCountLabel(episodicOffset(page) + rendered.length, hasNext)
    : zoneCountLabel(items.length, wasFull);

  // 刪光之後的呈現：語意／程序區直接是空態；情節區等背景重抓的回應決定
  // （第一頁可能被下一頁的列補滿，不能先說「沒有」）。
  const showEmpty =
    status === 'empty' ||
    (status === 'default' && rendered.length === 0 && (!isEpisodic || (!syncing && !syncFailed && page === 1)));
  const showList = status === 'default' && rendered.length > 0;
  const showPager =
    isEpisodic && hasLoaded && (status === 'default' || status === 'loading' || (status === 'empty' && page > 1));

  return (
    <section
      role="region"
      aria-labelledby={headingId}
      data-testid={`memory-zone-${fragment}`}
      className="rounded-2xl border border-gray-200 bg-gray-50 p-4"
    >
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2
          id={headingId}
          ref={headingRef}
          tabIndex={-1}
          className="text-base font-extrabold text-gray-900 outline-none"
        >
          {label.title}
          <span className="ml-2 text-sm font-bold text-gray-500">（{label.hint}）</span>
        </h2>
        {(status === 'default' || status === 'empty') && (
          <span data-testid={`memory-zone-${fragment}-count`} className="text-sm font-bold text-gray-600">
            {countLabel}
          </span>
        )}
      </div>

      {status === 'loading' && (
        <div aria-busy="true" className="space-y-2">
          <div className="h-10 animate-pulse rounded-lg bg-gray-200" />
          <div className="h-10 animate-pulse rounded-lg bg-gray-200" />
          <span className="sr-only">載入中</span>
        </div>
      )}

      {status === 'error' && (
        <div
          data-testid={`memory-zone-${fragment}-error`}
          className="flex flex-wrap items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3"
        >
          <span className="text-sm font-bold text-red-700">無法載入{label.title}。</span>
          <button
            type="button"
            data-testid={`memory-zone-${fragment}-retry`}
            onClick={() => loadPage(page)}
            className="rounded-md border border-red-300 bg-white px-3 py-1 text-sm font-bold text-red-700 hover:bg-red-100"
          >
            重試
          </button>
        </div>
      )}

      {showEmpty && (
        <div data-testid={`memory-zone-${fragment}-empty`} className="rounded-lg bg-white px-4 py-3">
          <p className="text-sm font-bold text-gray-700">{EMPTY_TITLE}</p>
          <p className="text-sm text-gray-500">{label.emptyHint}</p>
        </div>
      )}

      {status === 'default' && rendered.length === 0 && isEpisodic && syncing && (
        <p className="text-sm text-gray-500">正在更新清單…</p>
      )}

      {syncFailed && (
        <p data-testid={`memory-zone-${fragment}-sync-failed`} className="mb-2 text-sm font-bold text-amber-700">
          {SYNC_FAILED_TEXT}
        </p>
      )}

      {showList && (
        <ul className="space-y-2">
          {rendered.map((record) => {
            const isOwn = record.owner_user_id === currentUserId;
            return (
              <MemoryItem
                key={record.memory_id}
                record={record}
                showDates={isEpisodic}
                isOwn={isOwn}
                // UI 判定，非授權（`SEC-U15-2`）：伺服器以 404 拒絕非擁有者。
                canDelete={isOwn}
                deleteRecord={deleteRecord}
                onRemoved={(memoryId, summary) => handleRemoved(memoryId, summary, page)}
                announce={announce}
              />
            );
          })}
        </ul>
      )}

      {showPager && (
        <EpisodicPager
          page={page}
          rangeStart={episodicView.rangeStart}
          rangeEnd={episodicView.rangeEnd}
          hasNext={hasNext}
          isBusy={status === 'loading'}
          onPageChange={loadPage}
        />
      )}
    </section>
  );
};

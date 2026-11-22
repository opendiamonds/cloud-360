import React, { useCallback, useRef, useState } from 'react';
import { useAuth } from '../context/auth-context';
import { LiveRegion } from '../components/LiveRegion';
import { MemoryZone } from '../components/memory/MemoryZone';
import { MEMORY_ZONE_KINDS, type MemoryKind } from '../memory/memoryLabels';

/**
 * MemoryPage — `U15` 的「我的記憶」頁（`/memory`）
 *
 * **契約（`U17 a11y-gate` 以 test id 為掃描標的，請勿改名）**：`memory-page`、
 * `memory-zone-{semantic|procedural|episodic}`、`memory-item-{id}` 等，見
 * `functional-design/frontend-components.md §九`。
 *
 * - 路由走 `ProtectedRoute`、**不包** `CapabilityRoute`（`BR31.1`）。
 * - 三區固定存在、順序固定（`BR32.1`），各自抓取（`BR32.2`）——本頁**不持有**
 *   任何一區的條目。
 * - 記憶內容只存在於各區的元件 state：不新增 Context、不放模組層變數、不寫
 *   瀏覽器儲存（`NFR4.90`／`NFR7.90`）。離開本頁即釋放。
 *
 * ## `user.id` 未定之前不掛載三區（`frontend-components.md §四之一`）
 *
 * `BR35.1` 的「你／其他使用者」與 `BR35.2` 的刪除鍵都以 `user.id` 為比較基準；
 * `undefined` 時先渲染再修正，會讓自己的記憶短暫被標成「其他使用者」且沒有刪除鍵。
 *
 * **`/api/auth/me` 失敗時 `user.id` 永遠不會出現**（`login()` 先以不含 `id` 的物件
 * `setUser`，`/me` 失敗時保留它）。此時若只看 `user.id` 會無限轉圈
 * （functional-design 審查 `R-03`）——故 `isLoading` 已結束而 `id` 仍不是數字時，
 * 顯示錯誤態與重新整理提示。
 */
export const MemoryPage: React.FC = () => {
  const { user, token, isLoading } = useAuth();
  const [liveMessage, setLiveMessage] = useState('正在載入記憶');
  const settledKinds = useRef(new Set<MemoryKind>());

  const announce = useCallback((message: string) => {
    setLiveMessage(message);
  }, []);

  const handleInitialSettled = useCallback(
    (kind: MemoryKind) => {
      settledKinds.current.add(kind);
      if (settledKinds.current.size === MEMORY_ZONE_KINDS.length) {
        announce('記憶已載入');
      }
    },
    [announce]
  );

  const userId = user?.id;
  const identity = typeof userId === 'number' && token ? { userId, token } : null;

  return (
    <div data-testid="memory-page" className="mx-auto w-full max-w-4xl space-y-4 p-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-extrabold text-gray-900">我的記憶</h1>
        <div className="rounded-xl border border-brand-100 bg-brand-50 px-4 py-3 text-sm text-gray-700">
          <p>
            這裡是大腦記住的關於你的事。你可以刪掉<strong>自己的</strong>任何一則；標為「平台可見（他人的記憶）」的列由其擁有者管理。
          </p>
          <p>刪除後大腦不再依據它回答，但刪除動作本身會留下稽核紀錄。</p>
        </div>
      </header>

      {identity ? (
        <>
          {MEMORY_ZONE_KINDS.map((kind) => (
            <MemoryZone
              key={kind}
              kind={kind}
              token={identity.token}
              currentUserId={identity.userId}
              announce={announce}
              onInitialSettled={handleInitialSettled}
            />
          ))}
          <p className="text-xs text-gray-500">保存期限：情節記憶 90 天後自動刪除。</p>
        </>
      ) : isLoading ? (
        <p className="text-sm text-gray-500">正在確認你的身分…</p>
      ) : (
        <div
          data-testid="memory-page-identity-error"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-bold text-red-700"
        >
          無法確認你的身分，因此無法判斷哪些記憶是你的。請重新整理頁面後再試。
        </div>
      )}

      <LiveRegion message={liveMessage} />
    </div>
  );
};

import type { ReactNode } from 'react';
import { NavChromeProvider } from './NavChromeContext';
import { Sidebar } from './Sidebar';
import { ReselectionBanner } from './membership/ReselectionBanner';

interface LayoutProps {
  children: ReactNode;
}

export const Layout = ({ children }: LayoutProps) => {
  return (
    <NavChromeProvider>
      <div className="flex h-screen w-full bg-gray-50 overflow-hidden font-sans">
        <Sidebar />
        {/* min-h-0 + overflow-y-auto：Admin／矩陣頁可用滾輪看完整內容 */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0 overflow-y-auto overflow-x-hidden">
          <div data-slot="cost-banner" />
          {/*
            U24：交棒橫幅的宿主。**直接渲染於 React 樹內**，不走
            src/cost/slotRegistry.tsx 的 portal —— 該 portal 在目標元素不存在時
            `return () => undefined`（slotRegistry.tsx:9-10），是**靜默 no-op**，
            而 BR21.1 要求宿主無條件渲染；且它另開的 createRoot 不在
            AuthProvider 之下，`can("K3","view")` 在那棵樹裡取不到。
            掛在 Layout 使一處實作涵蓋全部落地頁（[F1]=A）。
          */}
          <ReselectionBanner />
          {children}
        </div>
      </div>
    </NavChromeProvider>
  );
};

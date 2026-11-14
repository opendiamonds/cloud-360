import React from 'react';
import { BrainSessionContext, type BrainConnection } from '../../brain/brainSession';
import { LiveRegion } from '../LiveRegion';

/**
 * BrainSession — 把頁面持有的大腦連線提供給子元件（`frontend-components.md` §二）
 *
 * 連線由頁面呼叫 `useBrainConnection` 持有（子頁面的同步掛點需要同一個物件），本元件只負責提供
 * context，並掛**一個**既有 `LiveRegion` 實例——本頁所有大腦相關播報都寫入它（`BR98.3`）。
 */
export const BrainSession: React.FC<{ connection: BrainConnection; children: React.ReactNode }> = ({
  connection,
  children,
}) => (
  <BrainSessionContext.Provider value={connection}>
    <div data-brain-session={connection.page} className="contents">
      {children}
      <div data-testid="brain-live">
        <LiveRegion message={connection.announcement} />
      </div>
    </div>
  </BrainSessionContext.Provider>
);

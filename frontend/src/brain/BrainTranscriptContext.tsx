import React, { useEffect, useMemo, useReducer } from 'react';
import { useAuth } from '../context/auth-context';
import {
  BrainTranscriptContextObject,
  initialTranscriptState,
  transcriptReducer,
} from './brainTranscript';

/**
 * BrainTranscriptProvider — 應用程式層、記憶體內的對話紀錄（`BR93.4`；`[EP4]`=A）
 *
 * 掛在 `AuthProvider` 之下、`BrowserRouter` 之上，故換頁不丟紀錄。
 *
 * **清除綁登入／登出事件**（functional-design R-03 使用者裁決；security-design §六之一）：訂閱
 * `subscribeAuthBoundary`，`login()`／`logout()` 第一行同步通知即 `reset`。**不**以使用者 id 作 React
 * key 重掛（`/me` 失敗時 `user.id` 缺值，且重掛路由樹會與登入後的 navigate 競賽），也**不**以 effect
 * 監聽 `user`。setState（dispatch）發生在訂閱回呼內、不在 effect body（`react-hooks/set-state-in-effect`）；
 * effect 的回傳值即退訂。
 */
export const BrainTranscriptProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { subscribeAuthBoundary } = useAuth();
  const [state, dispatch] = useReducer(transcriptReducer, undefined, initialTranscriptState);

  useEffect(() => subscribeAuthBoundary(() => dispatch({ type: 'reset' })), [subscribeAuthBoundary]);

  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <BrainTranscriptContextObject.Provider value={value}>{children}</BrainTranscriptContextObject.Provider>;
};

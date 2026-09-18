import { createContext, useContext } from 'react';

// Context 物件、型別與 useAuth hook 與 AuthProvider 分檔存放：react-refresh 要求
// 一個模組只匯出 component，否則編輯該檔會讓 HMR 退化成整頁重載。
// AuthProvider 在 ./AuthContext.tsx。

export type StoryAction = 'view' | 'edit' | 'review';

/** J5：註冊後尚未取得正式角色的授權狀態 */
export type AuthorizationStatus = 'pending' | 'approved' | 'rejected';

export interface StoryPermission {
  view: boolean;
  edit: boolean;
  review: boolean;
  can_view?: boolean;
  can_edit?: boolean;
  can_review?: boolean;
}

export interface PendingRequest {
  id: number;
  requested_role: string;
  created_at?: string;
  updated_at?: string;
}

export interface User {
  id?: number;
  username: string;
  /** J5：待授權使用者尚無正式角色 */
  role: string | null;
  is_active?: boolean;
  authorization_status?: AuthorizationStatus;
  permissions?: Record<string, StoryPermission>;
  pending_request?: PendingRequest | null;
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  /** J5：待授權狀態，為 true 時所有 story 權限一律 false */
  isPending: boolean;
  login: (username: string, token: string, role: string | null) => Promise<void>;
  logout: () => void;
  checkAuthSession: () => Promise<boolean>;
  can: (storyId: string, action?: StoryAction) => boolean;
  /** 架構圖生成（A1／A2／A4 同一功能） */
  canArch: (action?: StoryAction) => boolean;
  refreshMe: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

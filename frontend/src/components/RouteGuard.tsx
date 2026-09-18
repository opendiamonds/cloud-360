import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/auth-context';
import type { StoryAction } from '../context/auth-context';

const LoadingScreen: React.FC<{ label: string }> = ({ label }) => (
  <div className="flex h-screen w-screen items-center justify-center bg-gray-50 text-gray-500 font-medium">
    <div className="flex flex-col items-center gap-3">
      <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
      <span className="text-sm tracking-wider">{label}</span>
    </div>
  </div>
);

export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading, isPending } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <LoadingScreen label="載入中，請稍候..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (isPending && location.pathname !== '/waiting-approval') {
    return <Navigate to="/waiting-approval" replace />;
  }

  return <>{children}</>;
};

/** 依 story × action 檢查（預設 view） */
export const CapabilityRoute: React.FC<{
  storyId: string;
  action?: StoryAction;
  children: React.ReactNode;
}> = ({ storyId, action = 'view', children }) => {
  const { isAuthenticated, isLoading, can } = useAuth();

  if (isLoading) {
    return <LoadingScreen label="校驗權限中..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!can(storyId, action)) {
    return <Navigate to="/403" replace />;
  }

  return <>{children}</>;
};

/** @deprecated 改用 CapabilityRoute(J3a)；保留相容舊引用 */
export const AdminRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <CapabilityRoute storyId="J3a" action="view">
    {children}
  </CapabilityRoute>
);

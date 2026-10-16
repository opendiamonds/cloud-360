import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/auth-context';
import { ProtectedRoute, CapabilityRoute } from './components/RouteGuard';
import { Layout } from './components/Layout';

import { LoginPage } from './pages/LoginPage';
import { WorkspacePage } from './pages/WorkspacePage';
import { AdminPage } from './pages/AdminPage';
import { RolePermissionsPage } from './pages/RolePermissionsPage';
import { ForbiddenPage } from './pages/ForbiddenPage';
import { WaitingApprovalPage } from './pages/WaitingApprovalPage';
import { AuthorizationRequestsPage } from './pages/AuthorizationRequestsPage';
import { AssessmentPage } from './pages/AssessmentPage';
import { CostPage } from './pages/CostPage';
import { MembersListPage } from './pages/MembersListPage';
import { MemberDetailPage } from './pages/MemberDetailPage';
import { MemoryPage } from './pages/MemoryPage';
import { ProjectsListPage } from './pages/ProjectsListPage';
import { ProjectCreatePage } from './pages/ProjectCreatePage';
import { ProjectDetailPage } from './pages/ProjectDetailPage';

/** 依權限導向第一個可用頁；pending → 等待授權；皆無則 403 */
const DefaultRedirect: React.FC = () => {
  const { canArch, can, isLoading, isPending } = useAuth();
  if (isLoading) return null;
  if (isPending) return <Navigate to="/waiting-approval" replace />;
  if (canArch('view')) return <Navigate to="/workspace" replace />;
  if (can('A3', 'view')) return <Navigate to="/assessment" replace />;
  if (can('C1', 'view')) return <Navigate to="/cost" replace />;
  if (can('J3a', 'view')) return <Navigate to="/admin/users" replace />;
  if (can('J3b', 'view')) return <Navigate to="/admin/role-permissions" replace />;
  return <Navigate to="/403" replace />;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/403" element={<ForbiddenPage />} />
          <Route
            path="/waiting-approval"
            element={
              <ProtectedRoute>
                <WaitingApprovalPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/workspace"
            element={
              <ProtectedRoute>
                <CapabilityRoute storyId="A1" action="view">
                  <Layout>
                    <WorkspacePage />
                  </Layout>
                </CapabilityRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/assessment"
            element={
              <ProtectedRoute>
                <CapabilityRoute storyId="A3" action="view">
                  <Layout>
                    <AssessmentPage />
                  </Layout>
                </CapabilityRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/cost"
            element={
              <ProtectedRoute>
                <CapabilityRoute storyId="C1" action="view">
                  <Layout>
                    <CostPage />
                  </Layout>
                </CapabilityRoute>
              </ProtectedRoute>
            }
          />

          {/*
            U15：我的記憶。走 ProtectedRoute、**不包** CapabilityRoute（BR31.1）——
            把關的是伺服器端的擁有者欄位與帳號核准狀態，不是 story id；包上
            CapabilityRoute 會要求一個不存在的 story id，使所有人被導向 /403。
            前例為上方的 /waiting-approval。
          */}
          <Route
            path="/memory"
            element={
              <ProtectedRoute>
                <Layout>
                  <MemoryPage />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/*
            U23：專案清單／建立／詳情。三條都以 K2 把關（BR81.1）：清單與詳情需 view、
            建立需 edit。react-router v7 以具體度排序，靜態段 `/projects/new` 優先於
            參數段 `/projects/:projectId`，也不與下方 U24 的 `/projects/:projectId/members`
            系列互相遮蔽。需求籤的 K4 把關在頁內（BR83.2），不是路由層。
          */}
          <Route
            path="/projects"
            element={
              <ProtectedRoute>
                <CapabilityRoute storyId="K2" action="view">
                  <Layout>
                    <ProjectsListPage />
                  </Layout>
                </CapabilityRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/projects/new"
            element={
              <ProtectedRoute>
                <CapabilityRoute storyId="K2" action="edit">
                  <Layout>
                    <ProjectCreatePage />
                  </Layout>
                </CapabilityRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/projects/:projectId"
            element={
              <ProtectedRoute>
                <CapabilityRoute storyId="K2" action="view">
                  <Layout>
                    <ProjectDetailPage />
                  </Layout>
                </CapabilityRoute>
              </ProtectedRoute>
            }
          />

          {/*
            U24：成員頁。以既有 CapabilityRoute 做**能力層**把關（K3／view）。
            per-project 那一層**不能**用它表達（K-16 的 two_layer_rule）——
            管理者控件的出現依據伺服器回傳的 role 結論，見 MembersListPage 的
            canManage 兩段式判定。詳情路由放在清單之後：react-router v7 以
            具體度排序，兩者不互相遮蔽。
          */}
          <Route
            path="/projects/:projectId/members"
            element={
              <ProtectedRoute>
                <CapabilityRoute storyId="K3" action="view">
                  <Layout>
                    <MembersListPage />
                  </Layout>
                </CapabilityRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/projects/:projectId/members/:userId"
            element={
              <ProtectedRoute>
                <CapabilityRoute storyId="K3" action="view">
                  <Layout>
                    <MemberDetailPage />
                  </Layout>
                </CapabilityRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/users"
            element={
              <ProtectedRoute>
                <CapabilityRoute storyId="J3a" action="view">
                  <Layout>
                    <AdminPage />
                  </Layout>
                </CapabilityRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/authorization-requests"
            element={
              <ProtectedRoute>
                <CapabilityRoute storyId="J3a" action="view">
                  <Layout>
                    <AuthorizationRequestsPage />
                  </Layout>
                </CapabilityRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/role-permissions"
            element={
              <ProtectedRoute>
                <CapabilityRoute storyId="J3b" action="view">
                  <Layout>
                    <RolePermissionsPage />
                  </Layout>
                </CapabilityRoute>
              </ProtectedRoute>
            }
          />

          <Route path="/admin" element={<Navigate to="/admin/users" replace />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <DefaultRedirect />
              </ProtectedRoute>
            }
          />
          <Route
            path="*"
            element={
              <ProtectedRoute>
                <DefaultRedirect />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;

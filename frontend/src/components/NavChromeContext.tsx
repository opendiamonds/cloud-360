/* Context modules intentionally export the hook alongside the Provider. */
/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from 'react';

const SIDEBAR_STORAGE_KEY = 'cloud360.nav.sidebarCollapsed';

type NavChromeContextValue = {
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebarCollapsed: () => void;
};

const NavChromeContext = createContext<NavChromeContextValue | null>(null);

export function useLayoutNav(): NavChromeContextValue {
  const ctx = useContext(NavChromeContext);
  if (!ctx) {
    throw new Error('useLayoutNav must be used within NavChromeProvider');
  }
  return ctx;
}

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

function persistCollapsed(collapsed: boolean) {
  try {
    localStorage.setItem(SIDEBAR_STORAGE_KEY, collapsed ? '1' : '0');
  } catch {
    /* ignore */
  }
}

export function NavChromeProvider({ children }: { children: ReactNode }) {
  const [sidebarCollapsed, setSidebarCollapsedState] = useState(readCollapsed);

  const setSidebarCollapsed = useCallback((collapsed: boolean) => {
    setSidebarCollapsedState(collapsed);
    persistCollapsed(collapsed);
  }, []);

  const toggleSidebarCollapsed = useCallback(() => {
    setSidebarCollapsedState((prev) => {
      const next = !prev;
      persistCollapsed(next);
      return next;
    });
  }, []);

  return (
    <NavChromeContext.Provider
      value={{ sidebarCollapsed, setSidebarCollapsed, toggleSidebarCollapsed }}
    >
      {children}
    </NavChromeContext.Provider>
  );
}

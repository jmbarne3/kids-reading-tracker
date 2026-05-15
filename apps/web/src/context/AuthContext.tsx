import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import { getMe, login as apiLogin, logout as apiLogout, register as apiRegister } from '../api/auth';
import type { RegisterData, User } from '../api/auth';

interface AuthState {
  user: User | null;
  loading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, loading: true });

  useEffect(() => {
    getMe().then((user) => setState({ user, loading: false }));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const user = await apiLogin(email, password);
    setState({ user, loading: false });
  }, []);

  const register = useCallback(async (data: RegisterData) => {
    const user = await apiRegister(data);
    setState({ user, loading: false });
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setState({ user: null, loading: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}

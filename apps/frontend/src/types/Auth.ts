export interface AuthState {
  token: string | null;
  user: {
    id: string;
    username: string;
    email: string;
  } | null;
  isAuthenticated: boolean; // derived from token !== null
  hasHydrated: boolean; // hydration guard flag
  login: (token: string, user: AuthState['user']) => void;
  logout: () => void;
  setToken: (token: string | null) => void;
  setUser: (user: AuthState['user']) => void;
}

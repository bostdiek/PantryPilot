export interface AuthState {
  token: string | null;
  user: {
    id: string;
    username: string;
    email: string;
  } | null;
  login: (token: string, user: AuthState['user']) => void;
  logout: () => void;
  setToken: (token: string | null) => void;
  setUser: (user: AuthState['user']) => void;
}

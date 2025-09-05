// Types for authentication as specified in the issue

export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
}

export interface LoginFormData {
  username: string;
  password: string;
}

// Optional: Decoded token claims (if needed for storing basic claims like 'sub')
export interface DecodedToken {
  sub: string;
  exp: number;
  iat: number;
}

export interface AuthState {
  token: string | null;
  user: {
    id: string;
    username: string;
    email: string;
  } | null;
  hasHydrated: boolean; // hydration guard flag
  login: (token: string, user: AuthState['user']) => void;
  logout: () => void;
  setToken: (token: string | null) => void;
  setUser: (user: AuthState['user']) => void;
}

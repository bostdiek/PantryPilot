// Types for authentication as specified in the issue

export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
}

export interface LoginFormData {
  username: string;
  password: string;
}

export interface RegisterFormData {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
  first_name?: string;
  last_name?: string;
}

// Optional: Decoded token claims (if needed for storing basic claims like 'sub')
export interface DecodedToken {
  sub: string;
  exp: number;
  iat: number;
}

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
}

export interface AuthState {
  token: string | null;
  user: AuthUser | null;
  hasHydrated: boolean; // hydration guard flag
  login: (token: string, user: AuthUser) => void;
  logout: () => void;
  setToken: (token: string | null) => void;
  setUser: (user: AuthUser | null) => void;
  getDisplayName: () => string;
}

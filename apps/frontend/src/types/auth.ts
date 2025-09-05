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
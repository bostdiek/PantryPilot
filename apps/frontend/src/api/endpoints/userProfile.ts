import { apiClient } from '../client';
import type { 
  UserProfileResponse,
  UserProfileUpdate,
  UserPreferencesResponse,
  UserPreferencesUpdate 
} from '../../types/UserPreferences';

export const userProfileApi = {
  /**
   * Get current user's profile with preferences
   */
  async getProfile(): Promise<UserProfileResponse> {
    return apiClient.request<UserProfileResponse>('/api/v1/users/me');
  },

  /**
   * Update current user's profile information
   */
  async updateProfile(update: UserProfileUpdate): Promise<UserProfileResponse> {
    return apiClient.request<UserProfileResponse>('/api/v1/users/me', {
      method: 'PATCH',
      body: JSON.stringify(update),
    });
  },

  /**
   * Get current user's preferences
   */
  async getPreferences(): Promise<UserPreferencesResponse> {
    return apiClient.request<UserPreferencesResponse>('/api/v1/users/me/preferences');
  },

  /**
   * Update current user's preferences
   */
  async updatePreferences(update: UserPreferencesUpdate): Promise<UserPreferencesResponse> {
    return apiClient.request<UserPreferencesResponse>('/api/v1/users/me/preferences', {
      method: 'PATCH',
      body: JSON.stringify(update),
    });
  },

  /**
   * Create or replace current user's preferences
   */
  async createPreferences(preferences: UserPreferencesUpdate): Promise<UserPreferencesResponse> {
    return apiClient.request<UserPreferencesResponse>('/api/v1/users/me/preferences', {
      method: 'POST',
      body: JSON.stringify(preferences),
    });
  },
};
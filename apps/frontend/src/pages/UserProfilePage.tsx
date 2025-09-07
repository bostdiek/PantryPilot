import { useState, useCallback, useEffect } from 'react';
import { 
  Container, 
  Card, 
  Button, 
  Input, 
  Select, 
  LoadingSpinner,
  EmptyState
} from '../components/ui';
import { useAuthStore, useDisplayName } from '../stores/useAuthStore';
import { useUserPreferencesStore } from '../stores/useUserPreferencesStore';
import { userProfileApi } from '../api/endpoints/userProfile';
import { 
  commonAllergies, 
  commonDietaryRestrictions, 
  commonCuisines,
  toBackendPreferences,
  type UserPreferences,
  type UserProfileUpdate 
} from '../types/UserPreferences';

function UserProfilePage() {
  const { user, setUser } = useAuthStore();
  const { preferences, updatePreferences, syncWithBackend } = useUserPreferencesStore();
  const displayName = useDisplayName();
  
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    firstName: user?.first_name || '',
    lastName: user?.last_name || '',
    username: user?.username || '',
  });
  const [preferencesData, setPreferencesData] = useState<UserPreferences>(preferences);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Load user profile and preferences from backend on mount
  useEffect(() => {
    const loadProfile = async () => {
      if (!user) return;
      
      setLoading(true);
      try {
        const profile = await userProfileApi.getProfile();
        
        // Update user info if needed
        if (profile.first_name !== user.first_name || 
            profile.last_name !== user.last_name) {
          setUser({
            ...user,
            first_name: profile.first_name,
            last_name: profile.last_name,
          });
        }
        
        // Sync preferences with backend
        if (profile.preferences) {
          syncWithBackend(profile.preferences);
        }
        
        // Update form data
        setFormData({
          firstName: profile.first_name || '',
          lastName: profile.last_name || '',
          username: profile.username,
        });
      } catch (error) {
        console.error('Failed to load profile:', error);
        // Don't show error to user, just use local data
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, [user, setUser, syncWithBackend]);

  // Sync local preferences data with store
  useEffect(() => {
    setPreferencesData(preferences);
  }, [preferences]);

  // Form validation
  const validateForm = useCallback(() => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.username || formData.username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters';
    }
    
    if (formData.username && formData.username.length > 50) {
      newErrors.username = 'Username must be 50 characters or less';
    }
    
    if (formData.firstName && formData.firstName.length > 50) {
      newErrors.firstName = 'First name must be 50 characters or less';
    }
    
    if (formData.lastName && formData.lastName.length > 50) {
      newErrors.lastName = 'Last name must be 50 characters or less';
    }

    if (preferencesData.familySize < 1 || preferencesData.familySize > 20) {
      newErrors.familySize = 'Family size must be between 1 and 20';
    }

    if (preferencesData.defaultServings < 1 || preferencesData.defaultServings > 50) {
      newErrors.defaultServings = 'Default servings must be between 1 and 50';
    }

    if (preferencesData.mealPlanningDays < 1 || preferencesData.mealPlanningDays > 30) {
      newErrors.mealPlanningDays = 'Meal planning days must be between 1 and 30';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData, preferencesData]);

  const handleInputChange = useCallback((field: string) => (
    value: string
  ) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  }, []);

  const handlePreferenceChange = useCallback((field: keyof UserPreferences) => (
    value: any
  ) => {
    setPreferencesData(prev => ({ ...prev, [field]: value }));
  }, []);

  const handleSave = useCallback(async () => {
    if (!validateForm()) {
      return;
    }

    setSaving(true);
    try {
      // Update user profile if needed
      if (user && (
        formData.firstName !== user.first_name ||
        formData.lastName !== user.last_name ||
        formData.username !== user.username
      )) {
        const profileUpdate: UserProfileUpdate = {
          first_name: formData.firstName || undefined,
          last_name: formData.lastName || undefined,
          username: formData.username,
        };
        
        const updatedProfile = await userProfileApi.updateProfile(profileUpdate);
        setUser({
          ...user,
          first_name: updatedProfile.first_name,
          last_name: updatedProfile.last_name,
          username: updatedProfile.username,
        });
      }

      // Update preferences
      const backendPrefsUpdate = toBackendPreferences(preferencesData);
      const updatedPrefs = await userProfileApi.updatePreferences(backendPrefsUpdate);
      
      // Update local state
      updatePreferences(preferencesData);
      syncWithBackend(updatedPrefs);

      setIsEditing(false);
      
    } catch (error) {
      console.error('Failed to save profile:', error);
      setErrors({ general: 'Failed to save changes. Please try again.' });
      // TODO: Show error toast when toast system is available
    } finally {
      setSaving(false);
    }
  }, [formData, preferencesData, user, setUser, updatePreferences, syncWithBackend, validateForm]);

  const handleCancel = useCallback(() => {
    setFormData({
      firstName: user?.first_name || '',
      lastName: user?.last_name || '',
      username: user?.username || '',
    });
    setPreferencesData(preferences);
    setErrors({});
    setIsEditing(false);
  }, [user, preferences]);

  if (!user) {
    return (
      <Container size="md">
        <EmptyState
          message="Please log in to view your profile"
        />
      </Container>
    );
  }

  return (
    <Container size="lg">
      {loading ? (
        <div className="flex items-center justify-center min-h-[400px]">
          <LoadingSpinner />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Page Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Profile</h1>
              <p className="mt-1 text-sm text-gray-500">
                Manage your account information and preferences
              </p>
            </div>
            {!isEditing ? (
              <Button
                variant="primary"
                onClick={() => setIsEditing(true)}
              >
                Edit Profile
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  onClick={handleCancel}
                  disabled={saving}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? <LoadingSpinner /> : 'Save Changes'}
                </Button>
              </div>
            )}
          </div>

          {/* Error Messages */}
          {errors.general && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{errors.general}</p>
            </div>
          )}

        {/* Basic Information */}
        <Card variant="default" className="p-6">
          <h2 className="text-xl font-semibold mb-4">Basic Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="First Name"
              type="text"
              value={formData.firstName}
              onChange={handleInputChange('firstName')}
              disabled={!isEditing}
              error={errors.firstName}
              placeholder="Enter your first name"
            />
            
            <Input
              label="Last Name"
              type="text"
              value={formData.lastName}
              onChange={handleInputChange('lastName')}
              disabled={!isEditing}
              error={errors.lastName}
              placeholder="Enter your last name"
            />
            
            <Input
              label="Username"
              type="text"
              value={formData.username}
              onChange={handleInputChange('username')}
              disabled={!isEditing}
              error={errors.username}
              required
              placeholder="Enter your username"
            />
            
            <Input
              label="Email"
              type="email"
              value={user.email}
              onChange={() => {}} // No-op since field is disabled
              disabled={true}
              helperText="Email cannot be changed"
            />
          </div>
          
          {displayName && (
            <div className="mt-4 p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700">
                Display Name: <span className="text-gray-900">{displayName}</span>
              </p>
            </div>
          )}
        </Card>

        {/* Family & Serving Preferences */}
        <Card variant="default" className="p-6">
          <h2 className="text-xl font-semibold mb-4">Family & Serving Preferences</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Input
              label="Family Size"
              type="number"
              value={preferencesData.familySize.toString()}
              onChange={(value) => handlePreferenceChange('familySize')(parseInt(value) || 1)}
              disabled={!isEditing}
              error={errors.familySize}
              helperText="Number of people in your household (1-20)"
            />
            
            <Input
              label="Default Servings"
              type="number"
              value={preferencesData.defaultServings.toString()}
              onChange={(value) => handlePreferenceChange('defaultServings')(parseInt(value) || 1)}
              disabled={!isEditing}
              error={errors.defaultServings}
              helperText="Default servings for new recipes (1-50)"
            />
            
            <Input
              label="Meal Planning Days"
              type="number"
              value={preferencesData.mealPlanningDays.toString()}
              onChange={(value) => handlePreferenceChange('mealPlanningDays')(parseInt(value) || 7)}
              disabled={!isEditing}
              error={errors.mealPlanningDays}
              helperText="How many days to plan ahead (1-30)"
            />
          </div>
        </Card>

        {/* Dietary Restrictions & Allergies */}
        <Card variant="default" className="p-6">
          <h2 className="text-xl font-semibold mb-4">Dietary Restrictions & Allergies</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Allergies
              </label>
              <div className="space-y-2">
                {commonAllergies.map((allergy) => (
                  <label key={allergy} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={preferencesData.allergies.includes(allergy)}
                      onChange={(e) => {
                        const newAllergies = e.target.checked
                          ? [...preferencesData.allergies, allergy]
                          : preferencesData.allergies.filter(a => a !== allergy);
                        handlePreferenceChange('allergies')(newAllergies);
                      }}
                      disabled={!isEditing}
                      className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="text-sm text-gray-700">{allergy}</span>
                  </label>
                ))}
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Dietary Restrictions
              </label>
              <div className="space-y-2">
                {commonDietaryRestrictions.map((restriction) => (
                  <label key={restriction} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={preferencesData.dietaryRestrictions.includes(restriction)}
                      onChange={(e) => {
                        const newRestrictions = e.target.checked
                          ? [...preferencesData.dietaryRestrictions, restriction]
                          : preferencesData.dietaryRestrictions.filter(r => r !== restriction);
                        handlePreferenceChange('dietaryRestrictions')(newRestrictions);
                      }}
                      disabled={!isEditing}
                      className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="text-sm text-gray-700">{restriction}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </Card>

        {/* App Preferences */}
        <Card variant="default" className="p-6">
          <h2 className="text-xl font-semibold mb-4">App Preferences</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Theme
              </label>
              <Select
                value={{ id: preferencesData.theme, name: preferencesData.theme === 'light' ? 'Light' : preferencesData.theme === 'dark' ? 'Dark' : 'System' }}
                onChange={(option) => handlePreferenceChange('theme')(option.id)}
                disabled={!isEditing}
                options={[
                  { id: 'light', name: 'Light' },
                  { id: 'dark', name: 'Dark' },
                  { id: 'system', name: 'System' },
                ]}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Units
              </label>
              <Select
                value={{ id: preferencesData.units, name: preferencesData.units === 'imperial' ? 'Imperial (cups, lbs, °F)' : 'Metric (ml, kg, °C)' }}
                onChange={(option) => handlePreferenceChange('units')(option.id)}
                disabled={!isEditing}
                options={[
                  { id: 'imperial', name: 'Imperial (cups, lbs, °F)' },
                  { id: 'metric', name: 'Metric (ml, kg, °C)' },
                ]}
              />
            </div>
          </div>
        </Card>

        {/* Preferred Cuisines */}
        <Card variant="default" className="p-6">
          <h2 className="text-xl font-semibold mb-4">Preferred Cuisines</h2>
          <p className="text-sm text-gray-600 mb-4">
            Select your favorite cuisines to get better recipe recommendations
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {commonCuisines.map((cuisine) => (
              <label key={cuisine} className="flex items-center">
                <input
                  type="checkbox"
                  checked={preferencesData.preferredCuisines.includes(cuisine)}
                  onChange={(e) => {
                    const newCuisines = e.target.checked
                      ? [...preferencesData.preferredCuisines, cuisine]
                      : preferencesData.preferredCuisines.filter(c => c !== cuisine);
                    handlePreferenceChange('preferredCuisines')(newCuisines);
                  }}
                  disabled={!isEditing}
                  className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="text-sm text-gray-700">{cuisine}</span>
              </label>
            ))}
          </div>
        </Card>
      </div>
      )}
    </Container>
  );
}

export default UserProfilePage;
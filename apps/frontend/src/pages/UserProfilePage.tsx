import React, { useState, useCallback } from 'react';
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
import { 
  commonAllergies, 
  commonDietaryRestrictions, 
  commonCuisines,
  type UserPreferences 
} from '../types/UserPreferences';

function UserProfilePage() {
  const { user, setUser } = useAuthStore();
  const { preferences, updatePreferences } = useUserPreferencesStore();
  const displayName = useDisplayName();
  
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    firstName: user?.first_name || '',
    lastName: user?.last_name || '',
    username: user?.username || '',
  });
  const [preferencesData, setPreferencesData] = useState<UserPreferences>(preferences);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

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
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    setFormData(prev => ({ ...prev, [field]: event.target.value }));
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
      // Update local preferences immediately
      updatePreferences(preferencesData);
      
      // Update user info if changed
      if (user && (
        formData.firstName !== user.first_name ||
        formData.lastName !== user.last_name ||
        formData.username !== user.username
      )) {
        const updatedUser = {
          ...user,
          first_name: formData.firstName || undefined,
          last_name: formData.lastName || undefined,
          username: formData.username,
        };
        setUser(updatedUser);
      }

      setIsEditing(false);
      
      // TODO: When backend preferences endpoint exists, sync preferences here
      // await userApi.updateProfile(formData);
      // await userApi.updatePreferences(preferencesData);
      
    } catch (error) {
      console.error('Failed to save profile:', error);
      // TODO: Show error toast
    } finally {
      setSaving(false);
    }
  }, [formData, preferencesData, user, updatePreferences, setUser, validateForm]);

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
          title="Not logged in"
          description="Please log in to view your profile"
        />
      </Container>
    );
  }

  return (
    <Container size="lg">
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
              min="1"
              max="20"
              value={preferencesData.familySize.toString()}
              onChange={(e) => handlePreferenceChange('familySize')(parseInt(e.target.value) || 1)}
              disabled={!isEditing}
              error={errors.familySize}
              helperText="Number of people in your household"
            />
            
            <Input
              label="Default Servings"
              type="number"
              min="1"
              max="50"
              value={preferencesData.defaultServings.toString()}
              onChange={(e) => handlePreferenceChange('defaultServings')(parseInt(e.target.value) || 1)}
              disabled={!isEditing}
              error={errors.defaultServings}
              helperText="Default servings for new recipes"
            />
            
            <Input
              label="Meal Planning Days"
              type="number"
              min="1"
              max="30"
              value={preferencesData.mealPlanningDays.toString()}
              onChange={(e) => handlePreferenceChange('mealPlanningDays')(parseInt(e.target.value) || 7)}
              disabled={!isEditing}
              error={errors.mealPlanningDays}
              helperText="How many days to plan ahead"
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
                value={preferencesData.theme}
                onChange={(value) => handlePreferenceChange('theme')(value)}
                disabled={!isEditing}
                options={[
                  { value: 'light', label: 'Light' },
                  { value: 'dark', label: 'Dark' },
                  { value: 'system', label: 'System' },
                ]}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Units
              </label>
              <Select
                value={preferencesData.units}
                onChange={(value) => handlePreferenceChange('units')(value)}
                disabled={!isEditing}
                options={[
                  { value: 'imperial', label: 'Imperial (cups, lbs, °F)' },
                  { value: 'metric', label: 'Metric (ml, kg, °C)' },
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
    </Container>
  );
}

export default UserProfilePage;
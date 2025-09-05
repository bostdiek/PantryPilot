import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore, useIsAuthenticated } from '../stores/useAuthStore';
import { Button } from './ui/Button';

const Navigation: React.FC = () => {
  const { hasHydrated, logout } = useAuthStore();
  const isAuthenticated = useIsAuthenticated();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="flex items-center justify-between gap-4 border-b border-gray-200 bg-white px-6 py-4 shadow">
      <div className="flex gap-4">
        {/* Show navigation links only when authenticated */}
        {hasHydrated && isAuthenticated && (
          <>
            <NavLink
              to="/"
              end
              className={(meta: { isActive: boolean }) =>
                `text-lg font-bold ${
                  meta.isActive
                    ? 'text-primary-700 border-primary-500 border-b-2'
                    : 'hover:text-primary-600 text-gray-700 transition-colors'
                }`
              }
            >
              Home
            </NavLink>
            <NavLink
              to="/recipes"
              className={(meta: { isActive: boolean }) =>
                `text-lg font-bold ${
                  meta.isActive
                    ? 'text-primary-700 border-primary-500 border-b-2'
                    : 'hover:text-primary-600 text-gray-700 transition-colors'
                }`
              }
            >
              Recipes
            </NavLink>
            <NavLink
              to="/recipes/new"
              className={(meta: { isActive: boolean }) =>
                `text-lg font-bold ${
                  meta.isActive
                    ? 'text-primary-700 border-primary-500 border-b-2'
                    : 'hover:text-primary-600 text-gray-700 transition-colors'
                }`
              }
            >
              Add Recipe
            </NavLink>
            <NavLink
              to="/meal-plan"
              className={(meta: { isActive: boolean }) =>
                `text-lg font-bold ${
                  meta.isActive
                    ? 'text-primary-700 border-primary-500 border-b-2'
                    : 'hover:text-primary-600 text-gray-700 transition-colors'
                }`
              }
            >
              Meal Plan
            </NavLink>
          </>
        )}
      </div>

      {/* Authentication buttons */}
      <div className="flex items-center gap-2">
        {hasHydrated && (
          <>
            {isAuthenticated ? (
              <Button variant="secondary" onClick={handleLogout}>
                Logout
              </Button>
            ) : (
              <NavLink to="/login">
                <Button variant="primary">Login</Button>
              </NavLink>
            )}
          </>
        )}
      </div>
    </nav>
  );
};

export default Navigation;

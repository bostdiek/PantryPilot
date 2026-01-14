import { MessageSquare } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  useAuthStore,
  useDisplayName,
  useIsAuthenticated,
} from '../../stores/useAuthStore';
import { Button } from '../ui/Button';
import { Brand } from './Brand';

const Navigation: React.FC = () => {
  const { hasHydrated, logout } = useAuthStore();
  const isAuthenticated = useIsAuthenticated();
  const displayName = useDisplayName();
  const navigate = useNavigate();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        userMenuRef.current &&
        !userMenuRef.current.contains(event.target as Node)
      ) {
        setUserMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleLogout = () => {
    logout('manual');
    setUserMenuOpen(false);
    navigate('/login');
  };

  const handleProfileClick = () => {
    setUserMenuOpen(false);
    navigate('/user');
  };

  return (
    <nav className="flex items-center justify-between gap-4 border-b border-gray-200 bg-white px-6 py-4 shadow">
      {/* Brand Logo */}
      <div className="flex-shrink-0">
        <NavLink to="/" className="transition-opacity hover:opacity-80">
          <Brand />
        </NavLink>
      </div>

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
            <NavLink
              to="/grocery-list"
              className={(meta: { isActive: boolean }) =>
                `text-lg font-bold ${
                  meta.isActive
                    ? 'text-primary-700 border-primary-500 border-b-2'
                    : 'hover:text-primary-600 text-gray-700 transition-colors'
                }`
              }
            >
              Grocery List
            </NavLink>
            <NavLink
              to="/assistant"
              className={(meta: { isActive: boolean }) =>
                `text-lg font-bold ${
                  meta.isActive
                    ? 'text-primary-700 border-primary-500 border-b-2'
                    : 'hover:text-primary-600 text-gray-700 transition-colors'
                }`
              }
            >
              <span className="inline-flex items-center gap-2">
                <MessageSquare className="h-5 w-5" aria-hidden="true" />
                <span>Assistant</span>
              </span>
            </NavLink>
          </>
        )}
      </div>

      {/* Authentication and User Menu */}
      <div className="flex items-center gap-2">
        {hasHydrated && (
          <>
            {isAuthenticated ? (
              <div className="relative" ref={userMenuRef}>
                {/* User Menu Button */}
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-blue-700">
                    {displayName.charAt(0).toUpperCase()}
                  </div>
                  <span className="hidden sm:block">{displayName}</span>
                  <svg
                    className={`h-4 w-4 transition-transform ${
                      userMenuOpen ? 'rotate-180' : ''
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>

                {/* Dropdown Menu */}
                {userMenuOpen && (
                  <div className="ring-opacity-5 absolute right-0 z-50 mt-2 w-48 rounded-md bg-white py-1 shadow-lg ring-1 ring-black">
                    <button
                      onClick={handleProfileClick}
                      className="block w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100"
                    >
                      Profile Settings
                    </button>
                    <button
                      onClick={handleLogout}
                      className="block w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100"
                    >
                      Logout
                    </button>
                  </div>
                )}
              </div>
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
